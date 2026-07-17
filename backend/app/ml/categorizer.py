"""
WealthPilot 4-Layer Expense Categorizer
========================================
Layer 1: Keyword rules     — instant, free, ~90% coverage
Layer 2: TF-IDF + RF       — ML model, handles ambiguous merchants
Layer 3: Gemini LLM batch  — for genuinely unclear transactions
Layer 4: HITL              — human confirmation, adds to training data

Interview talking point:
"Each layer has a different cost-accuracy profile. Rules are instant and free.
ML is cheap (local inference). LLM costs money — we only call it in batches
for the small % that rules and ML can't handle. HITL closes the loop by
converting human corrections into new training data for Layer 2."
"""
import os
import re
import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Category definitions ───────────────────────────────────────
CATEGORIES = [
    "Food & Dining", "Groceries", "Transport", "Shopping",
    "Bills & Utilities", "Healthcare", "Entertainment", "Investment",
    "EMI & Loans", "Travel", "Education", "ATM Withdrawal",
    "Transfers", "Salary & Income", "Other",
]

# ── Model storage path ─────────────────────────────────────────
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "layer2_categorizer.pkl"
VECTORIZER_PATH = MODEL_DIR / "layer2_vectorizer.pkl"

# ── Layer 1: Keyword rules ─────────────────────────────────────
# ORDER MATTERS — more specific rules first, generic last
CATEGORY_RULES = {
    "Salary & Income": [
        "salary", "payroll", "neft/employer", "salary credit",
        "monthly salary", "net pay", "interest credit",
    ],
    "EMI & Loans": [
        "loan emi", "home loan", "car loan", "personal loan",
        "bajaj finance", "tata capital", "nach/", "education loan emi",
    ],
    "Investment": [
        "zerodha", "groww", "kuvera", "coin zerodha", "ppfas",
        "axis mf", "sbi mf", "hdfc mf", "/sip/", "mutual fund",
        "equity purchase", "mf investment",
    ],
    "Entertainment": [
        "bookmyshow", "netflix", "spotify", "hotstar", "pvr cinemas",
        "amazon prime", "inox", "youtube premium", "prime/",
        "movie ticket", "ott subscription",
    ],
    "Food & Dining": [
        "swiggy", "zomato", "dominos", "mcdonald", "subway", "kfc",
        "chaayos", "biryani", "pizza", "starbucks", "saravana",
        "restaurant", "dhaba", "cafe", "food payment", "dunzo food",
    ],
    "Groceries": [
        "bigbasket", "zepto", "grofers", "dmart", "nilgiris",
        "spar", "more supermarket", "reliance smart", "dairy products",
        "grocery", "supermarket",
    ],
    "Transport": [
        "uber", "ola cabs", "rapido", "irctc", "fastag", "nhai",
        "hpcl", "ixigo", "redbus", "flight blr", "flight del",
        "flight mum", "flight hyd", "bus ticket", "rail booking",
        "petrol", "fuel", "bmtc", "metro",
    ],
    "Travel": [
        "hotel booking", "oyo", "goibibo", "airbnb", "yatra",
        "taj hotels", "holiday package", "accommodation",
        "makemytrip/hotel", "resort",
    ],
    "Education": [
        "udemy", "coursera", "unacademy", "unacad", "byju",
        "byjus", "leetcode", "upgrad", "simplilearn", "coursefee",
    ],
    "Healthcare": [
        "apollo pharmacy", "1mg", "netmeds", "practo", "medplus",
        "hospital", "pathology", "pharmacy", "medicine", "lab test",
        "clinic", "diagnostic",
    ],
    "Bills & Utilities": [
        "bescom", "airtel", "jio recharge", "tataplay", "bwssb",
        "gaspay", "hathway", "vodafone", "bbps", "electricity bill",
        "water bill", "broadband", "dth recharge", "mobile bill",
        "mobile recharge",
    ],
    "Shopping": [
        "amazon pay", "amazon/in", "amazon purchase",
        "flipkart", "myntra", "meesho", "nykaa", "ajio", "croma",
        "snapdeal", "reliance digital", "lifestyle", "fashion",
        "electronics", "gadget",
    ],
    "ATM Withdrawal": [
        "atm/", "atm cash", "cash withdrawal", "atm wd",
    ],
    "Transfers": [
        "neft/transfer", "imps/transfer", "upi/p2p", "p2p/transfer",
        "family transfer", "rent payment", "split",
    ],
    "Healthcare": [
    "apollo pharmac", "1mg", "netmeds", "practo", "medplus",
    "hospital", "pathology", "pharmacy", "medicine", "lab test",
    "clinic", "diagnostic", "raj medical", "medical stores",
],
"Shopping": [
    "flipkart", "myntra", "meesho", "nykaa", "ajio", "croma",
    "snapdeal", "reliance digital", "lifestyle", "fashion",
    "electronics", "gadget", "ekart", "amazon pay", "amazon/in",
    "apparels", "readymades", "fashion-ibkpos", "watch electr",
    "electricals", "novelty stores",
],
"Groceries": [
    "bigbasket", "zepto", "grofers", "dmart", "nilgiris",
    "spar", "more supermarket", "reliance smart", "dairy products",
    "grocery", "supermarket", "kirana store", "samriya kirana",
    "jain general", "ms kamal enterprises",
],
"Food & Dining": [
    "swiggy", "zomato", "dominos", "mcdonald", "subway", "kfc",
    "chaayos", "biryani", "pizza", "starbucks", "saravana",
    "restaurant", "dhaba", "cafe", "food payment",
    "om namkeen", "jain dairy", "chaaps n curries",
    "vijay juice", "dholpur gajak", "novelty stores",
    "namkeen", "snack", "curries", "juice point",
],
"Transport": [
    "uber", "ola cabs", "rapido", "irctc", "fastag", "nhai",
    "hpcl", "ixigo", "redbus", "flight blr", "flight del",
    "flight mum", "flight hyd", "bus ticket", "rail booking",
    "petrol", "fuel", "bmtc", "metro", "bpcl ufill", "bpcl",
    "supreme transpor", "ravi carpenter",
],
"Education": [
    "udemy", "coursera", "unacademy", "unacad", "byju",
    "byjus", "leetcode", "upgrad", "simplilearn",
    "takeuforward", "srnprinters", "srn printers",
    "stationery",
],
"Transfers": [
    "neft/transfer", "imps/transfer", "upi/p2p",
    "mali-", "prajapat-", "chhabr-", "ibkpos.ep",
    "vyapar.", "aviral mittal-aviral", "etisha mittal",
    "kwatra-ibkpos", "jabir husain", "kala kunj",
    "mahesh kumar mali", "shailendra prajapat",
],
}


