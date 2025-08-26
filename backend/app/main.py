from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings  # Use your existing settings import
from app.database import engine
import app.models

# Import routers
from app.routers import users, documents, embeddings, search, rag

# Create database tables
app.models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GenAI Research Assistant",
    description="A RAG-powered AI research assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "GenAI Research Assistant API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "openai_configured": bool(settings.openai_api_key)
    }

# Include routers
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(embeddings.router)
app.include_router(search.router)
app.include_router(rag.router)