from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine
import app.models  # Import the models module

# Create database tables
app.models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GenAI Research Assistant",
    description="A RAG-powered AI research assistant",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
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
        "environment": settings.app_env,
        "openai_configured": bool(settings.openai_api_key)
    }

# Include authentication routes
from app.routers import users
app.include_router(users.router)

from app.routers import documents
app.include_router(documents.router)

from app.routers import embeddings
app.include_router(embeddings.router)