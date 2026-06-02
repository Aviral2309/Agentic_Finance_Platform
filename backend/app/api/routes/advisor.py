import json
import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import AdvisorMessage
from app.ml.advisor import get_advisor_graph, AdvisorState

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/chat")
async def chat(
    payload: AdvisorMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    LangGraph multi-agent advisor with SSE streaming.
    Router → [Expense | Portfolio | RAG] → Synthesizer → stream to client.
    """
    graph = get_advisor_graph()

    initial_state: AdvisorState = {
        "user_id": str(current_user.id),
        "query": payload.message,
        "intent": None,
        "expense_context": None,
        "portfolio_context": None,
        "rag_chunks": None,
        "messages": [],
        "final_response": None,
    }

    async def event_stream():
        try:
            # Yield thinking indicator
            yield f"data: {json.dumps({'type': 'thinking', 'content': 'Analyzing your financial data...'})}\n\n"
            await asyncio.sleep(0.1)

            # Run graph — synchronous call wrapped for SSE
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                None, lambda: graph.invoke(initial_state)
            )

            response = final_state.get("final_response", "I could not generate a response.")
            intent = final_state.get("intent", "general")

            # Stream response word by word for chat feel
            words = response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # Final done event
            yield f"data: {json.dumps({'type': 'done', 'intent': intent})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve conversation history from ChromaDB.
    Placeholder — full implementation uses ChromaDB embeddings per user.
    """
    return {"messages": [], "note": "Conversation memory active for session context"}
