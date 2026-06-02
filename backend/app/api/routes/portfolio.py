from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import yfinance as yf
import numpy as np

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import PortfolioHolding, LSTMModel, TickerSentiment, User
from app.schemas.schemas import (
    HoldingCreate, HoldingOut, PortfolioSummary,
    ForecastOut, SentimentOut,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _get_ticker_info(ticker: str) -> dict:
    """Fetch live price and company info from yfinance."""
    yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker
    try:
        data = yf.Ticker(yf_ticker)
        info = data.info
        hist = data.history(period="2d")
        current_price = float(hist["Close"].iloc[-1]) if not hist.empty else None
        return {
            "current_price": current_price,
            "company_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
        }
    except Exception:
        return {"current_price": None, "company_name": None, "sector": None}


def _compute_sharpe(ticker: str, period: str = "1y") -> Optional[float]:
    """Annualized Sharpe ratio using daily returns. Risk-free rate = 6.5% (India)."""
    try:
        yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker
        hist = yf.download(yf_ticker, period=period, progress=False)
        if hist.empty or len(hist) < 30:
            return None
        daily_returns = hist["Close"].pct_change().dropna()
        risk_free_daily = 0.065 / 252
        excess = daily_returns - risk_free_daily
        sharpe = float((excess.mean() / excess.std()) * np.sqrt(252))
        return round(sharpe, 3)
    except Exception:
        return None


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

    # Trigger LSTM training in background for new ticker
    background_tasks.add_task(_train_lstm_background, payload.ticker, db)

    return HoldingOut(
        id=holding.id,
        ticker=holding.ticker,
        company_name=holding.company_name,
        quantity=holding.quantity,
        buy_price=holding.buy_price,
        current_price=round(current_price, 2),
        current_value=round(current_val, 2),
        pnl=round(pnl, 2),
        pnl_pct=round((pnl / invested) * 100, 2),
        sector=holding.sector,
        exchange=holding.exchange,
        sentiment_label=None,
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


@router.get("/summary", response_model=PortfolioSummary)
def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.query(PortfolioHolding).filter(
        PortfolioHolding.user_id == current_user.id
    ).all()

    if not holdings:
        return PortfolioSummary(
            total_invested=0, current_value=0, total_pnl=0,
            total_pnl_pct=0, sharpe_ratio=None, holdings=[],
            allocation_by_sector={},
        )

    total_invested = 0.0
    total_current = 0.0
    sector_allocation: dict[str, float] = {}
    holding_outs = []

    for h in holdings:
        info = _get_ticker_info(h.ticker)
        current_price = info.get("current_price") or h.buy_price
        invested = h.quantity * h.buy_price
        current_val = h.quantity * current_price
        pnl = current_val - invested

        # Sentiment
        sentiment = (
            db.query(TickerSentiment)
            .filter(TickerSentiment.ticker == h.ticker)
            .order_by(TickerSentiment.computed_at.desc())
            .first()
        )

        holding_outs.append(HoldingOut(
            id=h.id,
            ticker=h.ticker,
            company_name=h.company_name or info.get("company_name"),
            quantity=h.quantity,
            buy_price=h.buy_price,
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

    # Normalize sector allocation to percentages
    if total_current > 0:
        sector_allocation = {k: round((v / total_current) * 100, 1) for k, v in sector_allocation.items()}

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested else 0

    # Portfolio-level Sharpe (use first holding as proxy — simplification)
    sharpe = _compute_sharpe(holdings[0].ticker) if holdings else None

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        current_value=round(total_current, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        sharpe_ratio=sharpe,
        holdings=holding_outs,
        allocation_by_sector=sector_allocation,
    )


# ── LSTM Forecast ──────────────────────────────────────────────

@router.get("/forecast/{ticker}", response_model=ForecastOut)
def get_forecast(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.ml.lstm_forecaster import forecast

    ticker = ticker.upper()

    # Verify user holds this ticker
    holding = db.query(PortfolioHolding).filter(
        PortfolioHolding.user_id == current_user.id,
        PortfolioHolding.ticker == ticker,
    ).first()
    if not holding:
        raise HTTPException(status_code=404, detail=f"You don't hold {ticker}")

    try:
        result = forecast(ticker, days=30)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Model for {ticker} not trained yet. Add holding to trigger training.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {e}")

    lstm_model = (
        db.query(LSTMModel)
        .filter(LSTMModel.ticker == ticker, LSTMModel.is_production == True)
        .first()
    )

    return ForecastOut(
        ticker=result["ticker"],
        current_price=result["current_price"],
        forecast_7d=result["forecast_7d"],
        forecast_30d=result["forecast_30d"],
        model_mae_pct=lstm_model.val_mae_pct if lstm_model else None,
    )


@router.post("/forecast/{ticker}/train", status_code=202)
def trigger_training(
    ticker: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger LSTM training for a ticker."""
    ticker = ticker.upper()
    background_tasks.add_task(_train_lstm_background, ticker, db)
    return {"message": f"Training started for {ticker}. This takes 3–8 minutes."}


# ── Sentiment ──────────────────────────────────────────────────

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
        .order_by(TickerSentiment.computed_at.desc())
        .first()
    )
    if not sentiment:
        raise HTTPException(status_code=404, detail="No sentiment data yet. Will be available within the hour.")

    return SentimentOut(
        ticker=ticker,
        label=sentiment.label.value,
        score=sentiment.score,
        top_headlines=sentiment.top_headlines,
        computed_at=sentiment.computed_at,
    )


# ── Background task ────────────────────────────────────────────

def _train_lstm_background(ticker: str, db: Session):
    """Train LSTM in background. Saves to disk + updates lstm_models table."""
    from app.ml.lstm_forecaster import train

    existing = (
        db.query(LSTMModel)
        .filter(LSTMModel.ticker == ticker, LSTMModel.is_production == True)
        .first()
    )
    existing_mae = existing.val_mae_pct if existing else None

    try:
        result = train(ticker, existing_mae)
        if result.get("promoted"):
            # Mark old model as not production
            db.query(LSTMModel).filter(
                LSTMModel.ticker == ticker,
                LSTMModel.is_production == True,
            ).update({"is_production": False})

            new_model = LSTMModel(
                ticker=ticker,
                model_path=result["model_path"],
                val_mae=result["val_mae"],
                val_mae_pct=result["val_mae_pct"],
                mlflow_run_id=result["mlflow_run_id"],
                is_production=True,
            )
            db.add(new_model)
            db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"LSTM training failed for {ticker}: {e}")
