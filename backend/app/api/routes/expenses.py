import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID
from collections import defaultdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, BackgroundTasks
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    BudgetLimit, HITLQueue, JobStatus,
    ParseJob, Transaction, TransactionType, User,
)
from app.schemas.schemas import (
    BudgetLimitCreate, BudgetLimitOut, BudgetStatus,
    HITLConfirm, HITLItem, JobStatusOut,
    ExpenseSummary, TransactionOut, TransactionUpdate,
)

router = APIRouter(prefix="/expenses", tags=["expenses"])

ALLOWED_EXTENSIONS = {".pdf", ".csv"}


# ── Direct parse (bypasses Celery — works on Windows) ──────────

def _run_parse_direct(job_id: str):
    """
    Runs file parsing directly in a FastAPI background thread.
    Used instead of Celery because Celery runs in Docker and
    cannot access files saved on the Windows host filesystem.
    """
    from app.core.database import SessionLocal
    from app.services.parse_service import _process_pdf, _process_csv

    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == UUID(job_id)).first()
        if not job:
            return
        job.status = JobStatus.PROCESSING
        db.commit()

        if job.file_type == "pdf":
            _process_pdf(db, job)
        elif job.file_type == "csv":
            _process_csv(db, job)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Direct parse failed: {e}", exc_info=True)
        db2 = SessionLocal()
        try:
            j = db2.query(ParseJob).filter(ParseJob.id == UUID(job_id)).first()
            if j:
                j.status = JobStatus.FAILED
                j.error_message = str(e)
                j.completed_at = datetime.utcnow()
                db2.commit()
        finally:
            db2.close()
    finally:
        db.close()


# ── Upload ──────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_statement(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not supported. Use PDF or CSV.")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB}MB.")

    upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    job_id = uuid.uuid4()
    filename = f"{job_id}{ext}"
    file_path = upload_dir / filename

    with open(file_path, "wb") as f:
        f.write(content)

    job = ParseJob(
        id=job_id,
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=ext.lstrip("."),
        status=JobStatus.QUEUED,
    )
    db.add(job)
    db.commit()

    # Use FastAPI background task instead of Celery
    # Celery worker runs in Docker and cannot access Windows host files
    background_tasks.add_task(_run_parse_direct, str(job_id))

    return {
        "job_id": str(job_id),
        "message": "Upload received. Processing started.",
        "poll_url": f"/api/expenses/jobs/{job_id}",
    }


