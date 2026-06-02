"""
4-layer expense categorizer.

Layer 1: Merchant keyword rules     → ~60% coverage, free, instant
Layer 2: TF-IDF + Random Forest     → ~25% coverage, cheap
Layer 3: Gemini LLM batch call      → ~10% coverage, costs money
Layer 4: Human-in-the-loop (HITL)   → remaining ~5%

Interview answer: Each layer has a different cost-accuracy profile.
Rules are free. ML is cheap. LLM only for genuine ambiguity.
Every HITL confirmation retrains Layer 2 monthly (online learning).
"""
import re
import os
import joblib
import logging
from functools import lru_cache
from typing import Optional
from pathlib import Path

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

logger = logging.getLogger(__name__)

MODEL_PATH = Path("models/categorizer.joblib")
CONFIDENCE_THRESHOLD = 0.75   # below this → Layer 3 or HITL
CATEGORIES = [
    "Food & Dining", "Groceries", "Transport", "Shopping",
    "Entertainment", "Bills & Utilities", "Healthcare",
    "Education", "Travel", "EMI & Loans", "Investment",
    "Salary & Income", "Transfers", "ATM Withdrawal", "Other",
]

# ── Layer 1: Merchant keyword rules ───────────────────────────
# Keys are lowercase regex patterns, values are categories.
# Order matters — first match wins.
MERCHANT_RULES: dict[str, str] = {
    # Food delivery
    r"swiggy|zomato|dunzo|eatsure|faasos|box8": "Food & Dining",
    # Restaurants / cafes
    r"mcdonald|kfc|domino|pizza|burger|cafe|restaurant|hotel|dhaba|biryani|darbar": "Food & Dining",
    # Groceries
    r"bigbasket|blinkit|grofers|jiomart|dmart|reliance fresh|more supermarket|nature.s basket|kirana": "Groceries",
    r"zepto|instamart|swiggy instamart": "Groceries",
    # Transport
    r"uber|ola|rapido|meru|blumart|yulu|bounce": "Transport",
    r"metro|dmrc|bmtc|best bus|apsrtc|ksrtc|msrtc": "Transport",
    r"petrol|fuel|indian oil|hp pump|bharat petroleum|shell": "Transport",
    # Travel
    r"irctc|makemytrip|goibibo|cleartrip|yatra|easemytrip|ixigo": "Travel",
    r"indigo|air india|spicejet|vistara|akasa|go first": "Travel",
    r"oyo|treebo|fabhotel|hotel|inn|resort|airbnb": "Travel",
    # Shopping
    r"amazon|flipkart|myntra|ajio|meesho|nykaa|tata cliq|snapdeal|shopclues": "Shopping",
    r"max fashion|pantaloons|westside|h&m|zara|lifestyle|shopper.s stop": "Shopping",
    # Entertainment
    r"netflix|prime video|hotstar|zee5|sony liv|jiocinema|mxplayer": "Entertainment",
    r"spotify|gaana|wynk|jiosaavn|apple music|youtube premium": "Entertainment",
    r"pvr|inox|cinepolis|bookmyshow": "Entertainment",
    # Bills
    r"electricity|bescom|tata power|adani electric|mseb|cesc|tneb": "Bills & Utilities",
    r"airtel|jio|vi |vodafone|bsnl|act broadband|hathway": "Bills & Utilities",
    r"gas|mahanagar gas|indraprastha gas|gujarat gas": "Bills & Utilities",
    r"water|bwssb|mcgm|bbmp": "Bills & Utilities",
    # Healthcare
    r"hospital|clinic|pharmacy|medplus|apollo|1mg|pharmeasy|netmeds|practo": "Healthcare",
    r"doctor|dentist|optician|diagnostic|pathlab|thyrocare": "Healthcare",
    # Education
    r"byju|unacademy|coursera|udemy|vedantu|toppr|collegedunia|upgrad": "Education",
    r"school fee|college fee|tuition|library": "Education",
    # EMI / Loans
    r"emi|loan|bajaj finance|hdfc loan|icici loan|axis loan|lic|nps": "EMI & Loans",
    # Investment
    r"zerodha|groww|upstox|angel broking|kuvera|paytm money|mf|sip|mutual fund": "Investment",
    r"ppf|elss|fd|fixed deposit|rd|recurring deposit": "Investment",
    # ATM
    r"atm|cash withdrawal|cash wdl": "ATM Withdrawal",
    # Transfers
    r"neft|rtgs|imps|upi|transfer|sent to|received from|payment to": "Transfers",
    # Salary
    r"salary|payroll|stipend|bonus|incentive|reimbursement": "Salary & Income",
}

