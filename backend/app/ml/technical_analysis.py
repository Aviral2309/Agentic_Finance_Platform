"""
Technical Analysis Engine — replaces LSTM.

Computes RSI, MACD, Bollinger Bands, MA crossovers, volume analysis.
Runs in under 2 seconds. No training needed.
Then feeds results to Gemini for plain-English interpretation.

Interview answer: "We replaced LSTM forecasting with a technical analysis
engine — RSI, MACD, Bollinger Bands — because these give actionable
signals instantly without the noise of ML price prediction on short
timeframes. Gemini interprets the indicators in natural language."
"""
import logging
import math
import numpy as np

logger = logging.getLogger(__name__)


def _clean(val):
    """Replace nan/inf with None for JSON compliance."""
    if val is None:
        return None
    try:
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (TypeError, ValueError):
        return val

def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
    """RSI — momentum oscillator. >70 = overbought, <30 = oversold."""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_macd(prices: np.ndarray) -> dict:
    """MACD — trend following. Signal crossover = buy/sell signal."""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0, "crossover": "neutral"}

    def ema(data, period):
        alpha = 2 / (period + 1)
        result = [data[0]]
        for price in data[1:]:
            result.append(alpha * price + (1 - alpha) * result[-1])
        return np.array(result)

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line

    # Detect crossover in last 3 days
    crossover = "neutral"
    if len(histogram) >= 3:
        if histogram[-1] > 0 and histogram[-2] <= 0:
            crossover = "bullish_crossover"
        elif histogram[-1] < 0 and histogram[-2] >= 0:
            crossover = "bearish_crossover"
        elif histogram[-1] > histogram[-2]:
            crossover = "bullish"
        else:
            crossover = "bearish"

    return {
        "macd": round(float(macd_line[-1]), 4),
        "signal": round(float(signal_line[-1]), 4),
        "histogram": round(float(histogram[-1]), 4),
        "crossover": crossover,
    }


def compute_bollinger_bands(prices: np.ndarray, period: int = 20) -> dict:
    """Bollinger Bands — volatility indicator."""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "position": "middle", "bandwidth": 0}

    recent = prices[-period:]
    middle = np.mean(recent)
    std = np.std(recent)
    upper = middle + 2 * std
    lower = middle - 2 * std
    current = prices[-1]

    # Where is current price relative to bands?
    if current > upper:
        position = "above_upper"  # potentially overbought
    elif current < lower:
        position = "below_lower"  # potentially oversold
    elif current > middle:
        position = "upper_half"
    else:
        position = "lower_half"

    bandwidth = round((upper - lower) / middle * 100, 2)

    return {
        "upper": round(float(upper), 2),
        "middle": round(float(middle), 2),
        "lower": round(float(lower), 2),
        "position": position,
        "bandwidth": bandwidth,
    }


def compute_moving_averages(prices: np.ndarray) -> dict:
    """50-day and 200-day MA. Golden cross = bullish, Death cross = bearish."""
    result = {}

    for period in [20, 50, 200]:
        if len(prices) >= period:
            result[f"ma{period}"] = round(float(np.mean(prices[-period:])), 2)
        else:
            result[f"ma{period}"] = None

    current = float(prices[-1]) if len(prices) > 0 else 0.0
    result["current"] = round(current, 2)

    # Golden/Death cross
    if result["ma50"] and result["ma200"]:
        if result["ma50"] > result["ma200"]:
            result["trend"] = "bullish"
            result["cross_signal"] = "golden_cross" if len(prices) >= 200 else "above_ma200"
        else:
            result["trend"] = "bearish"
            result["cross_signal"] = "death_cross" if len(prices) >= 200 else "below_ma200"
    elif result["ma50"]:
        result["trend"] = "bullish" if current > result["ma50"] else "bearish"
        result["cross_signal"] = "above_ma50" if current > result["ma50"] else "below_ma50"
    else:
        result["trend"] = "neutral"
        result["cross_signal"] = "insufficient_data"

    return result


def compute_volume_analysis(volumes: np.ndarray, prices: np.ndarray) -> dict:
    """Volume trend — high volume on up days = accumulation."""
    if len(volumes) < 10:
        return {"avg_volume": 0, "volume_trend": "neutral", "signal": "neutral"}

    avg_vol = float(np.mean(volumes[-20:]))
    recent_vol = float(volumes[-1])
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

    # Price direction on high volume days (last 5 days)
    up_vol = 0
    down_vol = 0
    for i in range(-5, 0):
        if len(prices) > abs(i) and len(volumes) > abs(i):
            if prices[i] > prices[i-1]:
                up_vol += volumes[i]
            else:
                down_vol += volumes[i]

    if up_vol > down_vol * 1.5:
        signal = "accumulation"
    elif down_vol > up_vol * 1.5:
        signal = "distribution"
    else:
        signal = "neutral"

    return {
        "avg_volume": round(avg_vol),
        "current_volume": round(recent_vol),
        "volume_ratio": round(vol_ratio, 2),
        "signal": signal,
    }


def compute_support_resistance(prices: np.ndarray) -> dict:
    """Simple support/resistance from recent highs/lows."""
    if len(prices) < 20:
        return {"support": 0, "resistance": 0}

    recent = prices[-52:] if len(prices) >= 52 else prices
    return {
        "support": round(float(np.min(recent)), 2),
        "resistance": round(float(np.max(recent)), 2),
        "week52_low": round(float(np.min(prices[-252:])) if len(prices) >= 252 else float(np.min(prices)), 2),
        "week52_high": round(float(np.max(prices[-252:])) if len(prices) >= 252 else float(np.max(prices)), 2),
    }

