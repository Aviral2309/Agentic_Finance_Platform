"""
New metrics features:
1. Modern Portfolio Theory (MPT) Efficient Frontier
2. Monte Carlo Retirement Simulation
3. Spending Forecast with MAE measurement

Add to backend/app/api/routes/insights.py
Or register as a new router in main.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
from datetime import datetime
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, PortfolioHolding

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ── MPT Efficient Frontier ─────────────────────────────────────

@router.get("/efficient-frontier")
def get_efficient_frontier(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute the Markowitz Efficient Frontier for the user's portfolio.
    
    Interview explanation:
    MPT says a rational investor wants maximum return for minimum risk.
    For a set of assets, there exists a curve of portfolios that are
    'efficient' — no other allocation gives better return for the same risk.
    We find this curve via Monte Carlo simulation of random allocations.
    """
    import yfinance as yf
    import pandas as pd

    uid = UUID(str(current_user.id))
    holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == uid).all()

    if len(holdings) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 holdings to compute efficient frontier"
        )

    tickers = [h.ticker for h in holdings]
    yf_tickers = [f"{t}.NS" if not t.endswith((".NS", ".BO")) else t for t in tickers]

    try:
        # Download 1 year of daily returns
        price_data = {}
        for ticker, yf_ticker in zip(tickers, yf_tickers):
            data = yf.download(yf_ticker, period="1y", progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            if not data.empty:
                price_data[ticker] = data["Close"].dropna()

        if len(price_data) < 2:
            raise HTTPException(status_code=400, detail="Insufficient price history")

        # Compute daily returns
        prices_df = pd.DataFrame(price_data).dropna()
        returns = prices_df.pct_change().dropna()
        mean_returns = returns.mean() * 252        # annualized
        cov_matrix = returns.cov() * 252           # annualized covariance

        n_assets = len(price_data)
        valid_tickers = list(price_data.keys())

        # Risk-free rate (India 10-year G-Sec ~7%)
        rf = 0.07

        # Monte Carlo simulation — 3000 random portfolios
        n_portfolios = 3000
        portfolio_returns = []
        portfolio_vols = []
        portfolio_sharpes = []
        portfolio_weights = []

        for _ in range(n_portfolios):
            weights = np.random.dirichlet(np.ones(n_assets))
            ret = float(np.dot(weights, mean_returns))
            vol = float(np.sqrt(weights @ cov_matrix.values @ weights))
            sharpe = (ret - rf) / vol if vol > 0 else 0
            portfolio_returns.append(round(ret * 100, 3))
            portfolio_vols.append(round(vol * 100, 3))
            portfolio_sharpes.append(round(sharpe, 4))
            portfolio_weights.append(weights.tolist())

        # Current portfolio
        total_value = sum(h.quantity * h.buy_price for h in holdings if h.ticker in valid_tickers)
        current_weights = np.array([
            (h.quantity * h.buy_price) / total_value
            for h in holdings if h.ticker in valid_tickers
        ])

        if len(current_weights) == n_assets:
            current_ret = float(np.dot(current_weights, mean_returns)) * 100
            current_vol = float(np.sqrt(current_weights @ cov_matrix.values @ current_weights)) * 100
            current_sharpe = (current_ret/100 - rf) / (current_vol/100) if current_vol > 0 else 0
        else:
            current_ret, current_vol, current_sharpe = 0, 0, 0

        # Max Sharpe portfolio
        max_idx = portfolio_sharpes.index(max(portfolio_sharpes))
        optimal_weights = {
            valid_tickers[i]: round(portfolio_weights[max_idx][i] * 100, 1)
            for i in range(n_assets)
        }

        return {
            "tickers": valid_tickers,
            "n_portfolios_simulated": n_portfolios,
            "frontier": {
                "returns": portfolio_returns,
                "volatilities": portfolio_vols,
                "sharpe_ratios": portfolio_sharpes,
            },
            "current_portfolio": {
                "return_pct": round(current_ret, 2),
                "volatility_pct": round(current_vol, 2),
                "sharpe_ratio": round(current_sharpe, 3),
            },
            "optimal_portfolio": {
                "return_pct": round(portfolio_returns[max_idx], 2),
                "volatility_pct": round(portfolio_vols[max_idx], 2),
                "sharpe_ratio": round(portfolio_sharpes[max_idx], 3),
                "weights_pct": optimal_weights,
            },
            "sharpe_gap": round(portfolio_sharpes[max_idx] - current_sharpe, 3),
            "insight": f"Your portfolio Sharpe ratio is {current_sharpe:.2f}. "
                       f"The optimal allocation gives {portfolio_sharpes[max_idx]:.2f} — "
                       f"consider rebalancing toward {max(optimal_weights, key=optimal_weights.get)}.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frontier computation failed: {str(e)}")


# ── Monte Carlo Retirement Simulation ─────────────────────────

class MonteCarloInput(BaseModel):
    monthly_sip: float
    current_corpus: float = 0.0
    years_to_retire: int
    target_corpus: float
    n_simulations: int = 10000


@router.post("/monte-carlo-retirement")
def monte_carlo_retirement(
    payload: MonteCarloInput,
    current_user: User = Depends(get_current_user),
):
    """
    Monte Carlo retirement simulation using historical Nifty 50 return distribution.
    
    Interview explanation:
    Instead of assuming a fixed 12% annual return (which gives false precision),
    we simulate 10,000 possible futures by drawing annual returns from the
    historical Nifty 50 distribution (mean ~14%, std ~18%).
    This gives a PROBABILITY of success rather than a single deterministic number.
    """
    if payload.n_simulations > 50000:
        payload.n_simulations = 10000

    # Historical Nifty 50 annual return statistics (1996-2024)
    NIFTY_MEAN = 0.14       # 14% mean annual return
    NIFTY_STD = 0.18        # 18% standard deviation
    MONTHS = payload.years_to_retire * 12
    MONTHLY_MEAN = NIFTY_MEAN / 12
    MONTHLY_STD = NIFTY_STD / np.sqrt(12)

    successes = 0
    all_final_corpus = []
    percentile_paths = {"p10": [], "p50": [], "p90": []}

    # Run simulations
    np.random.seed(42)  # reproducible results
    final_corpora = []

    for sim in range(payload.n_simulations):
        corpus = payload.current_corpus
        monthly_returns = np.random.normal(MONTHLY_MEAN, MONTHLY_STD, MONTHS)

        for monthly_return in monthly_returns:
            corpus = corpus * (1 + monthly_return) + payload.monthly_sip

        final_corpora.append(corpus)
        if corpus >= payload.target_corpus:
            successes += 1

    final_corpora = np.array(final_corpora)
    success_rate = successes / payload.n_simulations * 100

    # Percentile outcomes
    p10 = float(np.percentile(final_corpora, 10))
    p25 = float(np.percentile(final_corpora, 25))
    p50 = float(np.percentile(final_corpora, 50))
    p75 = float(np.percentile(final_corpora, 75))
    p90 = float(np.percentile(final_corpora, 90))

    def fmt(amt):
        if amt >= 1e7: return f"₹{amt/1e7:.1f}Cr"
        elif amt >= 1e5: return f"₹{amt/1e5:.1f}L"
        return f"₹{amt:,.0f}"

    # Recommendation
    if success_rate >= 90:
        recommendation = "Strong FIRE plan — you have a >90% chance of reaching your target."
    elif success_rate >= 70:
        recommendation = f"Good plan but consider increasing SIP by ₹{payload.monthly_sip * 0.2:,.0f}/month to reach 90% confidence."
    elif success_rate >= 50:
        recommendation = f"Moderate risk. Increase SIP by ₹{payload.monthly_sip * 0.4:,.0f}/month or extend timeline by 2-3 years."
    else:
        recommendation = "High risk of shortfall. Significantly increase SIP or reduce target corpus."

    return {
        "inputs": {
            "monthly_sip": payload.monthly_sip,
            "years_to_retire": payload.years_to_retire,
            "target_corpus": payload.target_corpus,
            "n_simulations": payload.n_simulations,
        },
        "results": {
            "success_rate_pct": round(success_rate, 1),
            "median_corpus": round(p50, 0),
            "median_corpus_readable": fmt(p50),
            "target_readable": fmt(payload.target_corpus),
            "percentiles": {
                "p10": round(p10, 0),
                "p25": round(p25, 0),
                "p50": round(p50, 0),
                "p75": round(p75, 0),
                "p90": round(p90, 0),
                "p10_readable": fmt(p10),
                "p50_readable": fmt(p50),
                "p90_readable": fmt(p90),
            },
        },
        "simulation_params": {
            "return_distribution": "Historical Nifty 50 (1996-2024)",
            "annual_mean_return": f"{NIFTY_MEAN*100:.0f}%",
            "annual_std_dev": f"{NIFTY_STD*100:.0f}%",
        },
        "recommendation": recommendation,
        "chart_data": {
            "histogram": np.histogram(final_corpora, bins=50)[0].tolist(),
            "bin_edges": [round(x, 0) for x in np.histogram(final_corpora, bins=50)[1].tolist()],
        }
    }


# ── Spending Forecast with MAE ─────────────────────────────────

@router.get("/spending-forecast")
def spending_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Forecast next month's spending per category using exponential smoothing.
    Measures MAE on the held-out last month for a real accuracy metric.
    """
    from app.models.models import Transaction, TransactionType
    from sqlalchemy import func, extract
    from collections import defaultdict

    uid = UUID(str(current_user.id))

    # Get monthly spending by category for last 6 months
    rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(
            Transaction.user_id == uid,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
        .group_by("year", "month", Transaction.category)
        .order_by("year", "month")
        .all()
    )

    # Organize by category → monthly series
    monthly_by_cat = defaultdict(dict)
    all_months = sorted(set(f"{int(r.year)}-{int(r.month):02d}" for r in rows))

    for r in rows:
        month_key = f"{int(r.year)}-{int(r.month):02d}"
        monthly_by_cat[r.category][month_key] = float(r.total)

    if len(all_months) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 months of data for forecasting. Upload more statements."
        )

    # Train on all months except last, validate on last
    train_months = all_months[:-1]
    validation_month = all_months[-1]
    next_month_date = datetime.strptime(all_months[-1] + "-01", "%Y-%m-%d")
    if next_month_date.month == 12:
        forecast_month = f"{next_month_date.year + 1}-01"
    else:
        forecast_month = f"{next_month_date.year}-{next_month_date.month + 1:02d}"

    forecasts = []
    total_mae = 0
    n_forecasted = 0

    for category, monthly_data in monthly_by_cat.items():
        series = [monthly_data.get(m, 0) for m in train_months]
        if len([s for s in series if s > 0]) < 2:
            continue

        # Simple exponential smoothing
        alpha = 0.3
        smoothed = series[0]
        for val in series[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed
        predicted = round(smoothed, 0)

        # Validation MAE
        actual_last = monthly_by_cat[category].get(validation_month, None)
        mae = abs(predicted - actual_last) if actual_last is not None else None

        if mae is not None:
            total_mae += mae
            n_forecasted += 1

        forecasts.append({
            "category": category,
            "predicted_amount": predicted,
            "last_month_actual": monthly_data.get(validation_month, 0),
            "mae": round(mae, 0) if mae is not None else None,
            "trend": "up" if predicted > (monthly_data.get(validation_month, predicted) or predicted) else "down",
        })

    forecasts.sort(key=lambda x: x["predicted_amount"], reverse=True)
    avg_mae = round(total_mae / n_forecasted, 0) if n_forecasted > 0 else None

    return {
        "forecast_month": forecast_month,
        "validation_month": validation_month,
        "model": "Exponential Smoothing (α=0.3)",
        "validation_mae": avg_mae,
        "validation_mae_note": f"Average ₹{avg_mae:,.0f} error per category on {validation_month} held-out validation",
        "forecasts": forecasts,
        "total_predicted": round(sum(f["predicted_amount"] for f in forecasts), 0),
    }
