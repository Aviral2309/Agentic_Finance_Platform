"""
New features:
1. Money Health Score — 6-dimension financial wellness score
2. FIRE Calculator — retirement corpus + month-by-month SIP plan
3. Tax Estimator — 80C gaps, old vs new regime comparison
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, Transaction, TransactionType,
    PortfolioHolding, BudgetLimit
)

router = APIRouter(prefix="/insights", tags=["insights"])


# ── Money Health Score ─────────────────────────────────────────

@router.get("/health-score")
def get_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    6-dimension financial health score (0-100 each).
    Computed from actual user data in DB.
    """
    user_id = current_user.id
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_3_months = now - timedelta(days=90)

    # ── 1. Emergency Fund Score ──────────────────────────────
    # Ideal: 6 months of expenses in liquid savings
    monthly_expense = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= last_3_months,
        ).scalar() or 0
    ) / 3  # average monthly

    monthly_income = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.CREDIT,
            Transaction.date >= month_start,
        ).scalar() or 0
    )

    savings_rate = ((monthly_income - monthly_expense) / max(monthly_income, 1)) * 100
    # Score based on savings rate: 20%+ = 100, 10% = 50, 0% = 0
    emergency_score = min(100, max(0, savings_rate * 5))

    # ── 2. Investment Score ──────────────────────────────────
    # Based on portfolio value vs monthly income ratio
    holdings = db.query(PortfolioHolding).filter(PortfolioHolding.user_id == user_id).all()
    portfolio_value = sum(h.quantity * h.buy_price for h in holdings)
    # Ideal: portfolio = 12x monthly income
    investment_score = min(100, (portfolio_value / max(monthly_income * 12, 1)) * 100)

    # ── 3. Debt Health Score ─────────────────────────────────
    # Based on EMI/loan transactions vs income
    emi_spend = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.category.in_(["EMI & Loans"]),
            Transaction.date >= month_start,
        ).scalar() or 0
    )
    emi_ratio = (emi_spend / max(monthly_income, 1)) * 100
    # Ideal: EMI < 30% of income
    debt_score = max(0, min(100, 100 - (emi_ratio - 30) * 2)) if emi_ratio > 30 else 100

    # ── 4. Spending Discipline Score ─────────────────────────
    # Based on budget adherence
    budgets = db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id).all()
    if budgets:
        over_budget_count = 0
        for b in budgets:
            spent = (
                db.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.category == b.category,
                    Transaction.transaction_type == TransactionType.DEBIT,
                    extract("year", Transaction.date) == now.year,
                    extract("month", Transaction.date) == now.month,
                ).scalar() or 0
            )
            if spent > b.monthly_limit:
                over_budget_count += 1
        discipline_score = max(0, 100 - (over_budget_count / len(budgets)) * 100)
    else:
        # No budgets set — partial score
        discipline_score = 50

    # ── 5. Diversification Score ────────────────────────────
    # Based on number of holdings and sector spread
    if not holdings:
        diversification_score = 0
    else:
        sectors = set(h.sector for h in holdings if h.sector)
        holding_count = len(holdings)
        # Ideal: 5+ holdings across 3+ sectors
        count_score = min(100, holding_count * 20)
        sector_score = min(100, len(sectors) * 33)
        diversification_score = (count_score + sector_score) / 2

    # ── 6. Savings Rate Score ────────────────────────────────
    # Savings rate benchmark: 20% = good, 30% = great
    savings_score = min(100, max(0, savings_rate * 3.33))

    # ── Composite ────────────────────────────────────────────
    scores = {
        "emergency_fund": round(emergency_score, 1),
        "investments": round(investment_score, 1),
        "debt_health": round(debt_score, 1),
        "spending_discipline": round(discipline_score, 1),
        "diversification": round(diversification_score, 1),
        "savings_rate": round(savings_score, 1),
    }
    composite = round(sum(scores.values()) / len(scores), 1)

    # ── Recommendations ──────────────────────────────────────
    recommendations = []
    if emergency_score < 50:
        recommendations.append(f"⚠ Low savings rate ({savings_rate:.1f}%) — aim for 20%+ of income")
    if investment_score < 30:
        recommendations.append("⚠ Portfolio value is low relative to income — consider increasing SIP")
    if debt_score < 70:
        recommendations.append(f"⚠ EMI burden is high ({emi_ratio:.1f}% of income) — ideal is under 30%")
    if discipline_score < 70:
        recommendations.append("⚠ Over budget in multiple categories — review spending habits")
    if diversification_score < 50:
        recommendations.append("⚠ Portfolio is under-diversified — add more sectors/holdings")
    if not recommendations:
        recommendations.append("✓ Financial health looks good — keep maintaining discipline")

    return {
        "scores": scores,
        "composite": composite,
        "grade": "A" if composite >= 80 else "B" if composite >= 60 else "C" if composite >= 40 else "D",
        "recommendations": recommendations,
        "metadata": {
            "monthly_income": round(monthly_income, 0),
            "monthly_expense": round(monthly_expense, 0),
            "savings_rate": round(savings_rate, 1),
            "emi_ratio": round(emi_ratio, 1),
            "portfolio_value": round(portfolio_value, 0),
            "holdings_count": len(holdings),
        }
    }


