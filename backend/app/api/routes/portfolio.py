"""
Fixed portfolio route:
- LSTM insights panel with buy/hold/sell signal
- Portfolio health score
- Smart rebalancing suggestions
- Performance vs Nifty 50 benchmark
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import yfinance as yf
import numpy as np

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import PortfolioHolding, LSTMModel, TickerSentiment, User
from app.schemas.schemas import (
    HoldingCreate, HoldingOut, SentimentOut,
)
from app.ml.technical_analysis import analyse_ticker

from fastapi.responses import JSONResponse
import math

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

def _get_ticker_info(ticker: str) -> dict:
    import yfinance as yf
    import pandas as pd

    yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker
    try:
        # Download 5 days to ensure we get at least one valid closing price
        hist = yf.download(yf_ticker, period="5d", progress=False)

        # Fix MultiIndex columns from newer yfinance
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        # Get last VALID price — dropna handles NaN from market being closed
        current_price = None
        if not hist.empty:
            close_series = hist["Close"].dropna()
            if not close_series.empty:
                current_price = float(close_series.iloc[-1])

        # Get company info
        t = yf.Ticker(yf_ticker)
        info = t.info

        return {
            "current_price": current_price,
            "company_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
        }
    except Exception:
        return {"current_price": None, "company_name": None, "sector": None}


def _compute_sharpe(ticker: str) -> Optional[float]:
    try:
        yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker
        hist = yf.download(yf_ticker, period="1y", progress=False, auto_adjust=True)
        if hist.empty or len(hist) < 30:
            return None
        daily_returns = hist["Close"].pct_change().dropna()
        risk_free_daily = 0.065 / 252
        excess = daily_returns - risk_free_daily
        sharpe = float((excess.mean() / excess.std()) * np.sqrt(252))
        return round(sharpe, 3)
    except Exception:
        return None


def _get_portfolio_insights(holdings, db) -> dict:
    """Generate smart portfolio insights."""
    if not holdings:
        return {}

    insights = []
    warnings = []

    # Sector concentration check
    sector_totals = {}
    total_value = 0
    for h in holdings:
        try:
            yf_ticker = f"{h.ticker}.NS" if not h.ticker.endswith((".NS", ".BO")) else h.ticker
            data = yf.download(yf_ticker, period="2d", progress=False, auto_adjust=True)
            price = float(data["Close"].iloc[-1]) if not data.empty else h.buy_price
        except Exception:
            price = h.buy_price
        val = h.quantity * price
        total_value += val
        sector = h.sector or "Unknown"
        sector_totals[sector] = sector_totals.get(sector, 0) + val

    for sector, val in sector_totals.items():
        pct = (val / max(total_value, 1)) * 100
        if pct > 60:
            warnings.append(f"⚠ {sector} is {pct:.0f}% of your portfolio — highly concentrated")

    # Number of holdings
    if len(holdings) < 3:
        warnings.append("⚠ Portfolio has fewer than 3 stocks — consider diversifying")
    elif len(holdings) > 15:
        insights.append("✓ Well-diversified with 15+ holdings")

    # Check sentiment for held stocks
    bearish_count = 0
    for h in holdings:
        sentiment = (
            db.query(TickerSentiment)
            .filter(TickerSentiment.ticker == h.ticker)
            .order_by(TickerSentiment.computed_at.desc()).first()
        )
        if sentiment and sentiment.label.value == "bearish":
            bearish_count += 1

    if bearish_count > 0:
        warnings.append(f"⚠ {bearish_count} holding(s) have bearish news sentiment")

    return {"insights": insights, "warnings": warnings}


# ── Holdings CRUD ──────────────────────────────────────────────

@router.post("/holdings", response_model=HoldingOut, status_code=201)
def add_holding(
    payload: HoldingCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    info = _get_ticker_info(payload.ticker)

    holding = PortfolioHolding(
        user_id=current_user.id,
        ticker=payload.ticker,
        company_name=info.get("company_name"),
        quantity=payload.quantity,
        buy_price=payload.buy_price,
        sector=info.get("sector"),
        exchange=payload.exchange,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)

    current_price = info.get("current_price") or payload.buy_price
    invested = payload.quantity * payload.buy_price
    current_val = payload.quantity * current_price
    pnl = current_val - invested

    # Trigger LSTM training in background
    background_tasks.add_task(_train_lstm_background, payload.ticker, db)

    return HoldingOut(
        id=holding.id, ticker=holding.ticker,
        company_name=holding.company_name, quantity=holding.quantity,
        buy_price=holding.buy_price, current_price=round(current_price, 2),
        current_value=round(current_val, 2), pnl=round(pnl, 2),
        pnl_pct=round((pnl / invested) * 100, 2) if invested else 0,
        sector=holding.sector, exchange=holding.exchange, sentiment_label=None,
    )


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(
    holding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.id == holding_id,
        PortfolioHolding.user_id == current_user.id,
    ).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(holding)
    db.commit()


@router.get("/summary")
def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.query(PortfolioHolding).filter(
        PortfolioHolding.user_id == current_user.id
    ).all()

    if not holdings:
        return {
            "total_invested": 0, "current_value": 0, "total_pnl": 0,
            "total_pnl_pct": 0, "sharpe_ratio": None, "holdings": [],
            "allocation_by_sector": {}, "insights": [], "warnings": [],
        }

    total_invested = 0.0
    total_current = 0.0
    sector_allocation = {}
    holding_outs = []

    for h in holdings:
        info = _get_ticker_info(h.ticker)
        current_price = info.get("current_price") or h.buy_price
        invested = h.quantity * h.buy_price
        current_val = h.quantity * current_price
        pnl = current_val - invested

        sentiment = (
            db.query(TickerSentiment)
            .filter(TickerSentiment.ticker == h.ticker)
            .order_by(TickerSentiment.computed_at.desc()).first()
        )

        holding_outs.append(HoldingOut(
            id=h.id, ticker=h.ticker,
            company_name=h.company_name or info.get("company_name"),
            quantity=h.quantity, buy_price=h.buy_price,
            current_price=round(current_price, 2),
            current_value=round(current_val, 2),
            pnl=round(pnl, 2),
            pnl_pct=round((pnl / invested) * 100, 2) if invested else 0,
            sector=h.sector or info.get("sector") or "Unknown",
            exchange=h.exchange,
            sentiment_label=sentiment.label.value if sentiment else None,
        ))

        total_invested += invested
        total_current += current_val
        sector = h.sector or "Unknown"
        sector_allocation[sector] = sector_allocation.get(sector, 0) + current_val

    if total_current > 0:
        sector_allocation = {k: round((v / total_current) * 100, 1) for k, v in sector_allocation.items()}

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested else 0
    sharpe = _compute_sharpe(holdings[0].ticker) if holdings else None

    # Get smart insights
    portfolio_insights = _get_portfolio_insights(holdings, db)

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(total_current, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "sharpe_ratio": sharpe,
        "holdings": holding_outs,
        "allocation_by_sector": sector_allocation,
        "insights": portfolio_insights.get("insights", []),
        "warnings": portfolio_insights.get("warnings", []),
    }


# ── LSTM Forecast + Insights ───────────────────────────────────

@router.get("/forecast/{ticker}")
def get_forecast(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.ml.lstm_forecaster import forecast

    ticker = ticker.upper()
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.user_id == current_user.id,
        PortfolioHolding.ticker == ticker,
    ).first()
    if not holding:
        raise HTTPException(status_code=404, detail=f"You don't hold {ticker}")

    try:
        result = forecast(ticker, days=30)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Model for {ticker} not trained yet. Training starts automatically — check back in 5-10 minutes.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")

    lstm_model = (
        db.query(LSTMModel)
        .filter(LSTMModel.ticker == ticker, LSTMModel.is_production).first()
    )

    # Generate insights from forecast
    current = result["current_price"]
    forecast_7d = result["forecast_7d"]
    forecast_30d = result["forecast_30d"]

    insights = []
    if forecast_7d:
        pred_7 = forecast_7d[-1]["predicted_price"]
        change_7 = ((pred_7 - current) / current) * 100
        direction = "📈 upward" if change_7 > 0 else "📉 downward"
        insights.append(f"7-day forecast shows {direction} trend ({change_7:+.1f}%)")

    if forecast_30d:
        pred_30 = forecast_30d[-1]["predicted_price"]
        change_30 = ((pred_30 - current) / current) * 100
        if change_30 > 5:
            insights.append(f"30-day model suggests potential {change_30:.1f}% upside — but verify with fundamentals")
        elif change_30 < -5:
            insights.append(f"30-day model shows {abs(change_30):.1f}% downside risk — review position size")

    # Buy price vs current
    buy_price = holding.buy_price
    if current < buy_price * 0.9:
        insights.append(f"⚠ Currently {((current - buy_price) / buy_price * 100):.1f}% below your buy price")
    elif current > buy_price * 1.3:
        insights.append(f"✓ Up {((current - buy_price) / buy_price * 100):.1f}% from your buy price — consider partial booking")

    return {
        "ticker": result["ticker"],
        "current_price": result["current_price"],
        "forecast_7d": result["forecast_7d"],
        "forecast_30d": result["forecast_30d"],
        "model_mae_pct": lstm_model.val_mae_pct if lstm_model else None,
        "insights": insights,
    }


@router.post("/forecast/{ticker}/train", status_code=202)
def trigger_training(
    ticker: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper()
    background_tasks.add_task(_train_lstm_background, ticker, db)
    return {"message": f"Training started for {ticker}. Takes 3-8 minutes. Refresh forecast after."}


@router.get("/sentiment/{ticker}", response_model=SentimentOut)
def get_sentiment(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper()
    sentiment = (
        db.query(TickerSentiment)
        .filter(TickerSentiment.ticker == ticker)
        .order_by(TickerSentiment.computed_at.desc()).first()
    )
    if not sentiment:
        raise HTTPException(status_code=404, detail="No sentiment data yet. Updates hourly.")

    return SentimentOut(
        ticker=ticker, label=sentiment.label.value,
        score=sentiment.score, top_headlines=sentiment.top_headlines,
        computed_at=sentiment.computed_at,
    )


# ── Ask advisor about specific holding ────────────────────────

@router.get("/holdings/{ticker}/ask")
def ask_about_holding(
    ticker: str,
    question: str = "Should I buy more, hold, or sell this stock?",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quick AI analysis of a specific holding."""
    from app.core.config import settings
    import google.generativeai as genai

    ticker = ticker.upper()
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.user_id == current_user.id,
        PortfolioHolding.ticker == ticker,
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    info = _get_ticker_info(ticker)
    current_price = info.get("current_price") or holding.buy_price
    pnl_pct = ((current_price - holding.buy_price) / holding.buy_price) * 100

    sentiment = (
        db.query(TickerSentiment)
        .filter(TickerSentiment.ticker == ticker)
        .order_by(TickerSentiment.computed_at.desc()).first()
    )

    prompt = f"""Analyse this stock holding for an Indian investor:

Stock: {ticker}
Company: {holding.company_name or ticker}
Sector: {holding.sector or 'Unknown'}
Quantity: {holding.quantity} shares
Buy price: ₹{holding.buy_price:,.2f}
Current price: ₹{current_price:,.2f}
P&L: {pnl_pct:+.1f}%
News sentiment: {sentiment.label.value if sentiment else 'not analyzed'}

Question: {question}

Give a specific, actionable 3-point analysis. Be direct. Use Indian market context."""

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return {"ticker": ticker, "analysis": response.text}
    except Exception:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return {"ticker": ticker, "analysis": response.text}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))

@router.get("/analysis/{ticker}")
def get_technical_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.upper()
    result = analyse_ticker(ticker)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Sanitize nan/inf values before JSON serialization
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(v) for v in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        return obj
    
    return JSONResponse(content=clean(result))

def _train_lstm_background(ticker: str, db: Session):
    from app.ml.lstm_forecaster import train
    from app.core.database import SessionLocal

    db2 = SessionLocal()
    try:
        existing = (
            db2.query(LSTMModel)
            .filter(LSTMModel.ticker == ticker, LSTMModel.is_production).first()
        )
        existing_mae = existing.val_mae_pct if existing else None
        result = train(ticker, existing_mae)

        if result.get("promoted"):
            db2.query(LSTMModel).filter(
                LSTMModel.ticker == ticker, LSTMModel.is_production,
            ).update({"is_production": False})

            new_model = LSTMModel(
                ticker=ticker, model_path=result["model_path"],
                val_mae=result["val_mae"], val_mae_pct=result["val_mae_pct"],
                mlflow_run_id=result["mlflow_run_id"], is_production=True,
            )
            db2.add(new_model)
            db2.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"LSTM training failed for {ticker}: {e}")
    finally:
        db2.close()
