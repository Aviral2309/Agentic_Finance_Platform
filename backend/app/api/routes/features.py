"""
New features:
1. Spending anomaly detection
2. News feed with portfolio impact
3. Goal tracking
4. Data export (CSV)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import io
import csv

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, Transaction, TransactionType, PortfolioHolding

router = APIRouter(prefix="/features", tags=["features"])


# ── Anomaly Detection ──────────────────────────────────────────

@router.get("/anomalies")
def detect_anomalies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detect spending anomalies by comparing current month
    against 3-month rolling average per category.
    """
    uid = UUID(str(current_user.id))
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    three_months_ago = month_start - timedelta(days=90)

    # Current month spending by category
    current = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
        .filter(
            Transaction.user_id == uid,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= month_start,
        )
        .group_by(Transaction.category)
        .all()
    )

    # 3-month average by category
    historical = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
        .filter(
            Transaction.user_id == uid,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= three_months_ago,
            Transaction.date < month_start,
        )
        .group_by(Transaction.category)
        .all()
    )

    hist_dict = {r.category: r.total / 3 for r in historical}
    anomalies = []

    for row in current:
        cat = row.category or "Other"
        current_amt = row.total
        avg_amt = hist_dict.get(cat, 0)

        if avg_amt > 0:
            pct_change = ((current_amt - avg_amt) / avg_amt) * 100
            if pct_change > 50:
                severity = "high" if pct_change > 100 else "medium"
                anomalies.append({
                    "category": cat,
                    "current_amount": round(current_amt, 0),
                    "average_amount": round(avg_amt, 0),
                    "pct_change": round(pct_change, 1),
                    "severity": severity,
                    "message": f"{cat} is up {pct_change:.0f}% vs your 3-month average — ₹{current_amt:,.0f} vs ₹{avg_amt:,.0f} normally",
                })
        elif current_amt > 1000:
            # New category with significant spend
            anomalies.append({
                "category": cat,
                "current_amount": round(current_amt, 0),
                "average_amount": 0,
                "pct_change": 100,
                "severity": "low",
                "message": f"New spending in {cat} — ₹{current_amt:,.0f} (no prior history)",
            })

    anomalies.sort(key=lambda x: x["pct_change"], reverse=True)
    return {"anomalies": anomalies, "count": len(anomalies)}


# ── News Feed with Portfolio Impact ────────────────────────────

