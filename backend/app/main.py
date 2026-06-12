from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base

from app.api.routes import auth, expenses, portfolio, advisor, insights

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown logic."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create upload + model directories
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path("models/lstm").mkdir(parents=True, exist_ok=True)

    # Initialize ChromaDB collections
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)

        # Create default tenant and database if they don't exist
        try:
            client.get_tenant("default_tenant")
        except Exception:
            chromadb.api.client.SharedSystemClient.create_tenant("default_tenant")

        try:
            client.get_database("default_database", tenant="default_tenant")
        except Exception:
            pass

        client.get_or_create_collection("financial_knowledge")
        client.get_or_create_collection("conversation_memory")
        logger.info("ChromaDB collections initialized")
    except Exception as e:
        logger.warning(f"ChromaDB not available: {e}. RAG features will be limited.")

    logger.info(f"WealthPilot backend started. ENV: {settings.APP_ENV}")
    yield
    logger.info("WealthPilot backend shutting down")


app = FastAPI(
    title="WealthPilot API",
    description="Agentic Personal Finance Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes


app.include_router(auth.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(advisor.router, prefix="/api")
app.include_router(insights.router, prefix="/api")


@app.get("/ping")
def ping():
    return {"status": "ok", "service": "WealthPilot API", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "WealthPilot API",
        "docs": "/docs",
        "health": "/ping",
    }
