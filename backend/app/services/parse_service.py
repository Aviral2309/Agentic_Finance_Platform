"""
Async chunked PDF/CSV parser with per-chunk fault tolerance.

Design decisions (interview-ready):
- Returns 202 Accepted immediately — never blocks FastAPI worker
- 50 pages per chunk — constant memory regardless of file size
- Per-chunk retry — failure at page 847 does not abort the job
- Writes to DB chunk by chunk — partial progress visible instantly
- Batches LLM calls — 750 Gemini calls → 1 batch call per chunk
"""
import re
import logging
from datetime import datetime
from math import ceil
from typing import Optional
from uuid import UUID

import pandas as pd
import pdfplumber
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.ml.categorizer import categorize_batch
from app.models.models import (
    FailedChunk, HITLQueue, JobStatus,
    ParseJob, Transaction, TransactionType,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 50   # pages per chunk
MAX_RETRIES = 3


# ── Celery task ────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=0)
def process_upload_task(self, job_id: str):
    """
    Entry point called by FastAPI after file is saved.
    Runs in Celery worker — completely separate from the API process.
    """
    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        if job.file_type == "pdf":
            _process_pdf(db, job)
        elif job.file_type == "csv":
            _process_csv(db, job)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        db = SessionLocal()
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


# ── PDF processing ─────────────────────────────────────────────

def _process_pdf(db: Session, job: ParseJob):
    with pdfplumber.open(job.file_path) as pdf:
        total_pages = len(pdf.pages)
        total_chunks = ceil(total_pages / CHUNK_SIZE)

        job.total_pages = total_pages
        job.total_chunks = total_chunks
        db.commit()

        failed_any = False

        for chunk_idx in range(total_chunks):
            start = chunk_idx * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, total_pages)
            chunk_pages = pdf.pages[start:end]

            success = _process_pdf_chunk_with_retry(
                db, job, chunk_idx, chunk_pages
            )
            if not success:
                failed_any = True

            # Update progress after each chunk — frontend polls this
            job.chunks_done = chunk_idx + 1
            db.commit()

        job.status = JobStatus.PARTIAL if failed_any else JobStatus.DONE
        job.completed_at = datetime.utcnow()
        db.commit()


def _process_pdf_chunk_with_retry(
    db: Session, job: ParseJob, chunk_idx: int, pages
) -> bool:
    for attempt in range(MAX_RETRIES):
        try:
            transactions_data = _extract_transactions_from_pages(pages)
            if transactions_data:
                _save_transactions(db, job, transactions_data)
            return True
        except Exception as e:
            logger.warning(f"Chunk {chunk_idx} attempt {attempt+1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                # Log failed chunk — job continues without aborting
                failed = FailedChunk(
                    job_id=job.id,
                    chunk_idx=chunk_idx,
                    error_msg=str(e),
                    retry_count=MAX_RETRIES,
                )
                db.add(failed)
                db.commit()
                return False
    return False


def _extract_transactions_from_pages(pages) -> list[dict]:
    """
    Extract transaction rows from PDF pages.
    Handles SBI, HDFC, ICICI, Axis, Kotak statement formats.
    """
    transactions = []
    for page in pages:
        text = page.extract_text() or ""
        rows = _parse_statement_text(text)
        transactions.extend(rows)
    return transactions


def _parse_statement_text(text: str) -> list[dict]:
    """
    Parse raw text from bank statement page into structured rows.
    Interview: regex-based extraction — handles format variance across banks.
    """
    transactions = []
    lines = text.split("\n")

    # Pattern: date + description + amount (debit/credit) + balance
    # Covers most Indian bank statement formats
    date_pattern = re.compile(
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{2}\s+\w{3}\s+\d{4})"
    )
    amount_pattern = re.compile(r"[\d,]+\.\d{2}")

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        date_match = date_pattern.search(line)
        amounts = amount_pattern.findall(line)

        if not date_match or not amounts:
            continue

        try:
            date_str = date_match.group(1)
            date = _parse_date(date_str)
            if not date:
                continue

            # Remove date and amounts from description
            desc = date_pattern.sub("", line)
            for amt in amounts:
                desc = desc.replace(amt, "")
            desc = re.sub(r"\s+", " ", desc).strip()

            if not desc or len(desc) < 3:
                continue

            # First amount is usually debit, second credit, third balance
            # This is heuristic — adjust per bank format
            amount_vals = [float(a.replace(",", "")) for a in amounts]

            if len(amount_vals) >= 2:
                # Determine debit vs credit by position in line
                debit_pos = line.find(amounts[0])
                credit_pos = line.find(amounts[1]) if len(amounts) > 1 else -1

                if credit_pos > debit_pos and amount_vals[0] > 0:
                    tx_type = TransactionType.DEBIT
                    amount = amount_vals[0]
                else:
                    tx_type = TransactionType.CREDIT
                    amount = amount_vals[0]
            else:
                tx_type = TransactionType.DEBIT
                amount = amount_vals[0]

            if amount <= 0:
                continue

            transactions.append({
                "date": date,
                "description": desc[:500],
                "amount": amount,
                "transaction_type": tx_type,
                "balance": amount_vals[-1] if len(amount_vals) >= 2 else None,
                "hour": date.hour,
                "day_of_week": date.weekday(),
            })

        except Exception:
            continue

    return transactions


