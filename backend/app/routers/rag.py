from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import openai
import logging

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.search import search_service
from app.services.web_search import web_search_service
from app.services.langgraph_workflow import LangGraphAgenticWorkflow
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])

# Keep the basic RAG for simple queries
class RAGRequest(BaseModel):
    question: str
    max_chunks: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.7
    include_sources: Optional[bool] = True

class RAGResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_method: str
    confidence: float
    processing_time_ms: float
    reasoning_steps: List[Dict[str, Any]]

# Advanced LangGraph-based endpoint
class AdvancedRAGRequest(BaseModel):
    question: str
    max_iterations: Optional[int] = 3
    enable_detailed_reasoning: Optional[bool] = True

class AdvancedRAGResponse(BaseModel):
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_method: str
    confidence: float
    processing_time_ms: float
    workflow_metadata: Dict[str, Any]
    reasoning_steps: List[Dict[str, Any]]
    langgraph_features: Dict[str, Any]

@router.post("/ask", response_model=RAGResponse)
async def ask_question(
    request: RAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Standard RAG Pipeline for Simple Questions
    
    This endpoint provides basic RAG functionality:
    - Semantic search of documents
    - Optional web search for missing information
    - Direct answer generation
    """
    
    start_time = datetime.utcnow()
    reasoning_steps = []
    
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Simple local search
        local_results = await search_service.search_documents(
            query=request.question,
            user=current_user,
            db=db,
            limit=request.max_chunks
        )
        
        reasoning_steps.append({
            "step": "local_search",
            "timestamp": datetime.utcnow().isoformat(),
            "action": f"Found {len(local_results)} relevant chunks",
            "details": {"chunks_found": len(local_results)}
        })
        
        # Simple web search if no local results
        web_results = []
        if len(local_results) == 0:
            try:
                web_results = await web_search_service.search(request.question, max_results=3)
                reasoning_steps.append({
                    "step": "web_search",
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": f"No local results, searched web and found {len(web_results)} results",
                    "details": {"web_results_found": len(web_results)}
                })
            except Exception as e:
                logger.warning(f"Web search failed: {e}")
        
        # Generate answer
        if local_results or web_results:
            context = build_simple_context(local_results, web_results)
            answer = await generate_simple_answer(request.question, context)
            sources = prepare_sources(local_results, web_results, request.include_sources)
            confidence = calculate_simple_confidence(local_results, web_results)
            retrieval_method = "hybrid" if web_results else "local_only"
        else:
            answer = "I couldn't find relevant information to answer your question. Please try rephrasing or ensure relevant documents are uploaded."
            sources = []
            confidence = 0.1
            retrieval_method = "no_results"
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return RAGResponse(
            question=request.question,
            answer=answer,
            sources=sources,
            retrieval_method=retrieval_method,
            confidence=confidence,
            processing_time_ms=processing_time,
            reasoning_steps=reasoning_steps
        )
        
    except Exception as e:
        logger.error(f"Standard RAG failed: {e}")
        return RAGResponse(
            question=request.question,
            answer=f"Error processing question: {str(e)}",
            sources=[],
            retrieval_method="error",
            confidence=0.0,
            processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            reasoning_steps=reasoning_steps + [{"error": str(e)}]
        )

@router.post("/ask-advanced", response_model=AdvancedRAGResponse)
async def ask_question_advanced(
    request: AdvancedRAGRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Advanced Agentic RAG Pipeline with LangGraph Workflow Management
    
    This endpoint demonstrates sophisticated agentic capabilities:
    - LangGraph-based state management and conditional routing
    - Multi-stage autonomous decision making 
    - Iterative refinement with structured reasoning
    - Full transparency of workflow execution
    - Hybrid retrieval with intelligent source selection
    
    Use this for complex questions requiring research-grade analysis.
    """
    
    start_time = datetime.utcnow()
    
    try:
        # Input validation
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if len(request.question) > 3000:
            raise HTTPException(status_code=400, detail="Question too long (max 3000 characters)")
        
        # Initialize and execute LangGraph workflow
        langgraph_workflow = LangGraphAgenticWorkflow(search_service, web_search_service)
        
        logger.info(f"Starting advanced LangGraph workflow for: '{request.question[:100]}...'")
        
        workflow_result = await langgraph_workflow.execute_langgraph_workflow(
            question=request.question,
            user=current_user,
            db=db
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(f"Advanced workflow completed in {processing_time:.2f}ms")
        
        return AdvancedRAGResponse(
            question=request.question,
            answer=workflow_result["answer"],
            sources=workflow_result["sources"],
            retrieval_method=workflow_result["retrieval_method"],
            confidence=workflow_result["confidence"],
            processing_time_ms=processing_time,
            workflow_metadata=workflow_result["workflow_metadata"],
            reasoning_steps=workflow_result["reasoning_steps"],
            langgraph_features=workflow_result.get("langgraph_features", {})
        )
        
    except Exception as e:
        logger.error(f"Advanced workflow failed: {str(e)}")
        error_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AdvancedRAGResponse(
            question=request.question,
            answer=f"Advanced workflow encountered an error: {str(e)}",
            sources=[],
            retrieval_method="error",
            confidence=0.0,
            processing_time_ms=error_time,
            workflow_metadata={"error": str(e), "workflow_type": "langgraph_failed"},
            reasoning_steps=[{
                "node": "error",
                "action": "Workflow failed", 
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }],
            langgraph_features={"error": True, "error_message": str(e)}
        )

# Helper functions for standard RAG
def build_simple_context(local_results: List, web_results: List) -> str:
    """Build context for standard RAG"""
    context_parts = []
    
    if local_results:
        context_parts.append("=== DOCUMENTS ===")
        for chunk, similarity in local_results:
            doc_name = chunk.document.filename if hasattr(chunk, 'document') else 'Unknown'
            context_parts.append(f"Document: {doc_name} (Relevance: {similarity:.3f})")
            context_parts.append(f"Content: {chunk.chunk_text}")
            context_parts.append("---")
    
    if web_results:
        context_parts.append("=== WEB RESULTS ===")
        for result in web_results:
            context_parts.append(f"Title: {result.title}")
            context_parts.append(f"Content: {result.content}")
            context_parts.append("---")
    
    return "\n".join(context_parts)

async def generate_simple_answer(question: str, context: str) -> str:
    """Generate answer using GPT-4o"""
    client = openai.OpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""Answer this question based on the provided context.

Question: {question}

Context:
{context}

Instructions:
1. Answer based only on the provided context
2. Cite sources appropriately
3. Be concise but comprehensive
4. If context is insufficient, acknowledge limitations

Answer:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o consistently
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"

def prepare_sources(local_results: List, web_results: List, include_sources: bool) -> List[Dict]:
    """Prepare source citations"""
    if not include_sources:
        return []
    
    sources = []
    
    for chunk, similarity in local_results:
        sources.append({
            "type": "document",
            "document_name": chunk.document.filename if hasattr(chunk, 'document') else 'Unknown',
            "page_number": chunk.page_number,
            "similarity_score": similarity,
            "text_preview": chunk.chunk_text[:200] + "..."
        })
    
    for result in web_results:
        sources.append({
            "type": "web",
            "title": result.title,
            "url": result.url,
            "score": result.score,
            "text_preview": result.content[:200] + "..."
        })
    
    return sources

def calculate_simple_confidence(local_results: List, web_results: List) -> float:
    """Calculate confidence for standard RAG"""
    if not local_results and not web_results:
        return 0.1
    
    base_confidence = 0.6
    if local_results:
        avg_similarity = sum(sim for _, sim in local_results) / len(local_results)
        base_confidence += avg_similarity * 0.3
    
    if web_results:
        base_confidence += 0.1
    
    return min(base_confidence, 1.0)

# Utility endpoints
@router.get("/capabilities")
async def get_rag_capabilities():
    """Get available RAG capabilities and recommendations"""
    return {
        "endpoints": {
            "/rag/ask": {
                "name": "Standard RAG",
                "description": "Fast, direct answers for simple questions",
                "best_for": ["Factual queries", "Simple document lookup", "Quick answers"],
                "features": ["Local search", "Basic web search", "Source citation"]
            },
            "/rag/ask-advanced": {
                "name": "Advanced Agentic RAG",
                "description": "Sophisticated multi-stage analysis with LangGraph",
                "best_for": ["Complex research questions", "Comparative analysis", "Multi-step reasoning"],
                "features": ["LangGraph workflow", "Autonomous decision making", "Iterative refinement", "Full transparency"]
            }
        },
        "recommendations": {
            "simple_facts": "Use /rag/ask",
            "document_lookup": "Use /rag/ask", 
            "complex_analysis": "Use /rag/ask-advanced",
            "comparative_research": "Use /rag/ask-advanced",
            "multi_step_reasoning": "Use /rag/ask-advanced"
        }
    }

@router.get("/health")
async def rag_health_check():
    """Health check for RAG system"""
    return {
        "status": "healthy",
        "components": {
            "openai_configured": bool(settings.openai_api_key),
            "search_service": "available",
            "web_search_service": "available", 
            "langgraph_workflow": "available",
            "database": "connected"
        },
        "models": {
            "generation_model": "gpt-4o",
            "embedding_model": "text-embedding-3-small"
        }
    }