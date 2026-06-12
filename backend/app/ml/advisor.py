"""
Fixed LangGraph advisor — proper SQLAlchemy session handling.

Key fix: each agent opens and closes its OWN session.
Never pass session objects across thread boundaries.
UUID conversion done explicitly to avoid type mismatch.
"""
import logging
from typing import TypedDict, Optional, Annotated
import operator
from uuid import UUID

logger = logging.getLogger(__name__)


class AdvisorState(TypedDict):
    user_id: str          # always a string UUID
    query: str
    intent: Optional[str]
    expense_context: Optional[str]
    portfolio_context: Optional[str]
    rag_chunks: Optional[str]
    statement_context: Optional[str]
    messages: Annotated[list, operator.add]
    final_response: Optional[str]


def _safe_uuid(user_id: str) -> UUID:
    """Convert string to UUID safely."""
    try:
        return UUID(user_id)
    except Exception:
        raise ValueError(f"Invalid user_id: {user_id}")


# ── Router ─────────────────────────────────────────────────────

def router_agent(state: AdvisorState) -> AdvisorState:
    from app.core.config import settings
    import google.generativeai as genai

    intent = "both"  # safe default
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env")
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""Classify this financial query. Reply with ONE word only.

Query: "{state['query']}"

Options:
- expense (spending, transactions, budget, categories)
- portfolio (stocks, investments, returns, holdings)
- both (needs expense AND portfolio data)
- rag (tax rules, financial concepts, SEBI guidelines)
- general (savings tips, financial planning)

