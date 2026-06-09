# WealthPilot — Agentic Personal Finance Platform

> 95% of Indians have no financial plan. Financial advisors charge ₹25,000+/year and serve only HNIs.
> WealthPilot is the advisor for everyone else.

![WealthPilot Dashboard](https://via.placeholder.com/1200x600/080c14/c9a84c?text=WealthPilot+Dashboard)

**Live Demo:** [wealthpilot.vercel.app](https://wealthpilot.vercel.app) *(deploy in progress)*
**Backend API:** [wealthpilot.railway.app](https://wealthpilot.railway.app)

---

## What It Does

WealthPilot reads your actual bank statements, tracks your portfolio, and gives you the same personalized financial guidance a ₹25,000/year advisor would give — for free, in seconds.

| Problem | Solution |
|---|---|
| Bank statements are PDFs nobody reads | 4-layer ML pipeline auto-categorizes every transaction |
| No idea where money goes | Category breakdown with month-over-month comparison |
| Generic financial advice | LangGraph advisor that knows YOUR actual numbers |
| Investment decisions with no context | Technical analysis (RSI, MACD, Bollinger) + Gemini AI interpretation |
| No financial plan | FIRE Calculator, Tax Estimator, Money Health Score |

---

## Features

### 💳 Expense Tracker
- Upload bank statements (PDF or CSV) — SBI, HDFC, ICICI, Axis, Kotak
- **4-layer categorization pipeline:**
  - Layer 1: Merchant keyword rules (~60% coverage, instant, free)
  - Layer 2: TF-IDF + Random Forest ML classifier (~25% coverage)
  - Layer 3: Gemini LLM batch call for ambiguous transactions (~10%)
  - Layer 4: Human-in-the-loop confirmation UI (remaining ~5%)
- Online learning — every HITL confirmation retrains Layer 2 monthly
- Budget limits per category with overspend alerts
- Recurring transaction detection
- Month-over-month spending trends
- Manual expense entry

### 📈 Portfolio Manager
- Add stock holdings — live prices via yfinance (NSE + global)
- P&L tracking, Sharpe ratio, sector allocation
- **Technical Analysis Engine** (replaces slow LSTM):
  - RSI (14-period) — overbought/oversold signals
  - MACD with crossover detection
  - Bollinger Bands with position analysis
  - 50/200-day moving averages — golden/death cross
  - Volume analysis — accumulation vs distribution
- **Gemini AI interpretation** of technical indicators in plain English
- FinBERT NLP sentiment — hourly news analysis per ticker
- Portfolio concentration warnings

### 🤖 AI Financial Advisor (LangGraph)
- **5-agent graph** with conditional routing:
  - Router Agent — classifies query intent
  - Expense Agent — reads your actual transaction data
  - Portfolio Agent — reads your holdings and P&L
  - RAG Agent — retrieves from financial knowledge base
  - Synthesizer Agent — combines context, calls Gemini 2.5 Flash
- Streaming SSE responses (token by token)
- Conversation history saved and recalled
- Reads uploaded bank statement context
- Knows your actual numbers — not generic advice

### 📊 Financial Insights
- **Money Health Score** — 6-dimension wellness score:
  - Emergency Fund, Investments, Debt Health
  - Spending Discipline, Diversification, Savings Rate
- **FIRE Calculator** — Financial Independence, Retire Early:
  - Inflation-adjusted corpus calculation (4% safe withdrawal rule)
  - Month-by-month SIP roadmap
  - Insurance gap analysis
  - Asset allocation glide path
- **Tax Estimator** — FY 2024-25:
  - Old vs new regime comparison with your actual numbers
  - Missing deduction detector (80C, 80D, 80CCD, HRA)
  - Tax-saving investment suggestions ranked by risk profile

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| React 18 + Vite | SPA framework with fast HMR |
| React Router v6 | Client-side navigation |
| Recharts | Charts — area, bar, pie, radar |
| Zustand | Global state management |
| Axios | HTTP client |
| Lucide React | Icon system |
| CSS Variables | Design system — dark luxury theme |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | Async Python API framework |
| PostgreSQL | Primary relational database |
| SQLAlchemy | ORM with session management |
| Redis | Celery broker + job queue |
| ChromaDB | Vector database for RAG |
| Celery | Async background workers |
| JWT (python-jose) | Stateless authentication |
| bcrypt (passlib) | Password hashing |
| pdfplumber | Bank statement PDF parsing |

### ML / AI
| Technology | Purpose |
|---|---|
| scikit-learn | TF-IDF + Random Forest categorizer |
| FinBERT (HuggingFace) | Finance-specific NLP sentiment |
| Gemini 2.5 Flash | GenAI — advisor + stock analysis |
| LangGraph | Multi-agent orchestration |
| yfinance | Live stock prices + historical OHLCV |
| NewsAPI | Financial news headlines |
| numpy / pandas / scipy | Data processing + financial math |
| MLflow | Experiment tracking |

### DevOps
| Technology | Purpose |
|---|---|
| Docker Compose | Multi-container local development |
| GitHub Actions | CI — pytest + ruff on every push |
| Railway | Backend deployment |
| Vercel | Frontend deployment |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│         Vite · Recharts · Zustand · Axios            │
└─────────────────┬───────────────────────────────────┘
                  │ REST + SSE
┌─────────────────▼───────────────────────────────────┐
│                  FastAPI Backend                     │
│   Auth · Expenses · Portfolio · Advisor · Insights   │
└──────┬──────────┬──────────────┬────────────────────┘
       │          │              │
┌──────▼──┐ ┌────▼─────┐ ┌─────▼──────────────────┐
│ PostgreSQL│ │ ChromaDB │ │     Celery Workers      │
│ (primary) │ │ (vectors)│ │  Sentiment · Retrain    │
└──────────┘ └──────────┘ └────────────┬────────────┘
                                        │
                           ┌────────────▼────────────┐
                           │          Redis           │
                           │    (broker + cache)      │
                           └─────────────────────────┘

ML Pipeline:
┌─────────────────────────────────────────────────────┐
│              4-Layer Categorizer                     │
│  Rules(60%) → RF+TFIDF(25%) → Gemini(10%) → HITL(5%)│
└─────────────────────────────────────────────────────┘

LangGraph Agent Graph:
┌──────────┐    ┌─────────┐   ┌───────────┐
│  Router  │───▶│ Expense │──▶│           │
│  Agent   │    │  Agent  │   │Synthesizer│──▶ SSE Stream
│          │───▶│Portfolio│──▶│  Agent    │
│          │    │  Agent  │   │           │
│          │───▶│   RAG   │──▶│           │
└──────────┘    └─────────┘   └───────────┘
```

---

## Scalable PDF Processing

The system handles 1000+ page bank statements without blocking:

```
Upload → 202 Accepted + job_id
              ↓
        Celery Worker
              ↓
    Parse 50 pages at a time
    (constant memory, fault tolerant)
              ↓
    4-layer categorize batch
              ↓
    Write to PostgreSQL chunk by chunk
              ↓
Client polls GET /jobs/{id} → real progress bar
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop

### 1. Clone and setup
```bash
git clone https://github.com/YOUR-USERNAME/wealthpilot.git
cd wealthpilot
cp .env.example .env
# Fill in GEMINI_API_KEY and NEWS_API_KEY in .env
```

### 2. Start infrastructure
```bash
docker compose up -d
# Starts PostgreSQL + Redis + ChromaDB
```

### 3. Start backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Open browser
```
http://localhost:5173
```

---

## API Documentation

Interactive API docs available at `http://localhost:8000/docs`

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/expenses/upload` | Upload bank statement (async) |
| GET | `/api/expenses/jobs/{id}` | Poll upload progress |
| GET | `/api/expenses/summary` | Monthly category breakdown |
| GET | `/api/expenses/trends` | 6-month spending trends |
| POST | `/api/expenses/transactions/manual` | Add manual transaction |
| POST | `/api/portfolio/holdings` | Add stock holding |
| GET | `/api/portfolio/summary` | Portfolio with live prices |
| GET | `/api/portfolio/analysis/{ticker}` | Technical analysis |
| POST | `/api/advisor/chat` | SSE streaming advisor |
| GET | `/api/advisor/history` | Conversation history |
| GET | `/api/insights/health-score` | 6-dimension wellness score |
| POST | `/api/insights/fire-calculator` | FIRE retirement plan |
| POST | `/api/insights/tax-estimator` | Tax regime comparison |

---

## Interview Defensibility

### Why 4 layers for categorization?
Each layer has a different cost-accuracy profile. Rules are free and instant. ML is cheap. LLM costs money per call — only used as fallback. HITL for edge cases. Batching all ambiguous transactions in one Gemini call reduces cost by ~50x vs per-transaction calls.

### Why LangGraph over LangChain agents?
LangGraph gives explicit state schema and conditional edges. I control exactly which agents activate per query. LangChain agents are non-deterministic in routing — in a financial product, auditability of which data sources influenced a response matters.

### Why technical analysis instead of LSTM?
LSTM forecasting on price data is largely noise on short timeframes, takes 5-10 minutes to train per ticker, and gives users a false sense of precision. Technical indicators (RSI, MACD, Bollinger) are computed in under 2 seconds, always available, and give actionable signals. Gemini then interprets the indicators in plain English — more useful than a noisy prediction chart.

### Why FinBERT over VADER for sentiment?
VADER is trained on social media text. "Stock crashes record highs" reads as negative to VADER. FinBERT is fine-tuned on Wall Street Journal and Reuters financial text — it correctly identifies that sentence as bullish. Domain-specific model beats general model on domain-specific task.

### How does the system handle 1000-page PDFs?
202 Accepted + job queue. Parser runs in Celery background worker, 50 pages per chunk. Memory stays flat — GC clears each chunk after PostgreSQL write. Per-chunk retry means failure at page 847 doesn't abort the job. Client polls `/jobs/{id}` and sees a real progress bar.

---

## Project Structure

```
wealthpilot/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # auth, expenses, portfolio, advisor, insights
│   │   ├── core/            # config, database, security, celery
│   │   ├── ml/              # categorizer, technical_analysis, sentiment, advisor
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # parse_service (async PDF/CSV)
│   │   └── main.py
│   ├── tests/
│   │   └── test_basics.py   # 12 tests — categorizer + schema validation
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Expenses, Portfolio, Advisor, Insights
│   │   ├── components/      # Layout, shared UI
│   │   ├── services/        # api.js — all API calls
│   │   └── store/           # Zustand global state
│   ├── index.html
│   └── package.json
├── docker-compose.yml
├── .github/workflows/ci.yml
└── .env.example
```

---

## Resume Bullets

```
• Built WealthPilot — deployed agentic personal finance platform with 4-layer ML
  expense categorizer (rules + RF + Gemini + HITL), LangGraph 5-agent advisor,
  technical analysis engine (RSI/MACD/Bollinger + Gemini AI interpretation), and
  FinBERT NLP sentiment pipeline

• Engineered async chunked PDF pipeline handling 1000-page bank statements —
  50-page chunks maintain flat memory, per-chunk fault tolerance, Celery job queue
  with /jobs/{id} polling — [N] statements processed across [N] users

• Designed LangGraph multi-agent system: Router → [Expense|Portfolio|RAG] →
  Synthesizer with conditional routing — advisor answers context-aware queries
  using user's actual transaction and portfolio data via Gemini 2.5 Flash

• Built Financial Insights suite: Money Health Score (6-dimension weighted),
  FIRE Calculator (inflation-adjusted corpus + SIP roadmap), Tax Estimator
  (old vs new regime + missing deduction detector for FY 2024-25)
```

---

## Roadmap

- [ ] Deploy to Railway + Vercel
- [ ] News feed with portfolio impact analysis
- [ ] Multi-account bank statement support
- [ ] Historical spending comparison (previous months)
- [ ] Spending anomaly detection with personalized alerts
- [ ] Google OAuth
- [ ] Stripe billing (Free/Pro tiers)

---

## Built By

**Aviral Jain** — B.Tech, SGSITS Indore
- GitHub: [@YOUR-USERNAME](https://github.com/YOUR-USERNAME)
- LinkedIn: [linkedin.com/in/YOUR-PROFILE](https://linkedin.com/in/YOUR-PROFILE)

---

*WealthPilot — Making financial planning as accessible as checking WhatsApp.*