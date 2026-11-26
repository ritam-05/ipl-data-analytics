import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure project root is on sys.path whether run from root or backend/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from backend.app.api.analytics_routes import router as analytics_router
from backend.app.api.chat_routes import router as chat_router

app = FastAPI(
    title="IPL Intelligence API",
    description="Historical IPL Data Analytics, Hybrid RAG & LangGraph Agentic AI Backend",
    version="1.0.0",
)

# Configure CORS for local Next.js dev and Vercel production
allowed_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Accept production and preview Vercel deployments without listing each URL.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics_router)
app.include_router(chat_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "IPL Intelligence API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