Reply with exactly one word:"""

        response = model.generate_content(prompt)
        raw = response.text.strip().lower().split()[0]
        if raw in ["expense", "portfolio", "both", "rag", "general"]:
            intent = raw
        else:
            intent = "both"
    except Exception as e:
        logger.warning(f"Router failed ({e}), defaulting to both")
        intent = "both"

    return {**state, "intent": intent}


# ── Expense Agent ──────────────────────────────────────────────

def expense_agent(state: AdvisorState) -> AdvisorState:
    from app.core.database import SessionLocal
    from app.models.models import Transaction, TransactionType, BudgetLimit
    from sqlalchemy import func
    from datetime import datetime, timedelta

    context = "No expense data available."
    db = SessionLocal()
    try:
        uid = _safe_uuid(state["user_id"])
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # This month by category
        this_month = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"), func.count().label("cnt"))
            .filter(Transaction.user_id == uid,
                    Transaction.transaction_type == TransactionType.DEBIT,
                    Transaction.date >= month_start)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        # Last month
        last_month = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
            .filter(Transaction.user_id == uid,
                    Transaction.transaction_type == TransactionType.DEBIT,
                    Transaction.date >= last_month_start,
                    Transaction.date < month_start)
            .group_by(Transaction.category).all()
        )

        # Income
        income = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == uid,
            Transaction.transaction_type == TransactionType.CREDIT,
            Transaction.date >= month_start,
        ).scalar() or 0

        # Budgets
        budgets = db.query(BudgetLimit).filter(BudgetLimit.user_id == uid).all()

        # Recurring
        recurring = db.query(Transaction.description, Transaction.amount).filter(
            Transaction.user_id == uid,
            Transaction.is_recurring,
        ).distinct().limit(5).all()

        this_dict = {r.category or "Other": r.total for r in this_month}
        last_dict = {r.category or "Other": r.total for r in last_month}
        total_this = sum(this_dict.values())
        total_last = sum(last_dict.values())
        savings = income - total_this
        savings_rate = (savings / max(income, 1)) * 100

        lines = [
            "=== YOUR EXPENSE DATA ===",
            f"This month spending: ₹{total_this:,.0f}",
            f"Last month spending: ₹{total_last:,.0f}",
            f"Change: {((total_this-total_last)/max(total_last,1)*100):+.1f}%",
            f"Income this month: ₹{income:,.0f}",
            f"Savings: ₹{savings:,.0f} ({savings_rate:.1f}% savings rate)",
            "",
            "Spending breakdown:",
        ]
        for cat, amt in sorted(this_dict.items(), key=lambda x: x[1], reverse=True):
            last = last_dict.get(cat, 0)
            chg = ((amt - last) / max(last, 1)) * 100
            pct = (amt / max(total_this, 1)) * 100
            lines.append(f"  {cat}: ₹{amt:,.0f} ({pct:.1f}% of spend, {chg:+.1f}% vs last month)")

        if budgets:
            lines.append("\nBudget vs actual:")
            for b in budgets:
                spent = this_dict.get(b.category, 0)
                pct = (spent / b.monthly_limit) * 100
                status = "⚠ OVER" if pct > 100 else f"{pct:.0f}%"
                lines.append(f"  {b.category}: ₹{spent:,.0f} / ₹{b.monthly_limit:,.0f} ({status})")

        if recurring:
            lines.append("\nRecurring payments:")
            for r in recurring:
                lines.append(f"  {r.description[:35]}: ₹{r.amount:,.0f}/month")

        context = "\n".join(lines)

    except Exception as e:
        context = f"Could not load expense data: {e}"
        logger.error(f"Expense agent error: {e}", exc_info=True)
    finally:
        db.close()

    return {**state, "expense_context": context}


# ── Portfolio Agent ────────────────────────────────────────────

def portfolio_agent(state: AdvisorState) -> AdvisorState:
    from app.core.database import SessionLocal
    from app.models.models import PortfolioHolding, TickerSentiment
    import yfinance as yf

    context = "No portfolio holdings found."
    db = SessionLocal()
    try:
        uid = _safe_uuid(state["user_id"])
        holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == uid).all()

        if not holdings:
            return {**state, "portfolio_context": context}

        lines = ["=== YOUR PORTFOLIO DATA ==="]
        total_invested = 0.0
        total_current = 0.0
        sector_totals = {}

        for h in holdings:
            try:
                yf_ticker = f"{h.ticker}.NS" if not h.ticker.endswith((".NS", ".BO")) else h.ticker
                data = yf.download(yf_ticker, period="5d", progress=False, auto_adjust=True)
                price = float(data["Close"].iloc[-1]) if not data.empty else h.buy_price
            except Exception:
                price = h.buy_price

            invested = h.quantity * h.buy_price
            current = h.quantity * price
            pnl = current - invested
            pnl_pct = (pnl / max(invested, 1)) * 100

            sentiment = db.query(TickerSentiment).filter(
                TickerSentiment.ticker == h.ticker
            ).order_by(TickerSentiment.computed_at.desc()).first()
            sent_str = sentiment.label.value if sentiment else "not analyzed"

            lines.append(
                f"\n{h.ticker}: {h.quantity} shares @ ₹{h.buy_price} buy | "
                f"₹{price:,.2f} now | P&L: {pnl_pct:+.1f}% | Sentiment: {sent_str}"
            )
            total_invested += invested
            total_current += current
            sector = h.sector or "Unknown"
            sector_totals[sector] = sector_totals.get(sector, 0) + current

        total_pnl = total_current - total_invested
        total_pnl_pct = (total_pnl / max(total_invested, 1)) * 100

        lines.extend([
            f"\nTotal invested: ₹{total_invested:,.0f}",
            f"Current value: ₹{total_current:,.0f}",
            f"Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:+.1f}%)",
            "\nSector allocation:",
        ])
        for sector, val in sorted(sector_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (val / max(total_current, 1)) * 100
            flag = " ⚠ CONCENTRATED" if pct > 60 else ""
            lines.append(f"  {sector}: {pct:.1f}%{flag}")

        context = "\n".join(lines)

    except Exception as e:
        context = f"Could not load portfolio: {e}"
        logger.error(f"Portfolio agent error: {e}", exc_info=True)
    finally:
        db.close()

    return {**state, "portfolio_context": context}


# ── RAG Agent ──────────────────────────────────────────────────

def rag_agent(state: AdvisorState) -> AdvisorState:
    from app.core.config import settings
    import chromadb

    context = ""
    try:
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection("financial_knowledge")
        results = collection.query(query_texts=[state["query"]], n_results=3)
        chunks = results.get("documents", [[]])[0]
        if chunks:
            context = "=== FINANCIAL KNOWLEDGE ===\n" + "\n---\n".join(chunks)
    except Exception as e:
        logger.warning(f"RAG failed: {e}")

    return {**state, "rag_chunks": context}


# ── Synthesizer ────────────────────────────────────────────────

def synthesizer_agent(state: AdvisorState) -> AdvisorState:
    from app.core.config import settings
    import google.generativeai as genai

    parts = []
    if state.get("expense_context"):
        parts.append(state["expense_context"])
    if state.get("portfolio_context"):
        parts.append(state["portfolio_context"])
    if state.get("statement_context"):
        parts.append(f"=== UPLOADED STATEMENT ===\n{state['statement_context']}")
    if state.get("rag_chunks"):
        parts.append(state["rag_chunks"])

    context = "\n\n".join(parts) if parts else "No financial data available yet. Ask the user to upload a bank statement or add portfolio holdings."

    history = state.get("messages", [])
    history_str = ""
    if history:
        history_str = "\nPrevious conversation:\n" + "\n".join([
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in history[-6:]
        ]) + "\n"

    prompt = f"""You are WealthPilot, a personal financial advisor for Indian users.

