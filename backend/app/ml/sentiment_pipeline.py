"""
FinBERT sentiment pipeline.

Interview: why FinBERT over VADER?
VADER is trained on social media. 'Stock crashes record highs' → VADER says negative.
FinBERT is fine-tuned on WSJ/Reuters financial text → correctly reads as bullish.
Domain-specific model beats general model on domain-specific task. Always.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_finbert_pipeline = None


def _load_finbert():
    """Lazy load — only when first needed. Avoids startup delay."""
    global _finbert_pipeline
    if _finbert_pipeline is None:
        from transformers import pipeline as hf_pipeline
        logger.info("Loading FinBERT model...")
        _finbert_pipeline = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            top_k=None,  # return all class scores
        )
        logger.info("FinBERT loaded")
    return _finbert_pipeline


def analyze_headlines(headlines: list[str]) -> dict:
    """
    Classify a list of headlines and return aggregate sentiment.
    Returns: {label, score, per_headline_results}
    """
    if not headlines:
        return {"label": "neutral", "score": 0.5, "headlines": []}

    pipe = _load_finbert()

    # Truncate headlines to 512 tokens max (FinBERT limit)
    truncated = [h[:512] for h in headlines]

    results = pipe(truncated)

    # Aggregate: weighted average of positive/negative/neutral scores
    pos_scores, neg_scores, neu_scores = [], [], []

    per_headline = []
    for headline, result in zip(headlines, results):
        scores = {r["label"]: r["score"] for r in result}
        pos = scores.get("positive", 0)
        neg = scores.get("negative", 0)
        neu = scores.get("neutral", 0)
        pos_scores.append(pos)
        neg_scores.append(neg)
        neu_scores.append(neu)

        dominant = max(scores, key=scores.get)
        per_headline.append({
            "headline": headline,
            "label": dominant,
            "score": scores[dominant],
        })

    avg_pos = sum(pos_scores) / len(pos_scores)
    avg_neg = sum(neg_scores) / len(neg_scores)
    avg_neu = sum(neu_scores) / len(neu_scores)

    if avg_pos > avg_neg and avg_pos > avg_neu:
        label, score = "bullish", avg_pos
    elif avg_neg > avg_pos and avg_neg > avg_neu:
        label, score = "bearish", avg_neg
    else:
        label, score = "neutral", avg_neu

    return {
        "label": label,
        "score": round(score, 4),
        "headline_count": len(headlines),
        "top_headlines": [h["headline"] for h in sorted(per_headline, key=lambda x: x["score"], reverse=True)[:3]],
        "per_headline": per_headline,
    }


def fetch_and_analyze(ticker: str, news_api_key: str) -> Optional[dict]:
    """
    Fetch headlines via NewsAPI and run FinBERT.
    Called hourly by Celery beat for each held ticker.
    """
    if not news_api_key:
        logger.warning("NEWS_API_KEY not set — skipping sentiment")
        return None

    try:
        from newsapi import NewsApiClient
        api = NewsApiClient(api_key=news_api_key)

        # Clean ticker for search (remove .NS suffix)
        search_ticker = ticker.replace(".NS", "").replace(".BO", "")

        response = api.get_everything(
            q=search_ticker,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )

        articles = response.get("articles", [])
        headlines = [
            a["title"]
            for a in articles
            if a.get("title") and a["title"] != "[Removed]"
        ]

        if not headlines:
            return None

        result = analyze_headlines(headlines)
        result["ticker"] = ticker
        result["computed_at"] = datetime.utcnow().isoformat()
        return result

    except Exception as e:
        logger.error(f"Sentiment fetch failed for {ticker}: {e}")
        return None


# ── Celery task ────────────────────────────────────────────────

from app.core.celery_app import celery_app


@celery_app.task
def run_sentiment_for_all_users():
    """Hourly Celery beat task — runs FinBERT for all held tickers."""
    from app.core.database import SessionLocal
    from app.core.config import settings
    from app.models.models import PortfolioHolding, TickerSentiment, SentimentLabel

    db = SessionLocal()
    try:
        tickers = (
            db.query(PortfolioHolding.ticker)
            .distinct()
            .all()
        )
        tickers = [t[0] for t in tickers]

        for ticker in tickers:
            result = fetch_and_analyze(ticker, settings.NEWS_API_KEY)
            if not result:
                continue

            label_map = {"bullish": SentimentLabel.BULLISH, "bearish": SentimentLabel.BEARISH, "neutral": SentimentLabel.NEUTRAL}
            sentiment = TickerSentiment(
                ticker=ticker,
                label=label_map.get(result["label"], SentimentLabel.NEUTRAL),
                score=result["score"],
                headline_count=result["headline_count"],
                top_headlines=result["top_headlines"],
                computed_at=datetime.utcnow(),
            )
            db.add(sentiment)

        db.commit()
        logger.info(f"Sentiment updated for {len(tickers)} tickers")
    finally:
        db.close()
