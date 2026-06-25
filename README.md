<div align="center">

# WealthPilot

### Agentic Personal Finance Platform

*The same financial intelligence a ₹25,000/year advisor gives — powered by AI, built for every Indian.*

[![Live Demo](https://img.shields.io/badge/Live_Demo-Visit_App-c9a84c?style=for-the-badge)](https://agentic-finance-platform.vercel.app)
[![Backend API](https://img.shields.io/badge/Backend_API-Railway-7c3aed?style=for-the-badge)](https://agenticfinanceplatform-production-5694.up.railway.app/docs)
[![CI](https://img.shields.io/github/actions/workflow/status/Aviral2309/Agentic_Finance_Platform/ci.yml?style=for-the-badge&label=CI)](https://github.com/Aviral2309/Agentic_Finance_Platform/actions)
[![Python](https://img.shields.io/badge/Python-3.11-3776ab?style=for-the-badge)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge)](https://react.dev)

</div>

---

## The Problem

95% of Indians have no financial plan. Financial advisors charge ₹25,000+/year and serve only HNIs. Free tools (Walnut, Money View) either died or don't parse actual bank statements. No free tool combines statement parsing, ML categorization, portfolio tracking, and personalized AI advice in one place.

WealthPilot solves this.

---

## Live Links

| Service | URL |
|---|---|
| Frontend | https://agentic-finance-platform.vercel.app |
| Backend API | https://agenticfinanceplatform-production-5694.up.railway.app |
| API Docs | https://agenticfinanceplatform-production-5694.up.railway.app/docs |

---

## Key Metrics

| Metric | Value |
|---|---|
| Auto-categorization accuracy | **99.1%** on 215 transactions |
| Technical analysis speed | **<2 seconds** vs 5-10 min LSTM |
| LangGraph agents | **5 agents** with conditional routing |
| Tax regimes compared | Old vs New FY 2024-25 |
| Supported banks | SBI, HDFC, ICICI, Axis, Kotak |

---

## Features

### 💳 Smart Expense Tracker
- Upload bank statements — PDF or CSV
- **4-layer ML categorization pipeline:**
  - Layer 1: Merchant keyword rules — 99.1% coverage, instant, zero cost
  - Layer 2: TF-IDF + Random Forest — handles ambiguous merchants
  - Layer 3: Gemini LLM batch call — for genuinely unclear transactions
  - Layer 4: Human-in-the-loop — user confirms, model retrains
- **Spending anomaly detection** — alerts when category spikes vs 3-month average
- Budget limits with real-time overspend alerts
- Manual transaction entry
- Month-by-month history navigation
- CSV data export
- Statement library with delete

### 📈 Portfolio Intelligence
- Add NSE/BSE/global holdings — live prices via yfinance
- Real-time P&L, Sharpe ratio, sector allocation
- **Technical Analysis Engine** (replaces LSTM):
  - RSI (14-period) — overbought/oversold signals
  - MACD with bullish/bearish crossover detection
  - Bollinger Bands — price position and bandwidth
  - 50/200-day MA — golden cross / death cross
  - Volume analysis — accumulation vs distribution
- **Gemini AI interpretation** of technical indicators in plain English
- **FinBERT NLP sentiment** — hourly news analysis per ticker
- **Market news feed** with portfolio impact detection
- Portfolio concentration warnings

### 🤖 AI Financial Advisor (LangGraph)
- **5-agent conditional graph:**
  - Router Agent — classifies query intent using Gemini
  - Expense Agent — reads actual transaction data from PostgreSQL
  - Portfolio Agent — fetches live holdings, prices, P&L
  - RAG Agent — retrieves from ChromaDB knowledge base
  - Synthesizer Agent — combines context, calls Gemini 2.5 Flash
- Streaming SSE responses (token by token)
- Reads uploaded bank statement context
- Conversation history saved across sessions
- Answers with your actual ₹ numbers, not generic advice

### 📊 Financial Insights
- **Money Health Score** — 6-dimension weighted radar:
  - Emergency Fund, Investments, Debt Health
  - Spending Discipline, Diversification, Savings Rate
- **FIRE Calculator:**
  - 4% safe withdrawal rule with inflation adjustment
  - Month-by-month SIP roadmap
  - Insurance gap analysis
  - Asset allocation glide path by age
- **Tax Estimator (FY 2024-25):**
  - Old vs new regime comparison
  - HRA, 80C, 80D, 80CCD, Section 24 deductions
  - Missing deduction detector with tax saving amount
  - Investment suggestions ranked by risk profile

### 🎯 Goal Tracking
- Set financial goals (vacation, emergency fund, investment)
- Track progress with visual progress bars
- Target date with milestone tracking

---

## Tech Stack

### Frontend
| Tech | Purpose |
|---|---|
| React 18 + Vite | SPA with fast HMR |
| React Router v6 | Client-side navigation |
| Recharts | Charts — area, bar, pie, radar |
| Zustand | Global state management |
| Axios | HTTP client with JWT interceptor |
| Lucide React | Icon system |
| CSS Variables | Dark luxury design system |

### Backend
| Tech | Purpose |
|---|---|
| FastAPI | Async Python API framework |
| PostgreSQL (Neon) | Primary database |
| SQLAlchemy | ORM with session management |
| Redis | Celery broker |
| ChromaDB | Vector database for RAG |
| Celery | Async background workers |
| JWT (python-jose) | Stateless authentication |
| bcrypt (passlib) | Password hashing |
| pdfplumber | Bank statement PDF parsing |

### ML / AI
| Tech | Purpose |
|---|---|
| scikit-learn | TF-IDF + Random Forest categorizer |
| FinBERT (HuggingFace) | Finance-specific NLP sentiment |
| Gemini 2.5 Flash | GenAI — advisor + stock analysis |
| LangGraph | Multi-agent orchestration |
| yfinance | Live stock prices + OHLCV data |
| NewsAPI | Financial news headlines |
| numpy / pandas | Data processing + financial math |

### DevOps
| Tech | Purpose |
|---|---|
| Docker Compose | Multi-container local dev |
| GitHub Actions | CI — ruff + pytest on every push |
| Railway | Backend deployment |
| Vercel | Frontend deployment |
| Neon | Managed PostgreSQL (free tier) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vercel)                  │
│          Dashboard · Expenses · Portfolio · Advisor          │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────────────┐
│                  FastAPI Backend (Railway)                    │
│    Auth · Expenses · Portfolio · Advisor · Insights          │
└────────┬─────────────┬──────────────────┬───────────────────┘
         │             │                  │
   ┌─────▼──┐    ┌─────▼──┐        ┌─────▼──┐
   │  Neon  │    │ChromaDB│        │  Redis  │
   │  PgSQL │    │Vectors │        │ Broker  │
   └────────┘    └────────┘        └────────┘

4-Layer Categorizer:
Rules (99.1%) → RF+TF-IDF → Gemini LLM → HITL (0.9%)

LangGraph Agent Graph:
Router → [Expense | Portfolio | RAG] → Synthesizer → SSE
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop

### 1. Clone
```bash
git clone https://github.com/Aviral2309/Agentic_Finance_Platform.git
cd Agentic_Finance_Platform
```

### 2. Environment variables
```bash
cp backend/.env.example backend/.env
# Fill in GEMINI_API_KEY, NEWS_API_KEY, DATABASE_URL
```

### 3. Start infrastructure
```bash
docker compose up -d
# Starts PostgreSQL + Redis + ChromaDB
```

### 4. Start backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start frontend
```bash
cd frontend
npm install
npm run dev
```

### 6. Open browser
```
http://localhost:5173
```

---

## API Endpoints

Interactive docs: `https://agenticfinanceplatform-production-5694.up.railway.app/docs`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/expenses/upload` | Upload bank statement (async) |
| GET | `/api/expenses/jobs/{id}` | Poll upload progress |
| GET | `/api/expenses/summary` | Category breakdown |
| GET | `/api/expenses/trends` | 6-month spending trends |
| POST | `/api/expenses/transactions/manual` | Add manual transaction |
| GET | `/api/features/export/transactions` | Download CSV |
| GET | `/api/features/anomalies` | Spending anomaly detection |
| GET | `/api/features/news` | News + portfolio impact |
| POST | `/api/portfolio/holdings` | Add stock holding |
| GET | `/api/portfolio/summary` | Portfolio with live prices |
| GET | `/api/portfolio/analysis/{ticker}` | Technical analysis |
| POST | `/api/advisor/chat` | SSE streaming advisor |
| GET | `/api/advisor/history` | Conversation history |
| GET | `/api/insights/health-score` | 6-dimension wellness score |
| POST | `/api/insights/fire-calculator` | FIRE retirement plan |
| POST | `/api/insights/tax-estimator` | Tax regime comparison |
| POST | `/api/features/goals` | Create financial goal |


---

## Built By

**Aviral Mittal** — B.Tech Electrical Engineering, SGSITS Indore

- GitHub: [@Aviral2309](https://github.com/Aviral2309)
- Email: aviralmittal23092004@gmail.com

---

*WealthPilot — Making financial planning as accessible as checking WhatsApp.*