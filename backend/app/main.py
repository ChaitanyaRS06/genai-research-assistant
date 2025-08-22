from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

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

# We'll add more routes here as we build them
# from app.routers import users, docs, chat
# app.include_router(users.router)
# app.include_router(docs.router)
# app.include_router(chat.router)