def _parse_date(date_str: str) -> Optional[datetime]:
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%d %b %Y", "%d %B %Y", "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


# ── CSV processing ─────────────────────────────────────────────

def _process_csv(db: Session, job: ParseJob):
    """
    CSV parsing — simpler than PDF, all in one pass.
    Supports standard bank CSV export formats.
    """
    try:
        df = pd.read_csv(job.file_path, encoding="utf-8", on_bad_lines="skip")

        # Normalize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

        # Map common column name variants
        col_map = {
            "date": ["date", "transaction_date", "txn_date", "value_date"],
            "description": ["description", "narration", "particulars", "details", "remarks"],
            "debit": ["debit", "withdrawal", "dr", "debit_amount"],
            "credit": ["credit", "deposit", "cr", "credit_amount"],
            "balance": ["balance", "closing_balance", "running_balance"],
        }

        resolved = {}
        for field, variants in col_map.items():
            for v in variants:
                if v in df.columns:
                    resolved[field] = v
                    break

        if "date" not in resolved or "description" not in resolved:
            raise ValueError("Could not identify date/description columns in CSV")

        transactions_data = []
        for _, row in df.iterrows():
            try:
                date = _parse_date(str(row[resolved["date"]]))
                if not date:
                    continue

                desc = str(row[resolved["description"]]).strip()
                if not desc or desc in ("nan", ""):
                    continue

                debit = float(str(row.get(resolved.get("debit", ""), 0) or 0).replace(",", "") or 0)
                credit = float(str(row.get(resolved.get("credit", ""), 0) or 0).replace(",", "") or 0)

                if debit > 0:
                    amount, tx_type = debit, TransactionType.DEBIT
                elif credit > 0:
                    amount, tx_type = credit, TransactionType.CREDIT
                else:
                    continue

                transactions_data.append({
                    "date": date,
                    "description": desc[:500],
                    "amount": amount,
                    "transaction_type": tx_type,
                    "balance": float(str(row.get(resolved.get("balance", ""), 0) or 0).replace(",", "") or 0) or None,
                    "hour": date.hour,
                    "day_of_week": date.weekday(),
                })
            except Exception:
                continue

        job.total_pages = len(df)
        job.total_chunks = 1
        job.chunks_done = 1

        if transactions_data:
            _save_transactions(db, job, transactions_data)

        job.status = JobStatus.DONE
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise


# ── Save transactions with categorization ──────────────────────

def _save_transactions(db: Session, job: ParseJob, transactions_data: list[dict]):
    """
    Categorize and save a batch of transactions.
    Runs 4-layer pipeline — batches LLM calls for cost efficiency.
    """
    import asyncio

    # Run async categorizer in sync context (Celery worker)
    loop = asyncio.new_event_loop()
    cat_results = loop.run_until_complete(
        categorize_batch(transactions_data, settings.GEMINI_API_KEY)
    )
    loop.close()

    hitl_items = []

    for tx_data, cat_result in zip(transactions_data, cat_results):
        tx = Transaction(
            user_id=job.user_id,
            job_id=job.id,
            date=tx_data["date"],
            amount=tx_data["amount"],
            description=tx_data["description"],
            transaction_type=tx_data["transaction_type"],
            balance=tx_data.get("balance"),
            category=cat_result["category"],
            categorization_layer=cat_result["layer"],
            confidence=cat_result["confidence"],
            is_confirmed=not cat_result["needs_hitl"],
            merchant_name=_extract_merchant(tx_data["description"]),
        )
        db.add(tx)
        db.flush()  # get tx.id without full commit

        if cat_result["needs_hitl"]:
            hitl_items.append(tx)

    # Add HITL queue entries for uncertain transactions
    for tx in hitl_items:
        hitl = HITLQueue(
            user_id=job.user_id,
            transaction_id=tx.id,
            suggested_category=tx.category,
            alternative_categories=["Food & Dining", "Shopping", "Transport", "Other"],
        )
        db.add(hitl)

    job.transactions_found += len(transactions_data)
    db.commit()


def _extract_merchant(description: str) -> Optional[str]:
    """Best-effort merchant name extraction from description."""
    # UPI format: UPI/merchant_name/...
    upi_match = re.search(r"UPI[\/\-]([A-Za-z0-9\s]+)[\/\-]", description, re.IGNORECASE)
    if upi_match:
        return upi_match.group(1).strip()[:100]

    # Take first meaningful word(s)
    words = description.split()
    if words:
        return " ".join(words[:3])[:100]

    return None


# ── Recurring transaction detector ─────────────────────────────

def detect_recurring(db: Session, user_id: UUID):
    """
    Mark transactions as recurring if same amount appears
    on same merchant 3+ times. Runs after each successful parse.
    """
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date)
        .all()
    )

    # Group by merchant + amount
    from collections import defaultdict
    groups = defaultdict(list)
    for tx in txns:
        key = (tx.merchant_name or tx.description[:30], round(tx.amount, 2))
        groups[key].append(tx)

    for key, group in groups.items():
        if len(group) >= 3:
            for tx in group:
                tx.is_recurring = True
    db.commit()