# Pre-compile for speed
_COMPILED_RULES = [
    (re.compile(pattern, re.IGNORECASE), category)
    for pattern, category in MERCHANT_RULES.items()
]


@lru_cache(maxsize=10_000)
def _layer1_cached(description: str) -> Optional[str]:
    """
    Cache is per merchant description string.
    10,000 entries covers typical user's merchant universe many times over.
    Interview: same merchant never re-classified — O(1) after first hit.
    """
    for pattern, category in _COMPILED_RULES:
        if pattern.search(description):
            return category
    return None


def layer1_rule_based(description: str) -> Optional[str]:
    return _layer1_cached(description.lower().strip())


# ── Layer 2: TF-IDF + Random Forest ───────────────────────────

def _build_feature_string(description: str, amount: float, hour: int, day_of_week: int) -> str:
    """
    Combine text + numeric signals into one string for TF-IDF.
    Interview: amount + time are strong signals — ₹40 at 8PM is food,
    ₹40,000 at 10AM is likely EMI or investment.
    """
    amount_bucket = (
        "tiny" if amount < 100 else
        "small" if amount < 500 else
        "medium" if amount < 2000 else
        "large" if amount < 10000 else
        "very_large"
    )
    time_period = (
        "early_morning" if hour < 6 else
        "morning" if hour < 12 else
        "afternoon" if hour < 17 else
        "evening" if hour < 21 else
        "night"
    )
    day_type = "weekend" if day_of_week >= 5 else "weekday"
    return f"{description} amount_{amount_bucket} time_{time_period} {day_type}"


def layer2_ml(
    description: str,
    amount: float,
    hour: int,
    day_of_week: int,
) -> tuple[Optional[str], float]:
    """Returns (category, confidence). Falls through if model not trained."""
    model = _load_model()
    if model is None:
        return None, 0.0
    feature_str = _build_feature_string(description, amount, hour, day_of_week)
    proba = model.predict_proba([feature_str])[0]
    confidence = float(np.max(proba))
    predicted = model.classes_[np.argmax(proba)]
    return predicted, confidence


def _load_model() -> Optional[Pipeline]:
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            logger.warning(f"Could not load categorizer model: {e}")
    return None


def train_classifier(
    descriptions: list[str],
    amounts: list[float],
    hours: list[int],
    days: list[int],
    labels: list[str],
) -> dict:
    """
    Train/retrain the Random Forest classifier.
    Called monthly by Celery beat using HITL-confirmed labels.
    Returns evaluation metrics.
    """
    if len(labels) < 50:
        return {"error": "Need at least 50 labeled samples to train"}

    features = [
        _build_feature_string(d, a, h, dw)
        for d, a, h, dw in zip(descriptions, amounts, hours, days)
    ]

    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            min_df=2,
        )),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    logger.info(f"Categorizer retrained. Weighted F1: {report['weighted avg']['f1-score']:.3f}")

    return {
        "weighted_f1": report["weighted avg"]["f1-score"],
        "accuracy": report["accuracy"],
        "samples_trained": len(X_train),
    }


# ── Layer 3: Gemini batch call ─────────────────────────────────

async def layer3_llm_batch(
    transactions: list[dict],
    gemini_api_key: str,
) -> list[Optional[str]]:
    """
    Single Gemini call for all ambiguous transactions.
    Interview: batching cuts LLM cost ~50x vs one call per transaction.
    """
    if not transactions:
        return []

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        tx_list = "\n".join([
            f"{i+1}. Amount: ₹{t['amount']}, Description: {t['description']}, "
            f"Time: {t['hour']}:00, Day: {t['day_of_week']}"
            for i, t in enumerate(transactions)
        ])

        categories_str = ", ".join(CATEGORIES)
        prompt = f"""Categorize each transaction into exactly one category from this list:
{categories_str}

Transactions:
{tx_list}

Reply ONLY with a JSON array of category strings in the same order.
Example: ["Food & Dining", "Transport", "Bills & Utilities"]
No explanation. No markdown. Just the JSON array."""

        response = model.generate_content(prompt)
        import json
        # Strip any markdown fences if present
        text = response.text.strip().strip("```json").strip("```").strip()
        result = json.loads(text)
        return result if isinstance(result, list) else [None] * len(transactions)

    except Exception as e:
        logger.error(f"Layer 3 LLM failed: {e}")
        return [None] * len(transactions)


