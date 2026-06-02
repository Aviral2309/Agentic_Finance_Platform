from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


# ── Auth ───────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Parse Job ──────────────────────────────────────────────────

class JobStatusOut(BaseModel):
    job_id: UUID
    status: str
    progress_pct: float
    chunks_done: int
    total_chunks: Optional[int]
    transactions_found: int
    filename: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Transactions ───────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: UUID
    date: datetime
    amount: float
    description: str
    transaction_type: str
    category: Optional[str]
    categorization_layer: Optional[int]
    confidence: Optional[float]
    is_confirmed: bool
    merchant_name: Optional[str]
    is_recurring: bool

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    category: str
    sub_category: Optional[str] = None


class ExpenseSummary(BaseModel):
    category: str
    total: float
    count: int
    percentage: float


class MonthlyTrend(BaseModel):
    month: str
    total_debit: float
    total_credit: float
    by_category: List[ExpenseSummary]


# ── HITL ───────────────────────────────────────────────────────

class HITLItem(BaseModel):
    hitl_id: UUID
    transaction_id: UUID
    date: datetime
    amount: float
    description: str
    suggested_category: Optional[str]
    alternative_categories: Optional[List[str]]

    class Config:
        from_attributes = True


class HITLConfirm(BaseModel):
    transaction_id: UUID
    confirmed_category: str
    sub_category: Optional[str] = None


# ── Budget ─────────────────────────────────────────────────────

class BudgetLimitCreate(BaseModel):
    category: str
    monthly_limit: float

    @field_validator("monthly_limit")
    @classmethod
    def positive(cls, v):
        if v <= 0:
            raise ValueError("Must be positive")
        return v


class BudgetLimitOut(BaseModel):
    id: UUID
    category: str
    monthly_limit: float

    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    category: str
    limit: float
    spent: float
    remaining: float
    percentage_used: float
    is_over: bool


# ── Portfolio ──────────────────────────────────────────────────

class HoldingCreate(BaseModel):
    ticker: str
    quantity: float
    buy_price: float
    exchange: str = "NSE"

    @field_validator("ticker")
    @classmethod
    def upper_ticker(cls, v):
        return v.upper().strip()

    @field_validator("quantity", "buy_price")
    @classmethod
    def positive_values(cls, v):
        if v <= 0:
            raise ValueError("Must be positive")
        return v


class HoldingOut(BaseModel):
    id: UUID
    ticker: str
    company_name: Optional[str]
    quantity: float
    buy_price: float
    current_price: Optional[float]
    current_value: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    sector: Optional[str]
    exchange: str
    sentiment_label: Optional[str]

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    total_pnl: float
    total_pnl_pct: float
    sharpe_ratio: Optional[float]
    holdings: List[HoldingOut]
    allocation_by_sector: Dict[str, float]


# ── LSTM Forecast ──────────────────────────────────────────────

class ForecastPoint(BaseModel):
    date: str
    predicted_price: float
    lower_band: float
    upper_band: float


class ForecastOut(BaseModel):
    ticker: str
    current_price: float
    forecast_7d: List[ForecastPoint]
    forecast_30d: List[ForecastPoint]
    model_mae_pct: Optional[float]


# ── Sentiment ──────────────────────────────────────────────────

class SentimentOut(BaseModel):
    ticker: str
    label: str
    score: float
    top_headlines: Optional[List[str]]
    computed_at: datetime

    class Config:
        from_attributes = True


# ── Advisor ────────────────────────────────────────────────────

class AdvisorMessage(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def non_empty(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()
