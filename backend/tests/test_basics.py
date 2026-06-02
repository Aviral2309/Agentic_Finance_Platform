"""
Basic tests — run with: pytest tests/ -v
These tests verify core logic without needing a real database.
"""
import pytest
from app.ml.categorizer import layer1_rule_based, categorize_batch
import asyncio


# ── Layer 1 tests ──────────────────────────────────────────────

def test_swiggy_categorized_as_food():
    assert layer1_rule_based("SWIGGY ORDER 123456") == "Food & Dining"


def test_uber_categorized_as_transport():
    assert layer1_rule_based("UBER TRIP MUMBAI") == "Transport"


def test_netflix_categorized_as_entertainment():
    assert layer1_rule_based("NETFLIX SUBSCRIPTION") == "Entertainment"


def test_irctc_categorized_as_travel():
    assert layer1_rule_based("IRCTC TICKET BOOKING") == "Travel"


def test_amazon_categorized_as_shopping():
    assert layer1_rule_based("Amazon.in order") == "Shopping"


def test_salary_categorized_correctly():
    assert layer1_rule_based("SALARY CREDIT INFOSYS") == "Salary & Income"


def test_unknown_returns_none():
    result = layer1_rule_based("XYZ RANDOM MERCHANT 999")
    assert result is None


def test_case_insensitive():
    assert layer1_rule_based("swiggy order") == layer1_rule_based("SWIGGY ORDER")


# ── Batch categorizer tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_categorizer_layer1():
    transactions = [
        {"description": "SWIGGY ORDER", "amount": 350, "hour": 20, "day_of_week": 2},
        {"description": "UBER TRIP", "amount": 180, "hour": 9, "day_of_week": 1},
        {"description": "NETFLIX SUB", "amount": 199, "hour": 10, "day_of_week": 0},
    ]
    results = await categorize_batch(transactions, gemini_api_key="")
    assert results[0]["category"] == "Food & Dining"
    assert results[0]["layer"] == 1
    assert results[1]["category"] == "Transport"
    assert results[2]["category"] == "Entertainment"


@pytest.mark.asyncio
async def test_batch_returns_result_for_each_input():
    transactions = [
        {"description": "RANDOM UNKNOWN MERCHANT", "amount": 100, "hour": 12, "day_of_week": 3},
    ]
    results = await categorize_batch(transactions, gemini_api_key="")
    assert len(results) == 1
    assert results[0]["category"] is not None


# ── Auth schema tests ──────────────────────────────────────────

def test_user_register_schema_rejects_short_password():
    from app.schemas.schemas import UserRegister
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UserRegister(email="test@example.com", password="123")


def test_holding_create_rejects_negative_quantity():
    from app.schemas.schemas import HoldingCreate
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        HoldingCreate(ticker="TCS", quantity=-10, buy_price=3500)