# ── FIRE Calculator ────────────────────────────────────────────

class FIREInput(BaseModel):
    current_age: int
    target_retirement_age: int
    monthly_income: float
    monthly_expenses: float
    existing_corpus: float = 0.0
    existing_term_cover: float = 0.0
    liquid_savings: float = 0.0
    expected_return_pct: float = 12.0    # annual % return on investments
    inflation_pct: float = 6.0           # annual inflation rate
    safe_withdrawal_rate: float = 4.0    # % of corpus to withdraw annually


@router.post("/fire-calculator")
def calculate_fire(
    payload: FIREInput,
    current_user: User = Depends(get_current_user),
):
    """
    FIRE Path Planner.
    4% safe withdrawal rule with inflation adjustment.
    Returns month-by-month SIP roadmap.
    """
    if payload.target_retirement_age <= payload.current_age:
        raise HTTPException(status_code=400, detail="Retirement age must be greater than current age")

    years_to_retire = payload.target_retirement_age - payload.current_age
    months_to_retire = years_to_retire * 12

    # Inflation-adjusted annual expenses at retirement
    inflation_factor = (1 + payload.inflation_pct / 100) ** years_to_retire
    annual_expenses_at_retirement = payload.monthly_expenses * 12 * inflation_factor

    # Corpus needed (4% safe withdrawal rule)
    corpus_needed = annual_expenses_at_retirement / (payload.safe_withdrawal_rate / 100)

    # Monthly SIP needed (future value of annuity formula)
    monthly_return = payload.expected_return_pct / 100 / 12
    existing_corpus_grown = payload.existing_corpus * (1 + monthly_return) ** months_to_retire

    remaining_corpus = max(0, corpus_needed - existing_corpus_grown)

    if monthly_return > 0 and months_to_retire > 0:
        monthly_sip = remaining_corpus * monthly_return / ((1 + monthly_return) ** months_to_retire - 1)
    else:
        monthly_sip = remaining_corpus / max(months_to_retire, 1)

    # Insurance gap (10x annual income rule)
    annual_income = payload.monthly_income * 12
    insurance_needed = annual_income * 10
    insurance_gap = max(0, insurance_needed - payload.existing_term_cover)

    # Emergency fund gap (6 months expenses)
    emergency_fund_needed = payload.monthly_expenses * 6
    emergency_fund_gap = max(0, emergency_fund_needed - payload.liquid_savings)

    # Asset allocation glide path (100 - age = equity %)
    equity_pct = max(40, 100 - payload.current_age)
    debt_pct = 100 - equity_pct

    # Savings rate check
    savings_rate = ((payload.monthly_income - payload.monthly_expenses) / payload.monthly_income) * 100
    can_afford_sip = monthly_sip <= (payload.monthly_income - payload.monthly_expenses)

    # Milestone roadmap (every 5 years)
    milestones = []
    for year in range(5, years_to_retire + 1, 5):
        age_at_milestone = payload.current_age + year
        corpus_at_milestone = payload.existing_corpus * (1 + monthly_return) ** (year * 12)
        corpus_at_milestone += monthly_sip * ((1 + monthly_return) ** (year * 12) - 1) / monthly_return if monthly_return > 0 else monthly_sip * year * 12
        progress_pct = (corpus_at_milestone / corpus_needed) * 100

        # Equity allocation at that age
        eq = max(40, 100 - age_at_milestone)

        milestones.append({
            "year": year,
            "age": age_at_milestone,
            "corpus_target": round(corpus_at_milestone, 0),
            "progress_pct": round(min(100, progress_pct), 1),
            "equity_allocation": eq,
            "debt_allocation": 100 - eq,
        })

    return {
        "inputs": {
            "current_age": payload.current_age,
            "target_retirement_age": payload.target_retirement_age,
            "years_to_retire": years_to_retire,
            "monthly_income": payload.monthly_income,
            "monthly_expenses": payload.monthly_expenses,
        },
        "results": {
            "corpus_needed": round(corpus_needed, 0),
            "corpus_needed_readable": _format_amount(corpus_needed),
            "monthly_sip_needed": round(monthly_sip, 0),
            "existing_corpus_grown": round(existing_corpus_grown, 0),
            "annual_expenses_at_retirement": round(annual_expenses_at_retirement, 0),
            "insurance_gap": round(insurance_gap, 0),
            "emergency_fund_gap": round(emergency_fund_gap, 0),
            "current_savings_rate": round(savings_rate, 1),
            "can_afford_sip": can_afford_sip,
            "sip_as_pct_of_savings": round((monthly_sip / max(payload.monthly_income - payload.monthly_expenses, 1)) * 100, 1),
        },
        "allocation": {
            "equity_pct": equity_pct,
            "debt_pct": debt_pct,
            "note": f"At age {payload.current_age}: {equity_pct}% equity, {debt_pct}% debt — shift 5% to debt every 5 years",
        },
        "milestones": milestones,
        "action_items": _get_fire_action_items(payload, monthly_sip, insurance_gap, emergency_fund_gap, savings_rate),
    }