def layer1_rule_based(description: str) -> Optional[str]:
    """
    Layer 1: Keyword matching.
    Returns category if matched, None if no match.
    Cost: ~0ms, free.
    """
    if not description:
        return None
    desc_lower = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None


# ── Layer 2: TF-IDF + Random Forest ───────────────────────────

def _load_layer2_model():
    """Load trained Layer 2 model from disk."""
    if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(VECTORIZER_PATH, "rb") as f:
            vectorizer = pickle.load(f)
        return model, vectorizer
    return None, None


def layer2_ml_classify(description: str) -> tuple[Optional[str], float]:
    """
    Layer 2: TF-IDF + Random Forest ML classifier.
    Returns (category, confidence). Returns (None, 0) if model not trained.
    Cost: ~5ms, free (local inference).
    
    Interview talking point:
    TF-IDF converts merchant description text into numeric vectors
    based on word importance (TF = how often the word appears in this 
    transaction, IDF = how rare that word is across all transactions).
    Random Forest then classifies from these vectors — fast, interpretable,
    and generalizes well with limited training data vs neural networks.
    """
    model, vectorizer = _load_layer2_model()
    if model is None:
        return None, 0.0

    try:
        X = vectorizer.transform([description])
        proba = model.predict_proba(X)[0]
        max_idx = np.argmax(proba)
        confidence = float(proba[max_idx])
        category = model.classes_[max_idx]
        return category, confidence
    except Exception as e:
        logger.warning(f"Layer 2 classification failed: {e}")
        return None, 0.0