@router.get("/jobs/{job_id}", response_model=JobStatusOut)
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(ParseJob).filter(
        ParseJob.id == job_id,
        ParseJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    progress_pct = 0.0
    if job.total_chunks and job.total_chunks > 0:
        progress_pct = (job.chunks_done / job.total_chunks) * 100

    return JobStatusOut(
        job_id=job.id,
        status=job.status.value,
        progress_pct=round(progress_pct, 1),
        chunks_done=job.chunks_done,
        total_chunks=job.total_chunks,
        transactions_found=job.transactions_found,
        filename=job.filename,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


# ── Statements library ──────────────────────────────────────────

@router.get("/statements")
def get_statements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(ParseJob)
        .filter(
            ParseJob.user_id == current_user.id,
            ParseJob.status.in_([JobStatus.DONE, JobStatus.PARTIAL]),
            ParseJob.transactions_found > 0,
        )
        .order_by(ParseJob.created_at.desc())
        .all()
    )
    return [
        {
            "job_id": str(j.id),
            "filename": j.filename,
            "file_type": j.file_type,
            "transactions_found": j.transactions_found,
            "status": j.status.value,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]


@router.delete("/statements/{job_id}", status_code=204)
def delete_statement(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.models import FailedChunk
    job = db.query(ParseJob).filter(
        ParseJob.id == job_id,
        ParseJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Statement not found")

    txn_ids = [t.id for t in db.query(Transaction.id).filter(Transaction.job_id == job_id).all()]
    for txn_id in txn_ids:
        db.query(HITLQueue).filter(HITLQueue.transaction_id == txn_id).delete()

    db.query(Transaction).filter(Transaction.job_id == job_id).delete()
    db.query(FailedChunk).filter(FailedChunk.job_id == job_id).delete()
    db.delete(job)
    db.commit()


# ── Transactions ────────────────────────────────────────────────

@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    category: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    q = db.query(Transaction).filter(Transaction.user_id == uid)

    if month:
        try:
            year, mon = int(month.split("-")[0]), int(month.split("-")[1])
            q = q.filter(
                extract("year", Transaction.date) == year,
                extract("month", Transaction.date) == mon,
            )
        except Exception:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM format")

    if category:
        q = q.filter(Transaction.category == category)

    return q.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()


@router.post("/transactions/manual", response_model=TransactionOut, status_code=201)
def add_manual_transaction(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.ml.categorizer import layer1_rule_based

    description = payload.get("description", "")
    amount = float(payload.get("amount", 0))
    transaction_type = payload.get("transaction_type", "debit")
    category = payload.get("category", "")
    date_str = payload.get("date", datetime.utcnow().isoformat())

    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))
    except Exception:
        date = datetime.utcnow()

    if not category:
        cat = layer1_rule_based(description)
        category = cat or "Other"
        layer = 1 if cat else 4
    else:
        layer = 4

    tx = Transaction(
        user_id=UUID(str(current_user.id)),
        date=date,
        amount=amount,
        description=description,
        transaction_type=TransactionType.DEBIT if transaction_type == "debit" else TransactionType.CREDIT,
        category=category,
        categorization_layer=layer,
        confidence=1.0 if layer == 1 else 0.5,
        is_confirmed=True,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction_category(
    tx_id: UUID,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.user_id == UUID(str(current_user.id)),
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.category = payload.category
    tx.sub_category = payload.sub_category
    tx.is_confirmed = True
    tx.categorization_layer = 4
    db.commit()
    db.refresh(tx)
    return tx


# ── Summary + Trends ────────────────────────────────────────────

@router.get("/summary")
def get_expense_summary(
    month: Optional[str] = Query(None, description="YYYY-MM for specific month, omit for all time"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))

    if month:
        try:
            year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        except Exception:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM format")
        rows = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"), func.count().label("count"))
            .filter(
                Transaction.user_id == uid,
                Transaction.transaction_type == TransactionType.DEBIT,
                extract("year", Transaction.date) == year,
                extract("month", Transaction.date) == mon,
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )
        month_label = f"{year}-{mon:02d}"
    else:
        rows = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"), func.count().label("count"))
            .filter(
                Transaction.user_id == uid,
                Transaction.transaction_type == TransactionType.DEBIT,
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )
        month_label = "all"

    grand_total = sum(r.total for r in rows)
    summary = [
        ExpenseSummary(
            category=r.category or "Uncategorized",
            total=round(r.total, 2),
            count=r.count,
            percentage=round((r.total / grand_total) * 100, 1) if grand_total else 0,
        )
        for r in rows
    ]
    return {"month": month_label, "total": round(grand_total, 2), "categories": summary}


@router.get("/trends")
def get_monthly_trends(
    months: int = Query(6, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.transaction_type,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.user_id == uid)
        .group_by("year", "month", Transaction.transaction_type)
        .order_by("year", "month")
        .all()
    )

    monthly = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
    for r in rows:
        key = f"{int(r.year)}-{int(r.month):02d}"
        if r.transaction_type == TransactionType.DEBIT:
            monthly[key]["debit"] += r.total
        else:
            monthly[key]["credit"] += r.total

    sorted_months = sorted(monthly.keys())[-months:]
    return [
        {
            "month": m,
            "total_debit": round(monthly[m]["debit"], 2),
            "total_credit": round(monthly[m]["credit"], 2),
            "net": round(monthly[m]["credit"] - monthly[m]["debit"], 2),
        }
        for m in sorted_months
    ]


# ── Budget ──────────────────────────────────────────────────────

@router.post("/budgets", response_model=BudgetLimitOut, status_code=201)
def create_budget(
    payload: BudgetLimitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    existing = db.query(BudgetLimit).filter(
        BudgetLimit.user_id == uid,
        BudgetLimit.category == payload.category,
    ).first()
    if existing:
        existing.monthly_limit = payload.monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = BudgetLimit(
        user_id=uid,
        category=payload.category,
        monthly_limit=payload.monthly_limit,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/budgets/status", response_model=List[BudgetStatus])
def get_budget_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    now = datetime.utcnow()
    budgets = db.query(BudgetLimit).filter(BudgetLimit.user_id == uid).all()

    result = []
    for b in budgets:
        spent = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == uid,
                Transaction.category == b.category,
                Transaction.transaction_type == TransactionType.DEBIT,
                extract("year", Transaction.date) == now.year,
                extract("month", Transaction.date) == now.month,
            )
            .scalar() or 0.0
        )
        result.append(BudgetStatus(
            category=b.category,
            limit=b.monthly_limit,
            spent=round(spent, 2),
            remaining=round(b.monthly_limit - spent, 2),
            percentage_used=round((spent / b.monthly_limit) * 100, 1) if b.monthly_limit else 0,
            is_over=spent > b.monthly_limit,
        ))
    return result


# ── HITL ────────────────────────────────────────────────────────

@router.get("/hitl", response_model=List[HITLItem])
def get_hitl_queue(
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    items = (
        db.query(HITLQueue)
        .filter(HITLQueue.user_id == uid, ~HITLQueue.is_resolved)
        .limit(limit)
        .all()
    )
    result = []
    for item in items:
        tx = db.query(Transaction).filter(Transaction.id == item.transaction_id).first()
        if tx:
            result.append(HITLItem(
                hitl_id=item.id,
                transaction_id=item.transaction_id,
                date=tx.date,
                amount=tx.amount,
                description=tx.description,
                suggested_category=item.suggested_category,
                alternative_categories=item.alternative_categories,
            ))
    return result


@router.post("/hitl/confirm")
def confirm_hitl(
    payload: HITLConfirm,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = UUID(str(current_user.id))
    hitl = db.query(HITLQueue).filter(
        HITLQueue.transaction_id == payload.transaction_id,
        HITLQueue.user_id == uid,
    ).first()

    tx = db.query(Transaction).filter(
        Transaction.id == payload.transaction_id,
        Transaction.user_id == uid,
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.category = payload.confirmed_category
    tx.sub_category = payload.sub_category
    tx.is_confirmed = True
    tx.categorization_layer = 4

    if hitl:
        hitl.is_resolved = True

    db.commit()
    return {"message": "Confirmed", "category": payload.confirmed_category}