You have the user's REAL financial data below. Use actual ₹ numbers in your response.
Be specific, direct, and actionable. Reference their actual data — not hypotheticals.

GUIDELINES:
- Use ₹ for amounts, not Rs or INR
- Reference specific categories, stocks, or amounts from their data
- Indian context: SIP, ELSS, NPS, NSE, 80C, HRA etc.
- If data is missing, tell them exactly what to upload/add
- Be conversational but professional
- Max 150 words unless detailed breakdown is requested
- Use bullet points for multiple recommendations

USER'S FINANCIAL DATA:
{context}
{history_str}
USER ASKS: {state['query']}"""

    response_text = "I encountered an error. Please try again."
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)

        # Try gemini-2.5-flash first
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            response_text = response.text
        except Exception:
            # Fallback to 1.5-flash
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            response_text = response.text

    except Exception as e:
        response_text = f"Error connecting to AI: {e}. Please verify your GEMINI_API_KEY in .env"
        logger.error(f"Synthesizer error: {e}", exc_info=True)

    return {**state, "final_response": response_text}


# ── Graph ──────────────────────────────────────────────────────

def build_advisor_graph():
    from langgraph.graph import StateGraph, END

    graph = StateGraph(AdvisorState)
    graph.add_node("router", router_agent)
    graph.add_node("expense_agent", expense_agent)
    graph.add_node("portfolio_agent", portfolio_agent)
    graph.add_node("rag_agent", rag_agent)
    graph.add_node("synthesizer", synthesizer_agent)

    graph.set_entry_point("router")

    def route(state: AdvisorState) -> str:
        intent = state.get("intent", "both")
        if intent == "expense":
            return "expense_agent"
        elif intent == "portfolio":
            return "portfolio_agent"
        elif intent == "rag":
            return "rag_agent"
        else:
            return "expense_agent"  # both/general: start with expense

    graph.add_conditional_edges("router", route, {
        "expense_agent": "expense_agent",
        "portfolio_agent": "portfolio_agent",
        "rag_agent": "rag_agent",
    })

    def after_expense(state: AdvisorState) -> str:
        # For both/general, also get portfolio
        if state.get("intent") in ["both", "general"]:
            return "portfolio_agent"
        return "synthesizer"

    graph.add_conditional_edges("expense_agent", after_expense, {
        "portfolio_agent": "portfolio_agent",
        "synthesizer": "synthesizer",
    })

    graph.add_edge("portfolio_agent", "synthesizer")
    graph.add_edge("rag_agent", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


_graph = None

def get_advisor_graph():
    global _graph
    if _graph is None:
        _graph = build_advisor_graph()
    return _graph
