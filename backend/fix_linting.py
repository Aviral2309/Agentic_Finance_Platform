# -*- coding: utf-8 -*-
"""
Run this script from backend/ folder to fix all remaining ruff errors.
python fix_linting.py
"""
import re

files_fixed = []

def fix_file(path, replacements):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        for old, new in replacements:
            content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        files_fixed.append(path)
        print(f"Fixed {path}")
    except Exception as e:
        print(f"Error fixing {path}: {e}")

# ── technical_analysis.py ──────────────────────────────────────
fix_file("app/ml/technical_analysis.py", [
    # Fix undefined ticker name
    (
        'return {"error": f"No valid price data for {yf_ticker}"}',
        'return {"error": f"No valid price data for {ticker}"}'
    ),
    # Fix math import position
    (
        "import logging\n",
        "import logging\nimport math\n"
    ),
    (
        "\nimport math\n\ndef _clean",
        "\n\ndef _clean"
    ),
    # Fix deep_clean indentation
    (
        "        return obj\n\n            result = _deep_clean(result)\n        return result",
        "        return obj\n\n    result = _deep_clean(result)\n    return result"
    ),
    # Expand one-liner ifs
    (
        "        if rsi < 40: bullish_signals += 1\n        elif rsi > 65: bearish_signals += 1",
        "        if rsi < 40:\n            bullish_signals += 1\n        elif rsi > 65:\n            bearish_signals += 1"
    ),
    (
        '        if macd["crossover"] in ["bullish_crossover", "bullish"]: bullish_signals += 1\n        elif macd["crossover"] in ["bearish_crossover", "bearish"]: bearish_signals += 1',
        '        if macd["crossover"] in ["bullish_crossover", "bullish"]:\n            bullish_signals += 1\n        elif macd["crossover"] in ["bearish_crossover", "bearish"]:\n            bearish_signals += 1'
    ),
    (
        '        if ma["trend"] == "bullish": bullish_signals += 1\n        elif ma["trend"] == "bearish": bearish_signals += 1',
        '        if ma["trend"] == "bullish":\n            bullish_signals += 1\n        elif ma["trend"] == "bearish":\n            bearish_signals += 1'
    ),
    (
        '        if bollinger["position"] == "below_lower": bullish_signals += 1\n        elif bollinger["position"] == "above_upper": bearish_signals += 1',
        '        if bollinger["position"] == "below_lower":\n            bullish_signals += 1\n        elif bollinger["position"] == "above_upper":\n            bearish_signals += 1'
    ),
    (
        '        if volume["signal"] == "accumulation": bullish_signals += 1\n        elif volume["signal"] == "distribution": bearish_signals += 1',
        '        if volume["signal"] == "accumulation":\n            bullish_signals += 1\n        elif volume["signal"] == "distribution":\n            bearish_signals += 1'
    ),
])

# ── insights.py ────────────────────────────────────────────────
fix_file("app/api/routes/insights.py", [
    (
        "    if taxable <= 250000: return 0\n    if taxable <= 500000: tax = (taxable - 250000) * 0.05\n    elif taxable <= 1000000: tax = 12500 + (taxable - 500000) * 0.20\n    else: tax = 112500 + (taxable - 1000000) * 0.30",
        "    if taxable <= 250000:\n        return 0\n    if taxable <= 500000:\n        tax = (taxable - 250000) * 0.05\n    elif taxable <= 1000000:\n        tax = 12500 + (taxable - 500000) * 0.20\n    else:\n        tax = 112500 + (taxable - 1000000) * 0.30"
    ),
    (
        "        if taxable <= prev: break",
        "        if taxable <= prev:\n            break"
    ),
    (
        "    if taxable <= 500000: return 0.05\n    elif taxable <= 1000000: return 0.20\n    else: return 0.30",
        "    if taxable <= 500000:\n        return 0.05\n    elif taxable <= 1000000:\n        return 0.20\n    else:\n        return 0.30"
    ),
])

# ── expenses.py ────────────────────────────────────────────────
fix_file("app/api/routes/expenses.py", [
    (
        "HITLQueue.is_resolved == False",
        "~HITLQueue.is_resolved"
    ),
])

# ── portfolio.py ───────────────────────────────────────────────
fix_file("app/api/routes/portfolio.py", [
    (
        "LSTMModel.is_production == True",
        "LSTMModel.is_production"
    ),
])

# ── advisor.py ─────────────────────────────────────────────────
fix_file("app/ml/advisor.py", [
    (
        "        last_3m = now - timedelta(days=90)\n",
        ""
    ),
    (
        "            Transaction.is_recurring == True,",
        "            Transaction.is_recurring,"
    ),
])

print(f"\nDone. Fixed {len(files_fixed)} files.")
print("Now run: python -m ruff check app/")