@router.get("/news")
def get_news_feed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch financial news and cross-reference with user's portfolio.
    """
    from app.core.config import settings

    uid = UUID(str(current_user.id))
    holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == uid).all()
    tickers = [h.ticker for h in holdings]

    news_items = []

    try:
        if not settings.NEWS_API_KEY or settings.NEWS_API_KEY == "dummy":
            # Return mock news if no API key
            return _mock_news(tickers)

        from newsapi import NewsApiClient
        newsapi = NewsApiClient(api_key=settings.NEWS_API_KEY)

        # General Indian finance news
        response = newsapi.get_top_headlines(
            category="business",
            country="in",
            page_size=15,
        )

        articles = response.get("articles", [])

        for article in articles:
            if not article.get("title"):
                continue

            title = article["title"]
            description = article.get("description", "")
            content = f"{title} {description}".upper()

            # Check portfolio impact
            impacted_holdings = []
            for h in holdings:
                if h.ticker in content or (h.company_name and h.company_name.upper() in content):
                    impacted_holdings.append(h.ticker)

            # Sentiment (simple rule-based if FinBERT unavailable)
            sentiment = _quick_sentiment(title)

            news_items.append({
                "title": title,
                "description": description or "",
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "sentiment": sentiment,
                "portfolio_impact": impacted_holdings,
                "affects_portfolio": len(impacted_holdings) > 0,
            })

    except Exception:
        return _mock_news(tickers)

    # Sort — portfolio impact first
    news_items.sort(key=lambda x: (not x["affects_portfolio"], x["published_at"]))

    return {
        "articles": news_items[:12],
        "portfolio_tickers": tickers,
        "total": len(news_items),
    }


def _quick_sentiment(text: str) -> str:
    text_lower = text.lower()
    positive = ["surge", "rally", "gain", "profit", "record", "growth", "rise", "high", "bull", "strong", "beat"]
    negative = ["fall", "drop", "loss", "crash", "weak", "decline", "bear", "miss", "cut", "default", "crisis"]

    pos_score = sum(1 for w in positive if w in text_lower)
    neg_score = sum(1 for w in negative if w in text_lower)

    if pos_score > neg_score:
        return "bullish"
    elif neg_score > pos_score:
        return "bearish"
    return "neutral"


def _mock_news(tickers: list) -> dict:
    """Mock news when API key is not available."""
    return {
        "articles": [
            {
                "title": "Nifty 50 hits record high as FIIs return to Indian markets",
                "description": "Foreign institutional investors pumped ₹12,000 crore into Indian equities this week.",
                "source": "Economic Times",
                "url": "https://economictimes.com",
                "published_at": datetime.utcnow().isoformat(),
                "sentiment": "bullish",
                "portfolio_impact": tickers[:2] if tickers else [],
                "affects_portfolio": bool(tickers),
            },
            {
                "title": "RBI keeps repo rate unchanged at 6.5%, maintains neutral stance",
                "description": "The central bank decided to hold rates steady amid global uncertainty.",
                "source": "Business Standard",
                "url": "https://business-standard.com",
                "published_at": datetime.utcnow().isoformat(),
                "sentiment": "neutral",
                "portfolio_impact": [],
                "affects_portfolio": False,
            },
            {
                "title": "IT sector faces pressure as US tech spending slows",
                "description": "Indian IT companies may see slower deal signings in Q3.",
                "source": "Mint",
                "url": "https://livemint.com",
                "published_at": datetime.utcnow().isoformat(),
                "sentiment": "bearish",
                "portfolio_impact": [t for t in tickers if t in ["TCS", "INFY", "WIPRO", "HCLTECH"]],
                "affects_portfolio": any(t in tickers for t in ["TCS", "INFY", "WIPRO", "HCLTECH"]),
            },
        ],
        "portfolio_tickers": tickers,
        "total": 3,
    }


# ── Goal Tracking ──────────────────────────────────────────────

# Simple in-memory goals for now (can add DB table later)
_user_goals = {}


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    target_date: Optional[str] = None
    category: str = "savings"


@router.get("/goals")
def get_goals(current_user: User = Depends(get_current_user)):
    uid = str(current_user.id)
    return {"goals": _user_goals.get(uid, [])}


@router.post("/goals", status_code=201)
def create_goal(
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    if uid not in _user_goals:
        _user_goals[uid] = []

    goal = {
        "id": len(_user_goals[uid]) + 1,
        "name": payload.name,
        "target_amount": payload.target_amount,
        "current_amount": payload.current_amount,
        "target_date": payload.target_date,
        "category": payload.category,
        "progress_pct": round((payload.current_amount / payload.target_amount) * 100, 1) if payload.target_amount else 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    _user_goals[uid].append(goal)
    return goal


@router.patch("/goals/{goal_id}")
def update_goal(
    goal_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    goals = _user_goals.get(uid, [])
    for goal in goals:
        if goal["id"] == goal_id:
            if "current_amount" in payload:
                goal["current_amount"] = payload["current_amount"]
                goal["progress_pct"] = round((goal["current_amount"] / goal["target_amount"]) * 100, 1)
            return goal
    raise HTTPException(status_code=404, detail="Goal not found")


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
):
    uid = str(current_user.id)
    if uid in _user_goals:
        _user_goals[uid] = [g for g in _user_goals[uid] if g["id"] != goal_id]


# ── Data Export ────────────────────────────────────────────────

@router.get("/export/transactions")
def export_transactions(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export transactions as CSV."""
    uid = UUID(str(current_user.id))
    q = db.query(Transaction).filter(Transaction.user_id == uid)

    if month:
        year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        q = q.filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == mon,
        )

    transactions = q.order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Type", "Amount", "Layer", "Confirmed"])

    for tx in transactions:
        writer.writerow([
            tx.date.strftime("%Y-%m-%d") if tx.date else "",
            tx.description or "",
            tx.category or "",
            tx.transaction_type.value if tx.transaction_type else "",
            tx.amount or 0,
            tx.categorization_layer or "",
            "Yes" if tx.is_confirmed else "No",
        ])

    output.seek(0)
    filename = f"wealthpilot_transactions_{month or 'all'}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
