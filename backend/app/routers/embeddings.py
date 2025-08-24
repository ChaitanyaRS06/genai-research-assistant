from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.embeddings import embedding_service
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

class EmbeddingResponse(BaseModel):
    message: str
    processed: Optional[int] = None
    failed: Optional[int] = None
    details: Optional[list] = None

class EmbeddingStatsResponse(BaseModel):
    total_chunks: int
    embedded_chunks: int
    chunks_without_embeddings: int
    embedding_coverage: float
    documents_with_embeddings: int
    total_documents_with_chunks: int
    embedding_model: str
    embedding_dimension: int

@router.post("/generate/{document_id}", response_model=EmbeddingResponse)
async def generate_document_embeddings(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate embeddings for a specific document.
    
    - **document_id**: ID of the document to process
    
    Admin users can generate embeddings for any document.
    Regular users can only process their own documents.
    """
    from app.models import Document
    
    # Verify document exists and user has access
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be processed before generating embeddings"
        )
    
    # Generate embeddings
    success = await embedding_service.embed_document_chunks(document_id, db)
    
    if success:
        return EmbeddingResponse(
            message=f"Successfully generated embeddings for document: {document.original_filename}"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings"
        )

@router.post("/generate-all", response_model=EmbeddingResponse)
async def generate_all_embeddings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate embeddings for all documents that don't have them yet.
    
    This endpoint is typically restricted to admin users due to potential
    high OpenAI API usage costs.
    """
    
    # Restrict to admin users for cost control
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for bulk embedding generation"
        )
    
    results = await embedding_service.embed_all_documents(db)
    
    return EmbeddingResponse(
        message=f"Completed bulk embedding generation",
        processed=results["processed"],
        failed=results["failed"],
        details=results.get("details", [])
    )

@router.get("/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about embeddings in the database.
    
    Shows coverage, model used, and processing status.
    """
    
    stats = embedding_service.get_embedding_stats(db)
    
    return EmbeddingStatsResponse(**stats)

@router.delete("/reset/{document_id}")
async def reset_document_embeddings(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove all embeddings for a specific document.
    
    Useful for re-generating embeddings with different models or parameters.
    Admin users can reset any document, regular users only their own.
    """
    from app.models import Document, DocumentChunk
    
    # Verify document exists and user has access
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Reset embeddings to None
    chunks_updated = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).update({"embedding": None})
    
    db.commit()
    
    return {
        "message": f"Reset embeddings for {chunks_updated} chunks in document: {document.original_filename}"
    }