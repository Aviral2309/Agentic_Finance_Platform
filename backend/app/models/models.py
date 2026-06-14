import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, ForeignKey, Text, JSON,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class TransactionType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


class SentimentLabel(str, enum.Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


# ── User ───────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email            = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password  = Column(String(255), nullable=False)
    full_name        = Column(String(255), nullable=True)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    transactions     = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    parse_jobs       = relationship("ParseJob",    back_populates="user", cascade="all, delete-orphan")
    holdings         = relationship("PortfolioHolding", back_populates="user", cascade="all, delete-orphan")
    budget_limits    = relationship("BudgetLimit", back_populates="user", cascade="all, delete-orphan")
    hitl_queue       = relationship("HITLQueue",   back_populates="user", cascade="all, delete-orphan")


# ── Parse Job ──────────────────────────────────────────────────

class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename           = Column(String(500), nullable=False)
    file_path          = Column(String(1000), nullable=False)
    file_type          = Column(String(10), nullable=False)   # pdf / csv
    total_pages        = Column(Integer, nullable=True)
    total_chunks       = Column(Integer, nullable=True)
    chunks_done        = Column(Integer, default=0)
    transactions_found = Column(Integer, default=0)
    status             = Column(SAEnum(JobStatus), default=JobStatus.QUEUED)
    error_message      = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    completed_at       = Column(DateTime, nullable=True)

    user               = relationship("User", back_populates="parse_jobs")
    failed_chunks      = relationship("FailedChunk", back_populates="job", cascade="all, delete-orphan")


class FailedChunk(Base):
    __tablename__ = "failed_chunks"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id      = Column(UUID(as_uuid=True), ForeignKey("parse_jobs.id"), nullable=False)
    chunk_idx   = Column(Integer, nullable=False)
    error_msg   = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    job         = relationship("ParseJob", back_populates="failed_chunks")


# ── Transaction ────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id              = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id               = Column(UUID(as_uuid=True), ForeignKey("parse_jobs.id"), nullable=True)

    date                 = Column(DateTime, nullable=False, index=True)
    amount               = Column(Float, nullable=False)
    description          = Column(Text, nullable=False)
    transaction_type     = Column(SAEnum(TransactionType), nullable=False)
    balance              = Column(Float, nullable=True)
    reference_id         = Column(String(255), nullable=True)

    category             = Column(String(100), nullable=True, index=True)
    sub_category         = Column(String(100), nullable=True)
    categorization_layer = Column(Integer, nullable=True)   # 1 / 2 / 3 / 4
    confidence           = Column(Float, nullable=True)
    is_confirmed         = Column(Boolean, default=False)
    merchant_name        = Column(String(255), nullable=True)
    is_recurring         = Column(Boolean, default=False)
    created_at           = Column(DateTime, default=datetime.utcnow)

    user                 = relationship("User", back_populates="transactions")


# ── HITL Queue ─────────────────────────────────────────────────

class HITLQueue(Base):
    __tablename__ = "hitl_queue"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transaction_id         = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    suggested_category     = Column(String(100), nullable=True)
    alternative_categories = Column(JSON, nullable=True)
    is_resolved            = Column(Boolean, default=False)
    created_at             = Column(DateTime, default=datetime.utcnow)

    user                   = relationship("User", back_populates="hitl_queue")


# ── Budget Limit ───────────────────────────────────────────────

class BudgetLimit(Base):
    __tablename__ = "budget_limits"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category      = Column(String(100), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user          = relationship("User", back_populates="budget_limits")


# ── Portfolio ──────────────────────────────────────────────────

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker       = Column(String(20), nullable=False)
    company_name = Column(String(255), nullable=True)
    quantity     = Column(Float, nullable=False)
    buy_price    = Column(Float, nullable=False)
    sector       = Column(String(100), nullable=True)
    exchange     = Column(String(20), default="NSE")
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user         = relationship("User", back_populates="holdings")


class LSTMModel(Base):
    __tablename__ = "lstm_models"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker        = Column(String(20), nullable=False, index=True)
    model_path    = Column(String(1000), nullable=False)
    val_mae       = Column(Float, nullable=True)
    val_mae_pct   = Column(Float, nullable=True)
    mlflow_run_id = Column(String(255), nullable=True)
    is_production = Column(Boolean, default=False)
    trained_at    = Column(DateTime, default=datetime.utcnow)


class TickerSentiment(Base):
    __tablename__ = "ticker_sentiment"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker         = Column(String(20), nullable=False, index=True)
    label          = Column(SAEnum(SentimentLabel), nullable=False)
    score          = Column(Float, nullable=False)
    headline_count = Column(Integer, default=0)
    top_headlines  = Column(JSON, nullable=True)
    computed_at    = Column(DateTime, default=datetime.utcnow, index=True)
