"""
LangGraph multi-agent financial advisor.

Graph: Router → [Expense Agent | Portfolio Agent | RAG Agent] → Synthesizer → SSE stream

Interview: why LangGraph over LangChain agents?
LangGraph gives explicit state + conditional edges. I control exactly which
agents activate. LangChain agents are non-deterministic. In a financial product,
I need auditability of which data sources influenced a response.
"""
import logging
from typing import TypedDict, Optional, Annotated
import operator

logger = logging.getLogger(__name__)


# ── State schema ───────────────────────────────────────────────

class AdvisorState(TypedDict):
    user_id: str
    query: str
    intent: Optional[str]                    # classified by router
    expense_context: Optional[str]           # from expense agent
    portfolio_context: Optional[str]         # from portfolio agent
    rag_chunks: Optional[str]                # from RAG agent
    messages: Annotated[list, operator.add]  # conversation history
    final_response: Optional[str]


# ── Router Agent ───────────────────────────────────────────────

def router_agent(state: AdvisorState) -> AdvisorState:
    """
    Classify query intent using Gemini.
    Returns one of: expense | portfolio | both | rag | general
    """
    from app.core.config import settings
    import google.generativeai as genai

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""Classify this financial query into one category.
Query: "{state['query']}"

Categories:
- expense: about spending, transactions, budget, categories
- portfolio: about investments, stocks, portfolio, returns, forecast
- both: needs both expense and portfolio context
- rag: needs financial knowledge (tax rules, SEBI guidelines, general finance concepts)
- general: general financial advice

Reply with ONLY the category word. Nothing else."""

        response = model.generate_content(prompt)
        intent = response.text.strip().lower()
        if intent not in ["expense", "portfolio", "both", "rag", "general"]:
            intent = "general"

    except Exception as e:
        logger.warning(f"Router failed: {e}. Defaulting to general.")
        intent = "general"

    return {**state, "intent": intent}


# ── Expense Agent ──────────────────────────────────────────────

def expense_agent(state: AdvisorState) -> AdvisorState:
    """Query PostgreSQL for user's expense data. Format as context string."""
    from app.core.database import SessionLocal
    from app.models.models import Transaction, TransactionType, BudgetLimit
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        user_id = state["user_id"]
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # This month spending by category
        this_month = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.date >= month_start,
            )
            .group_by(Transaction.category)
            .all()
        )

        # Last month for comparison
        last_month = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.date >= last_month_start,
                Transaction.date < month_start,
            )
            .group_by(Transaction.category)
            .all()
        )

        # Budget status
        budgets = db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id).all()

        # Build context string
        this_dict = {row.category: row.total for row in this_month}
        last_dict = {row.category: row.total for row in last_month}
        total_this = sum(this_dict.values())
        total_last = sum(last_dict.values())

        lines = [
            f"Current month spending: ₹{total_this:,.0f}",
            f"Last month spending: ₹{total_last:,.0f}",
            f"Month-over-month change: {((total_this - total_last) / max(total_last, 1)) * 100:.1f}%",
            "\nSpending by category this month:",
        ]
        for cat, amt in sorted(this_dict.items(), key=lambda x: x[1], reverse=True):
            last_amt = last_dict.get(cat, 0)
            change = ((amt - last_amt) / max(last_amt, 1)) * 100
            lines.append(f"  {cat}: ₹{amt:,.0f} ({change:+.1f}% vs last month)")

        if budgets:
            lines.append("\nBudget status:")
            for b in budgets:
                spent = this_dict.get(b.category, 0)
                pct = (spent / b.monthly_limit) * 100
                status = "OVER BUDGET" if pct > 100 else f"{pct:.0f}% used"
                lines.append(f"  {b.category}: ₹{spent:,.0f} / ₹{b.monthly_limit:,.0f} limit — {status}")

        context = "\n".join(lines)

    except Exception as e:
        context = f"Could not fetch expense data: {e}"
    finally:
        db.close()

    return {**state, "expense_context": context}


# ── Portfolio Agent ────────────────────────────────────────────