def _format_amount(amount: float) -> str:
    if amount >= 1e7:
        return f"₹{amount/1e7:.1f} Cr"
    elif amount >= 1e5:
        return f"₹{amount/1e5:.1f} L"
    else:
        return f"₹{amount:,.0f}"


def _get_fire_action_items(payload, monthly_sip, insurance_gap, emergency_fund_gap, savings_rate):
    items = []
    surplus = payload.monthly_income - payload.monthly_expenses

    if emergency_fund_gap > 0:
        months_to_build = round(emergency_fund_gap / max(surplus * 0.5, 1))
        items.append(f"🏦 Build emergency fund: Save ₹{min(surplus*0.5, emergency_fund_gap):,.0f}/month — done in {months_to_build} months")

    if insurance_gap > 0:
        term_premium = round(insurance_gap * 0.0004)  # ~0.04% annual premium estimate
        items.append(f"🛡 Buy term insurance: ₹{_format_amount(insurance_gap)} cover needed — est. premium ₹{term_premium:,}/year")

    if monthly_sip > 0:
        items.append(f"📈 Start SIP of ₹{monthly_sip:,.0f}/month — split {payload.expected_return_pct:.0f}% return target across equity MF")

    if savings_rate < 20:
        items.append(f"💰 Increase savings rate from {savings_rate:.1f}% to 20% — reduce discretionary spending by ₹{(0.2 * payload.monthly_income - (payload.monthly_income - payload.monthly_expenses)):,.0f}/month")

    return items


# ── Tax Estimator ──────────────────────────────────────────────

class TaxInput(BaseModel):
    annual_gross_salary: float
    hra_received: float = 0.0
    rent_paid: float = 0.0
    metro_city: bool = True
    section_80c_investments: float = 0.0    # PF, ELSS, PPF, LIC etc
    section_80d_premium: float = 0.0        # Health insurance
    section_80ccd1b: float = 0.0            # NPS additional
    home_loan_interest: float = 0.0         # Section 24
    lta_claimed: float = 0.0
    other_deductions: float = 0.0


