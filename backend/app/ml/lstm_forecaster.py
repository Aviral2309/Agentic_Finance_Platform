"""
LSTM price forecaster.

Architecture: 2-layer LSTM → Linear(50 → 1)
Input: 60-day sliding window of normalized OHLCV + technical indicators
Output: next-day price, repeated for 7/30 day forecasts

Interview answers:
- Why 60-day window? Balances short-term momentum and medium-term trend
- Why Monte Carlo dropout? Uncertainty quantification without full Bayesian network
- Why not Transformer? LSTM is simpler to explain, lighter to train, sufficient for demo
- MLflow: every run logged — loss curve, hyperparams, MAE, model artifact
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import numpy as np

import mlflow
import mlflow.pytorch
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

WINDOW_SIZE = 60
HIDDEN_SIZE = 50
NUM_LAYERS = 2
DROPOUT = 0.2
BATCH_SIZE = 32
MAX_EPOCHS = 100
PATIENCE = 10          # early stopping
MC_SAMPLES = 20        # Monte Carlo forward passes for confidence band
MODEL_DIR = Path("models/lstm")


# ── Model definition ───────────────────────────────────────────

class LSTMForecaster(nn.Module):
    """
    2-layer LSTM with dropout.
    Dropout stays ON during inference for Monte Carlo uncertainty estimation.
    """
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        last_out = lstm_out[:, -1, :]   # take last time step
        out = self.dropout(last_out)
        return self.fc(out).squeeze(-1)


# ── Feature engineering ────────────────────────────────────────

def _build_features(df) -> np.ndarray:
    """
    5 features per time step: normalized close, volume, 5-day MA, 20-day MA, RSI.
    All normalized to [0,1] within the window to remove price-level dependency.

    Interview: feature engineering is as important as architecture choice.
    Raw OHLCV without normalization makes the LSTM memorize price levels, not patterns.
    """
    close = df["Close"].values.astype(float)
    volume = df["Volume"].values.astype(float)

    # Moving averages
    ma5 = _rolling_mean(close, 5)
    ma20 = _rolling_mean(close, 20)

    # RSI (14-period)
    rsi = _compute_rsi(close, 14)

    features = np.column_stack([close, volume, ma5, ma20, rsi])

    # Normalize each feature column to [0,1] across the dataset
    mins = features.min(axis=0)
    maxs = features.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1  # prevent division by zero
    features = (features - mins) / ranges

    return features, mins, maxs


def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    result = np.zeros_like(arr)
    for i in range(len(arr)):
        start = max(0, i - window + 1)
        result[i] = arr[start:i+1].mean()
    return result


def _compute_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    rsi = np.zeros_like(prices)
    deltas = np.diff(prices, prepend=prices[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = _rolling_mean(gains, period)
    avg_loss = _rolling_mean(losses, period)
    avg_loss[avg_loss == 0] = 1e-10

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi / 100  # normalize to [0,1]


def _create_sequences(features: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(features) - window):
        X.append(features[i:i+window])
        y.append(features[i+window, 0])  # predict normalized close price
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ── Training ───────────────────────────────────────────────────

def train(ticker: str, existing_mae: Optional[float] = None) -> dict:
    """
    Download data, engineer features, train LSTM, log to MLflow.
    Only promotes model if val_MAE < existing production model MAE.

    Returns metadata dict — stored in lstm_models table.
    """
    import yfinance as yf

    logger.info(f"Training LSTM for {ticker}")

    # NSE tickers need .NS suffix
    yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker

    df = yf.download(yf_ticker, period="2y", progress=False)
    if df.empty or len(df) < WINDOW_SIZE + 30:
        raise ValueError(f"Insufficient data for {ticker}: {len(df)} rows")

    features, feat_mins, feat_maxs = _build_features(df)
    X, y = _create_sequences(features, WINDOW_SIZE)

    # 80/20 train/val split — no shuffle (time series!)
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=BATCH_SIZE, shuffle=True,
    )

    model = LSTMForecaster(
        input_size=X.shape[2],
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    mlflow.set_tracking_uri("sqlite:///mlflow.db")

    with mlflow.start_run(run_name=f"lstm_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        mlflow.log_params({
            "ticker": ticker,
            "window_size": WINDOW_SIZE,
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "dropout": DROPOUT,
            "batch_size": BATCH_SIZE,
        })

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        for epoch in range(MAX_EPOCHS):
            # Training
            model.train()
            train_loss = 0.0
            for xb, yb in train_loader:
                optimizer.zero_grad()
                pred = model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)

            # Validation
            model.eval()
            with torch.no_grad():
                val_pred = model(torch.from_numpy(X_val))
                val_loss = criterion(val_pred, torch.from_numpy(y_val)).item()
                val_mae_norm = float(torch.mean(torch.abs(val_pred - torch.from_numpy(y_val))).item())

            mlflow.log_metrics({
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_mae_normalized": val_mae_norm,
            }, step=epoch)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

        # Load best weights
        model.load_state_dict(best_state)

        # Compute MAE in real price terms
        model.eval()
        with torch.no_grad():
            val_pred_norm = model(torch.from_numpy(X_val)).numpy()

        # Denormalize close price
        close_range = feat_maxs[0] - feat_mins[0]
        if close_range == 0:
            close_range = 1
        val_pred_real = val_pred_norm * close_range + feat_mins[0]
        val_true_real = y_val * close_range + feat_mins[0]
        val_mae_real = float(np.mean(np.abs(val_pred_real - val_true_real)))
        avg_price = float(np.mean(val_true_real))
        val_mae_pct = (val_mae_real / avg_price) * 100

        mlflow.log_metrics({"val_mae_real": val_mae_real, "val_mae_pct": val_mae_pct})

        # Save model if better than existing production
        should_promote = existing_mae is None or val_mae_pct < existing_mae
        run_id = mlflow.active_run().info.run_id

        if should_promote:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            model_path = MODEL_DIR / f"{ticker}.pt"
            # Save model + normalization params together
            torch.save({
                "state_dict": model.state_dict(),
                "feat_mins": feat_mins,
                "feat_maxs": feat_maxs,
                "input_size": X.shape[2],
            }, model_path)
            mlflow.pytorch.log_model(model, "model")
            logger.info(f"Promoted {ticker} model. MAE: {val_mae_pct:.2f}%")

        return {
            "ticker": ticker,
            "model_path": str(MODEL_DIR / f"{ticker}.pt") if should_promote else None,
            "val_mae": val_mae_real,
            "val_mae_pct": val_mae_pct,
            "mlflow_run_id": run_id,
            "promoted": should_promote,
        }


# ── Inference with Monte Carlo dropout ────────────────────────

def forecast(ticker: str, days: int = 30) -> dict:
    """
    Generate forecast with uncertainty bands.

    Monte Carlo dropout: run inference 20 times with dropout ON.
    Mean = forecast, ±1σ = confidence band.

    Interview: this gives uncertainty quantification without
    a full Bayesian network — practical approximation.
    """
    import yfinance as yf

    model_path = MODEL_DIR / f"{ticker}.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model for {ticker}. Train first.")

    checkpoint = torch.load(model_path, map_location="cpu")
    feat_mins = checkpoint["feat_mins"]
    feat_maxs = checkpoint["feat_maxs"]
    input_size = checkpoint["input_size"]

    model = LSTMForecaster(
        input_size=input_size,
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        dropout=DROPOUT,
    )
    model.load_state_dict(checkpoint["state_dict"])
    model.train()  # Keep dropout ON for Monte Carlo sampling

    yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker
    df = yf.download(yf_ticker, period="6mo", progress=False)
    if df.empty:
        raise ValueError(f"No recent data for {ticker}")

    features, _, _ = _build_features(df)
    last_window = features[-WINDOW_SIZE:]  # most recent 60 days
    current_price = float(df["Close"].iloc[-1])

    # Monte Carlo: run MC_SAMPLES forward passes
    all_forecasts = []
    with torch.no_grad():
        for _ in range(MC_SAMPLES):
            window = last_window.copy()
            predictions = []
            for _ in range(days):
                x = torch.FloatTensor(window).unsqueeze(0)  # (1, 60, 5)
                pred_norm = model(x).item()

                # Denormalize
                close_range = feat_maxs[0] - feat_mins[0]
                if close_range == 0:
                    close_range = 1
                pred_price = pred_norm * close_range + feat_mins[0]
                predictions.append(pred_price)

                # Slide window forward
                new_row = window[-1].copy()
                new_row[0] = pred_norm  # update normalized close
                window = np.vstack([window[1:], new_row])

            all_forecasts.append(predictions)

    all_forecasts = np.array(all_forecasts)  # (MC_SAMPLES, days)
    mean_forecast = all_forecasts.mean(axis=0)
    std_forecast = all_forecasts.std(axis=0)

    # Build output
    forecast_dates = [
        (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
        for i in range(days)
    ]

    points = [
        {
            "date": d,
            "predicted_price": round(float(m), 2),
            "lower_band": round(float(m - std_forecast[i]), 2),
            "upper_band": round(float(m + std_forecast[i]), 2),
        }
        for i, (d, m) in enumerate(zip(forecast_dates, mean_forecast))
    ]

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "forecast_7d": points[:7],
        "forecast_30d": points[:30],
    }