def portfolio_agent(state: AdvisorState) -> AdvisorState:
    """Fetch holdings + live prices + sentiment. Format as context."""
    from app.core.database import SessionLocal
    from app.models.models import PortfolioHolding, TickerSentiment
    import yfinance as yf

    db = SessionLocal()
    try:
        user_id = state["user_id"]
        holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == user_id).all()

        if not holdings:
            return {**state, "portfolio_context": "User has no portfolio holdings."}

        lines = ["Portfolio holdings:"]
        total_invested = 0
        total_current = 0

        for h in holdings:
            try:
                yf_ticker = f"{h.ticker}.NS" if not h.ticker.endswith((".NS", ".BO")) else h.ticker
                data = yf.download(yf_ticker, period="2d", progress=False)
                current_price = float(data["Close"].iloc[-1]) if not data.empty else h.buy_price
            except Exception:
                current_price = h.buy_price

            invested = h.quantity * h.buy_price
            current = h.quantity * current_price
            pnl = current - invested
            pnl_pct = (pnl / invested) * 100

            # Latest sentiment
            sentiment = (
                db.query(TickerSentiment)
                .filter(TickerSentiment.ticker == h.ticker)
                .order_by(TickerSentiment.computed_at.desc())
                .first()
            )
            sentiment_str = sentiment.label.value if sentiment else "unknown"

            lines.append(
                f"  {h.ticker}: {h.quantity} shares @ ₹{h.buy_price:,.2f} buy | "
                f"₹{current_price:,.2f} current | P&L: ₹{pnl:,.0f} ({pnl_pct:+.1f}%) | "
                f"Sentiment: {sentiment_str}"
            )
            total_invested += invested
            total_current += current

        total_pnl = total_current - total_invested
        total_pnl_pct = (total_pnl / max(total_invested, 1)) * 100

        lines.extend([
            f"\nTotal invested: ₹{total_invested:,.0f}",
            f"Current value: ₹{total_current:,.0f}",
            f"Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)",
        ])

        context = "\n".join(lines)

    except Exception as e:
        context = f"Could not fetch portfolio data: {e}"
    finally:
        db.close()

    return {**state, "portfolio_context": context}


# ── RAG Agent ──────────────────────────────────────────────────

def rag_agent(state: AdvisorState) -> AdvisorState:
    """ChromaDB similarity search — returns top-3 relevant knowledge chunks."""
    from app.core.config import settings
    import chromadb

    try:
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection("financial_knowledge")

        results = collection.query(
            query_texts=[state["query"]],
            n_results=3,
        )

        chunks = results.get("documents", [[]])[0]
        if chunks:
            context = "Relevant financial knowledge:\n" + "\n---\n".join(chunks)
        else:
            context = "No specific knowledge found for this query."

    except Exception as e:
        logger.warning(f"RAG failed: {e}")
        context = ""

    return {**state, "rag_chunks": context}


# ── Synthesizer Agent ──────────────────────────────────────────

def synthesizer_agent(state: AdvisorState) -> AdvisorState:
    """
    Combine all context, call Gemini, return final response.
    This is the only agent that calls the LLM for response generation.
    """
    from app.core.config import settings
    import google.generativeai as genai

    context_parts = []
    if state.get("expense_context"):
        context_parts.append(f"EXPENSE DATA:\n{state['expense_context']}")
    if state.get("portfolio_context"):
        context_parts.append(f"PORTFOLIO DATA:\n{state['portfolio_context']}")
    if state.get("rag_chunks"):
        context_parts.append(f"FINANCIAL KNOWLEDGE:\n{state['rag_chunks']}")

    context = "\n\n".join(context_parts) if context_parts else "No specific user data available."

    history = state.get("messages", [])
    history_str = ""
    if history:
        history_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history[-6:]])
        history_str = f"\nConversation history:\n{history_str}\n"

    prompt = f"""You are WealthPilot, a personal financial advisor for Indian users.
You have access to the user's actual financial data. Give specific, actionable advice.
Be direct. Use ₹ for amounts. Reference their actual numbers, not hypotheticals.

{context}
{history_str}
User question: {state['query']}

Respond in 3-5 sentences. Be specific to their data."""

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        final_response = response.text
    except Exception as e:
        final_response = f"I encountered an error generating advice: {e}. Please try again."

    return {**state, "final_response": final_response}


# ── Build graph ────────────────────────────────────────────────

def build_advisor_graph():
    """
    Assemble the LangGraph graph with conditional routing.
    Router output determines which data-fetching agents activate.
    """
    from langgraph.graph import StateGraph, END

    graph = StateGraph(AdvisorState)

    graph.add_node("router", router_agent)
    graph.add_node("expense_agent", expense_agent)
    graph.add_node("portfolio_agent", portfolio_agent)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("synthesizer", synthesizer_agent)

    graph.set_entry_point("router")

    # Conditional routing based on intent
    def route_after_router(state: AdvisorState) -> list[str]:
        intent = state.get("intent", "general")
        if intent == "expense":
            return ["expense_agent"]
        elif intent == "portfolio":
            return ["portfolio_agent"]
        elif intent == "both":
            return ["expense_agent", "portfolio_agent"]
        elif intent == "rag":
            return ["rag_agent"]
        else:
            return ["synthesizer"]  # general → skip to synthesizer

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "expense_agent": "expense_agent",
            "portfolio_agent": "portfolio_agent",
            "rag_agent": "rag_agent",
            "synthesizer": "synthesizer",
        },
    )

    graph.add_edge("expense_agent", "synthesizer")
    graph.add_edge("portfolio_agent", "synthesizer")
    graph.add_edge("rag_agent", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


# Singleton graph — compiled once at import
_advisor_graph = None


def get_advisor_graph():
    global _advisor_graph
    if _advisor_graph is None:
        _advisor_graph = build_advisor_graph()
    return _advisor_graph