def analyse_ticker(ticker: str) -> dict:
    """
    Main function — computes all technical indicators for a ticker.
    Returns structured data + Gemini interpretation.
    """
    import yfinance as yf
    import pandas as pd

    yf_ticker = f"{ticker}.NS" if not ticker.endswith((".NS", ".BO")) else ticker

    try:
        data = yf.download(yf_ticker, period="1y", progress=False)

        # Fix MultiIndex columns from newer yfinance versions
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if data.empty or len(data) < 20:
            return {"error": f"Insufficient data for {ticker}"}

        prices = data["Close"].values.astype(float).flatten()
        volumes = data["Volume"].values.astype(float).flatten()
        current_price = float(prices[-1])

        # Compute all indicators
        rsi = compute_rsi(prices)
        macd = compute_macd(prices)
        bollinger = compute_bollinger_bands(prices)
        ma = compute_moving_averages(prices)
        volume = compute_volume_analysis(volumes, prices)
        sr = compute_support_resistance(prices)

        # Overall signal
        bullish_signals = 0
        bearish_signals = 0

        if rsi < 40:
            bullish_signals += 1
        elif rsi > 65:
            bearish_signals += 1

        if macd["crossover"] in ["bullish_crossover", "bullish"]:
            bullish_signals += 1
        elif macd["crossover"] in ["bearish_crossover", "bearish"]:
            bearish_signals += 1

        if ma["trend"] == "bullish":
            bullish_signals += 1
        elif ma["trend"] == "bearish":
            bearish_signals += 1

        if bollinger["position"] == "below_lower":
            bullish_signals += 1
        elif bollinger["position"] == "above_upper":
            bearish_signals += 1

        if volume["signal"] == "accumulation":
            bullish_signals += 1
        elif volume["signal"] == "distribution":
            bearish_signals += 1

        if bullish_signals >= 3:
            overall_signal = "bullish"
        elif bearish_signals >= 3:
            overall_signal = "bearish"
        else:
            overall_signal = "neutral"

        result = {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "rsi": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "moving_averages": ma,
            "volume": volume,
            "support_resistance": sr,
            "overall_signal": overall_signal,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "data_points": len(prices),
        }

        result["interpretation"] = get_gemini_interpretation(ticker, result)
        def _deep_clean(obj):
            if isinstance(obj, dict):
                return {k: _deep_clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_deep_clean(v) for v in obj]
            elif isinstance(obj, float):
                return _clean(obj)
            return obj

        result = _deep_clean(result)
        return result

    except Exception as e:
        logger.error(f"Technical analysis failed for {ticker}: {e}")
        return {"error": str(e), "ticker": ticker}


def get_gemini_interpretation(ticker: str, analysis: dict) -> str:
    from app.core.config import settings
    
    if not settings.GEMINI_API_KEY:
        return _rule_based_interpretation(analysis)

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        sr = analysis.get("support_resistance", {})
        ma = analysis.get("moving_averages", {})
        vol = analysis.get("volume", {})
        bb = analysis.get("bollinger", {})

        prompt = f"""Analyse this stock for an Indian retail investor. Be specific and direct.

Stock: {ticker}
Current Price: ₹{analysis.get('current_price', 'N/A')}
52W Range: ₹{sr.get('week52_low', 'N/A')} — ₹{sr.get('week52_high', 'N/A')}

Technical Indicators:
- RSI (14): {analysis.get('rsi', 'N/A')} {'(oversold)' if (analysis.get('rsi') or 50) < 35 else '(overbought)' if (analysis.get('rsi') or 50) > 70 else '(neutral)'}
- MACD: {analysis.get('macd', {}).get('crossover', 'N/A')}
- Trend: {ma.get('trend', 'N/A')} | 50MA: ₹{ma.get('ma50', 'N/A')} | 200MA: ₹{ma.get('ma200', 'N/A')}
- Bollinger: {bb.get('position', 'N/A')}
- Volume: {vol.get('signal', 'N/A')}
- Support: ₹{sr.get('support', 'N/A')} | Resistance: ₹{sr.get('resistance', 'N/A')}
- Overall signal: {analysis.get('overall_signal', 'N/A').upper()}

Give exactly 3 bullet points:
- Current technical position
- Key risk or opportunity  
- What to watch next

Be specific with ₹ levels. Max 60 words total."""

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.warning(f"Gemini interpretation failed: {e}")
        return _rule_based_interpretation(analysis)


def _rule_based_interpretation(analysis: dict) -> str:
    """Fallback when Gemini is not available."""
    rsi = analysis.get("rsi", 50)
    signal = analysis.get("overall_signal", "neutral")
    ma = analysis.get("moving_averages", {})

    parts = []

    if rsi < 35:
        parts.append(f"RSI at {rsi} indicates oversold territory — potential bounce possible.")
    elif rsi > 70:
        parts.append(f"RSI at {rsi} signals overbought — consider reducing exposure.")
    else:
        parts.append(f"RSI at {rsi} is in neutral range.")

    if ma.get("trend") == "bullish":
        parts.append("Price is above key moving averages — uptrend intact.")
    else:
        parts.append("Price is below key moving averages — downtrend in progress.")

    parts.append(f"Overall signal: {signal.upper()}.")
    return " ".join(parts)