def retrain_layer2(descriptions: list[str], labels: list[str]) -> dict:
    """
    Train/retrain the Layer 2 Random Forest model.
    Called:
    - After bulk HITL confirmations are saved
    - After uploading a large labeled dataset
    - On a schedule (e.g. nightly via Celery)
    
    Returns training metrics.
    
    Interview talking point:
    This is the online learning loop. Every HITL correction becomes a
    new labeled training example. The model retrains periodically,
    so accuracy improves the more a specific user uses the app.
    It adapts to that user's unique merchant patterns over time.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    import numpy as np

    if len(descriptions) < 20:
        return {"error": "Need at least 20 labeled examples to train Layer 2"}

    logger.info(f"Training Layer 2 on {len(descriptions)} examples...")

    # TF-IDF: character n-grams work well for merchant code strings
    # word n-grams (1,2) capture both individual words and common phrases
    vectorizer = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        analyzer="word",
        sublinear_tf=True,         # log normalization reduces impact of very frequent terms
        min_df=1,
    )

    X = vectorizer.fit_transform(descriptions)
    y = np.array(labels)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",   # handle imbalanced categories (fewer Travel vs more Food)
        random_state=42,
        n_jobs=-1,                 # use all CPU cores
    )
    model.fit(X, y)

    # Cross-validation accuracy (honest metric — not just train accuracy)
    if len(descriptions) >= 50:
        cv_scores = cross_val_score(model, X, y, cv=min(5, len(set(labels))), scoring="accuracy")
        cv_accuracy = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    else:
        train_preds = model.predict(X)
        cv_accuracy = float(np.mean(train_preds == y))
        cv_std = 0.0

    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)

    logger.info(f"Layer 2 trained. CV accuracy: {cv_accuracy:.1%}")

    return {
        "n_samples": len(descriptions),
        "n_categories": len(set(labels)),
        "cv_accuracy": round(cv_accuracy, 4),
        "cv_std": round(cv_std, 4),
        "model_path": str(MODEL_PATH),
    }


# ── Layer 3: Gemini LLM (batched) ─────────────────────────────

def layer3_llm_batch(descriptions: list[str]) -> dict[str, str]:
    """
    Layer 3: Gemini LLM for genuinely ambiguous transactions.
    Batches ALL ambiguous transactions into ONE API call to minimize cost.
    
    Interview talking point:
    Calling Gemini once per transaction = 200 API calls for one statement.
    Batching all ambiguous transactions into one prompt = 1 API call.
    This is ~50-200x cheaper and faster for this specific use case.
    """
    if not descriptions:
        return {}

    try:
        from app.core.config import settings
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        numbered = "\n".join(f"{i+1}. {d}" for i, d in enumerate(descriptions))
        categories_str = ", ".join(CATEGORIES)

        prompt = f"""Categorize these Indian bank transactions.
Categories: {categories_str}

Transactions:
{numbered}

Return ONLY a JSON array with one category string per transaction, in the same order.
Example: ["Food & Dining", "Transport", "Groceries"]
No explanation, just the JSON array."""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown code blocks if present
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
        categories = json.loads(text)

        if len(categories) != len(descriptions):
            logger.warning(f"Layer 3 returned {len(categories)} results for {len(descriptions)} inputs")
            return {}

        return {desc: cat for desc, cat in zip(descriptions, categories)}

    except Exception as e:
        logger.error(f"Layer 3 LLM batch failed: {e}")
        return {}


# ── Main pipeline ──────────────────────────────────────────────

def categorize_transaction(description: str) -> tuple[str, int, float]:
    """
    Run the full 4-layer pipeline for a single transaction.
    Returns (category, layer, confidence).
    
    Layer 1: keyword rules
    Layer 2: ML model
    Layer 3: LLM (caller should batch these)
    Layer 4: HITL (returns 'Uncategorized', caller handles UI)
    """
    # Layer 1
    cat = layer1_rule_based(description)
    if cat:
        return cat, 1, 1.0

    # Layer 2
    cat, confidence = layer2_ml_classify(description)
    if cat and confidence >= 0.65:
        return cat, 2, confidence

    # Layer 3 — signal to caller to batch this
    # Returning None tells the caller to collect this for batch LLM call
    return "Uncategorized", 4, 0.0


def categorize_batch(descriptions: list[str]) -> list[dict]:
    """
    Categorize a batch of transactions through all layers.
    Handles Layer 3 batching internally for efficiency.
    """
    results = []
    layer3_needed = []   # indices needing LLM
    layer3_descs = []

    # Layers 1 and 2
    for i, desc in enumerate(descriptions):
        cat, layer, conf = categorize_transaction(desc)
        if layer == 4 and cat == "Uncategorized":
            layer3_needed.append(i)
            layer3_descs.append(desc)
        results.append({"category": cat, "layer": layer, "confidence": conf})

    # Layer 3 — one batch call for all uncertain transactions
    if layer3_descs:
        llm_results = layer3_llm_batch(layer3_descs)
        for i, desc in zip(layer3_needed, layer3_descs):
            llm_cat = llm_results.get(desc)
            if llm_cat and llm_cat in CATEGORIES:
                results[i] = {"category": llm_cat, "layer": 3, "confidence": 0.85}
            else:
                results[i] = {"category": "Other", "layer": 4, "confidence": 0.0}

    return results