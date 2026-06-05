import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PUUID
import uuid

from app.core.database import get_db, Base, SessionLocal
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import AdvisorMessage

router = APIRouter(prefix="/advisor", tags=["advisor"])
logger = logging.getLogger(__name__)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = {'extend_existing': True}
    id         = Column(PUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(PUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def _get_history(user_id: str, limit=10):
    from uuid import UUID
    db = SessionLocal()
    try:
        uid = UUID(user_id)
        msgs = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.user_id == uid)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit).all()
        )
        return [{"role": m.role, "content": m.content} for m in reversed(msgs)]
    except Exception:
        return []
    finally:
        db.close()


def _save_message(user_id: str, role: str, content: str):
    from uuid import UUID
    db = SessionLocal()
    try:
        uid = UUID(user_id)
        msg = ConversationMessage(user_id=uid, role=role, content=content)
        db.add(msg)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _get_statement_context(user_id: str) -> str:
    from uuid import UUID
    from app.models.models import Transaction, TransactionType, ParseJob, JobStatus
    from sqlalchemy import func
    db = SessionLocal()
    try:
        uid = UUID(user_id)
        latest_job = (
            db.query(ParseJob)
            .filter(ParseJob.user_id == uid,
                    ParseJob.status.in_([JobStatus.DONE, JobStatus.PARTIAL]))
            .order_by(ParseJob.created_at.desc()).first()
        )
        if not latest_job:
            return ""
        summary = (
            db.query(Transaction.category,
                     func.sum(Transaction.amount).label("total"),
                     func.count().label("count"))
            .filter(Transaction.user_id == uid,
                    Transaction.job_id == latest_job.id,
                    Transaction.transaction_type == TransactionType.DEBIT)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc()).all()
        )
        if not summary:
            return ""
        total = sum(r.total for r in summary)
        lines = [
            f"Latest statement: {latest_job.filename}",
            f"Transactions: {latest_job.transactions_found}",
            f"Total spending: ₹{total:,.0f}",
        ]
        for r in summary[:8]:
            lines.append(f"  {r.category or 'Other'}: ₹{r.total:,.0f} ({r.count} txns)")
        return "\n".join(lines)
    except Exception:
        return ""
    finally:
        db.close()


@router.post("/chat")
async def chat(
    payload: AdvisorMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.ml.advisor import get_advisor_graph, AdvisorState

    # Capture string values immediately — never use ORM objects across async boundary
    user_id = str(current_user.id)

    history = _get_history(user_id)
    statement_context = _get_statement_context(user_id)
    _save_message(user_id, "user", payload.message)

    graph = get_advisor_graph()
    initial_state: AdvisorState = {
        "user_id": user_id,
        "query": payload.message,
        "intent": None,
        "expense_context": None,
        "portfolio_context": None,
        "rag_chunks": None,
        "statement_context": statement_context,
        "messages": history,
        "final_response": None,
    }

    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Analysing your financial data...'})}\n\n"
            await asyncio.sleep(0.1)

            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                None, lambda: graph.invoke(initial_state)
            )

            response = final_state.get("final_response", "Could not generate response.")
            intent = final_state.get("intent", "general")

            _save_message(user_id, "assistant", response)

            words = response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.015)

            yield f"data: {json.dumps({'type': 'done', 'intent': intent})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
def get_history_endpoint(
    current_user: User = Depends(get_current_user),
):
    from uuid import UUID
    db = SessionLocal()
    try:
        uid = UUID(str(current_user.id))
        msgs = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.user_id == uid)
            .order_by(ConversationMessage.created_at.asc())
            .limit(50).all()
        )
        return [{"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]
    except Exception:
        return []
    finally:
        db.close()


@router.delete("/history")
def clear_history_endpoint(
    current_user: User = Depends(get_current_user),
):
    from uuid import UUID
    db = SessionLocal()
    try:
        uid = UUID(str(current_user.id))
        db.query(ConversationMessage).filter(ConversationMessage.user_id == uid).delete()
        db.commit()
        return {"message": "History cleared"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()