# ── Main pipeline ──────────────────────────────────────────────

async def categorize_transaction(
    description: str,
    amount: float,
    hour: int,
    day_of_week: int,
    gemini_api_key: str = "",
) -> dict:
    """
    Run a single transaction through all layers.
    Returns: {category, layer, confidence, needs_hitl}
    """
    # Layer 1
    cat = layer1_rule_based(description)
    if cat:
        return {"category": cat, "layer": 1, "confidence": 1.0, "needs_hitl": False}

    # Layer 2
    cat, confidence = layer2_ml(description, amount, hour, day_of_week)
    if cat and confidence >= CONFIDENCE_THRESHOLD:
        return {"category": cat, "layer": 2, "confidence": confidence, "needs_hitl": False}

    # Layer 3 — caller should batch these, but handle single case
    if gemini_api_key:
        llm_results = await layer3_llm_batch(
            [{"description": description, "amount": amount, "hour": hour, "day_of_week": day_of_week}],
            gemini_api_key,
        )
        if llm_results and llm_results[0]:
            return {"category": llm_results[0], "layer": 3, "confidence": 0.8, "needs_hitl": False}

    # Layer 4 — HITL
    suggested = cat or "Other"
    return {"category": suggested, "layer": 4, "confidence": confidence or 0.0, "needs_hitl": True}


async def categorize_batch(
    transactions: list[dict],
    gemini_api_key: str = "",
) -> list[dict]:
    """
    Categorize a list of transactions efficiently.
    Batches Layer 3 calls to minimize LLM API costs.
    """
    results = []
    llm_needed_indices = []
    llm_needed_txns = []

    for i, tx in enumerate(transactions):
        desc = tx.get("description", "")
        amount = tx.get("amount", 0)
        hour = tx.get("hour", 12)
        dow = tx.get("day_of_week", 0)

        # Layer 1
        cat = layer1_rule_based(desc)
        if cat:
            results.append({"category": cat, "layer": 1, "confidence": 1.0, "needs_hitl": False})
            continue

        # Layer 2
        cat, confidence = layer2_ml(desc, amount, hour, dow)
        if cat and confidence >= CONFIDENCE_THRESHOLD:
            results.append({"category": cat, "layer": 2, "confidence": confidence, "needs_hitl": False})
            continue

        # Queue for Layer 3 batch
        results.append(None)  # placeholder
        llm_needed_indices.append(i)
        llm_needed_txns.append({"description": desc, "amount": amount, "hour": hour, "day_of_week": dow})

    # Single batch LLM call
    if llm_needed_txns and gemini_api_key:
        llm_results = await layer3_llm_batch(llm_needed_txns, gemini_api_key)
        for idx, llm_cat in zip(llm_needed_indices, llm_results):
            if llm_cat:
                results[idx] = {"category": llm_cat, "layer": 3, "confidence": 0.8, "needs_hitl": False}
            else:
                tx = transactions[idx]
                _, conf = layer2_ml(tx.get("description",""), tx.get("amount",0), tx.get("hour",12), tx.get("day_of_week",0))
                results[idx] = {"category": "Other", "layer": 4, "confidence": conf or 0.0, "needs_hitl": True}
    else:
        # No Gemini key — send remaining to HITL
        for idx in llm_needed_indices:
            if results[idx] is None:
                tx = transactions[idx]
                _, conf = layer2_ml(tx.get("description",""), tx.get("amount",0), tx.get("hour",12), tx.get("day_of_week",0))
                results[idx] = {"category": "Other", "layer": 4, "confidence": conf or 0.0, "needs_hitl": True}

    return results