@router.post("/tax-estimator")
def estimate_tax(
    payload: TaxInput,
    current_user: User = Depends(get_current_user),
):
    """
    Compare old vs new tax regime for FY 2024-25.
    Identify missing deductions and suggest tax-saving investments.
    """
    gross = payload.annual_gross_salary

    # ── Old Regime Calculation ──────────────────────────────
    # Standard deduction
    standard_deduction = 50000

    # HRA exemption
    if payload.hra_received > 0 and payload.rent_paid > 0:
        basic_salary = gross * 0.4  # approximate
        hra_limit1 = payload.hra_received
        hra_limit2 = payload.rent_paid - (0.1 * basic_salary)
        hra_limit3 = 0.5 * basic_salary if payload.metro_city else 0.4 * basic_salary
        hra_exemption = max(0, min(hra_limit1, hra_limit2, hra_limit3))
    else:
        hra_exemption = 0

    # Section 80C (max 1.5L)
    sec_80c = min(150000, payload.section_80c_investments)

    # Section 80D (max 25K self, 25K parents)
    sec_80d = min(25000, payload.section_80d_premium)

    # Section 80CCD(1B) NPS (max 50K)
    sec_80ccd = min(50000, payload.section_80ccd1b)

    # Section 24 home loan interest (max 2L)
    sec_24 = min(200000, payload.home_loan_interest)

    total_deductions_old = (
        standard_deduction + hra_exemption + sec_80c +
        sec_80d + sec_80ccd + sec_24 + payload.lta_claimed +
        payload.other_deductions
    )

    taxable_old = max(0, gross - total_deductions_old)
    tax_old = _compute_old_regime_tax(taxable_old)

    # ── New Regime Calculation (FY 2024-25) ─────────────────
    # Only standard deduction of 75,000 allowed
    taxable_new = max(0, gross - 75000)
    tax_new = _compute_new_regime_tax(taxable_new)

    # ── Missing Deductions ──────────────────────────────────
    missing = []
    savings = 0

    if payload.section_80c_investments < 150000:
        gap = 150000 - payload.section_80c_investments
        tax_saving = gap * _marginal_rate(taxable_old)
        missing.append({
            "section": "80C",
            "description": "ELSS, PPF, NPS, LIC, PF top-up",
            "max_limit": 150000,
            "invested": payload.section_80c_investments,
            "gap": gap,
            "potential_tax_saving": round(tax_saving),
        })
        savings += tax_saving

    if payload.section_80d_premium < 25000:
        gap = 25000 - payload.section_80d_premium
        tax_saving = gap * _marginal_rate(taxable_old)
        missing.append({
            "section": "80D",
            "description": "Health insurance premium",
            "max_limit": 25000,
            "invested": payload.section_80d_premium,
            "gap": gap,
            "potential_tax_saving": round(tax_saving),
        })
        savings += tax_saving

    if payload.section_80ccd1b < 50000:
        gap = 50000 - payload.section_80ccd1b
        tax_saving = gap * _marginal_rate(taxable_old)
        missing.append({
            "section": "80CCD(1B)",
            "description": "NPS additional contribution",
            "max_limit": 50000,
            "invested": payload.section_80ccd1b,
            "gap": gap,
            "potential_tax_saving": round(tax_saving),
        })
        savings += tax_saving

    # ── Recommendation ──────────────────────────────────────
    recommended_regime = "old" if tax_old < tax_new else "new"
    tax_saving_by_switching = abs(tax_new - tax_old)

    return {
        "old_regime": {
            "gross_salary": gross,
            "total_deductions": round(total_deductions_old),
            "taxable_income": round(taxable_old),
            "tax_payable": round(tax_old),
            "deduction_breakdown": {
                "standard_deduction": standard_deduction,
                "hra_exemption": round(hra_exemption),
                "section_80c": sec_80c,
                "section_80d": sec_80d,
                "section_80ccd1b": sec_80ccd,
                "home_loan_interest": sec_24,
            }
        },
        "new_regime": {
            "gross_salary": gross,
            "standard_deduction": 75000,
            "taxable_income": round(taxable_new),
            "tax_payable": round(tax_new),
        },
        "recommendation": {
            "better_regime": recommended_regime,
            "tax_saving": round(tax_saving_by_switching),
            "message": f"{'Old' if recommended_regime == 'old' else 'New'} regime saves you ₹{tax_saving_by_switching:,.0f} annually"
        },
        "missing_deductions": missing,
        "potential_additional_savings": round(savings),
        "investment_suggestions": _get_tax_investment_suggestions(missing, gross),
    }


def _compute_old_regime_tax(taxable: float) -> float:
    """Old tax regime slabs FY 2024-25."""
    tax = 0.0
    if taxable <= 250000:
        return 0
    if taxable <= 500000:
        tax = (taxable - 250000) * 0.05
    elif taxable <= 1000000:
        tax = 12500 + (taxable - 500000) * 0.20
    else:
        tax = 112500 + (taxable - 1000000) * 0.30
    # Add 4% cess
    return tax * 1.04


def _compute_new_regime_tax(taxable: float) -> float:
    """New tax regime slabs FY 2024-25."""
    tax = 0.0
    slabs = [(300000, 0), (600000, 0.05), (900000, 0.10), (1200000, 0.15), (1500000, 0.20), (float('inf'), 0.30)]
    prev = 0
    for limit, rate in slabs:
        if taxable <= prev:
            break
        taxable_in_slab = min(taxable, limit) - prev
        tax += taxable_in_slab * rate
        prev = limit
    return tax * 1.04


def _marginal_rate(taxable: float) -> float:
    if taxable <= 500000:
        return 0.05
    elif taxable <= 1000000:
        return 0.20
    else:
        return 0.30


def _get_tax_investment_suggestions(missing: list, gross: float) -> list:
    suggestions = []
    for m in sorted(missing, key=lambda x: x["potential_tax_saving"], reverse=True)[:3]:
        if m["section"] == "80C":
            if gross > 1000000:
                suggestions.append({"instrument": "ELSS Mutual Fund", "reason": "Best risk-adjusted 80C option — 3-year lock-in, market returns", "section": "80C", "max_amount": m["gap"]})
            else:
                suggestions.append({"instrument": "PPF", "reason": "Safest 80C option — guaranteed 7.1% return, tax-free maturity", "section": "80C", "max_amount": m["gap"]})
        elif m["section"] == "80D":
            suggestions.append({"instrument": "Health Insurance", "reason": "Mediclaim for self + family — essential coverage + tax benefit", "section": "80D", "max_amount": m["gap"]})
        elif m["section"] == "80CCD(1B)":
            suggestions.append({"instrument": "NPS Tier 1", "reason": "Extra ₹50K deduction beyond 80C — good for high earners", "section": "80CCD(1B)", "max_amount": m["gap"]})
    return suggestions
