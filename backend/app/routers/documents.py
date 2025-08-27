# 1. FIXED documents.py - Add missing process endpoint
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Document
from app.services.document_processor import process_uploaded_document, get_document_stats
from pydantic import BaseModel

router = APIRouter(prefix="/documents", tags=["documents"])

class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    status: str
    created_at: str
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024

def validate_pdf_file(file: UploadFile) -> None:
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type")

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    validate_pdf_file(file)
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    file_id = str(uuid.uuid4())
    unique_filename = f"{file_id}{Path(file.filename).suffix}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    db_document = Document(
        filename=unique_filename, 
        original_filename=file.filename,
        file_size=len(file_content), 
        content_type=file.content_type,
        status="uploaded", 
        upload_path=str(file_path), 
        owner_id=current_user.id
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return DocumentResponse(
        id=db_document.id, 
        filename=db_document.filename,
        original_filename=db_document.original_filename,
        file_size=db_document.file_size, 
        status=db_document.status,
        created_at=db_document.created_at.isoformat()
    )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.is_admin:
        documents = db.query(Document).all()
    else:
        documents = db.query(Document).filter(Document.owner_id == current_user.id).all()
    
    return DocumentListResponse(
        documents=[DocumentResponse(
            id=doc.id, 
            filename=doc.filename, 
            original_filename=doc.original_filename,
            file_size=doc.file_size, 
            status=doc.status, 
            created_at=doc.created_at.isoformat()
        ) for doc in documents],
        total_count=len(documents)
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details and metadata"""
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id, 
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        status=document.status,
        created_at=document.created_at.isoformat()
    )

# THIS WAS MISSING - Add the process endpoint
@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract text and create chunks from uploaded PDF"""
    
    # Verify document exists and user has access
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status == "completed":
        return {"message": f"Document {document.original_filename} already processed"}
    
    if document.status == "processing":
        return {"message": f"Document {document.original_filename} is currently being processed"}
        
    if document.status != "uploaded":
        raise HTTPException(
            status_code=400, 
            detail=f"Document status is {document.status}, cannot process"
        )
    
    # Process the document
    success = await process_uploaded_document(document_id, db)
    
    if success:
        return {
            "message": f"Successfully processed document: {document.original_filename}",
            "document_id": document_id,
            "status": "completed"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to process document"
        )

@router.get("/{document_id}/stats")
async def get_document_processing_stats(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing statistics for a document"""
    
    # Verify document exists and user has access
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    stats = get_document_stats(document_id, db)
    return stats

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int, 
    limit: int = 10, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """View extracted text chunks from a processed document"""
    
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id, 
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    from app.models import DocumentChunk
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).limit(limit).all()
    
    return {
        "document_id": document_id,
        "document_name": document.original_filename,
        "document_status": document.status,
        "total_chunks": len(chunks),
        "chunks": [
            {
                "index": chunk.chunk_index, 
                "page": chunk.page_number,
                "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                "full_length": len(chunk.chunk_text)
            } 
            for chunk in chunks
        ]
    }

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete document and associated data"""
    
    # Verify document exists and user has access
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == current_user.id
        ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete physical file
    try:
        if document.upload_path and Path(document.upload_path).exists():
            os.remove(document.upload_path)
    except Exception as e:
        print(f"Warning: Could not delete file {document.upload_path}: {e}")
    
    # Delete from database (chunks will cascade delete)
    db.delete(document)
    db.commit()
    
    return {"message": f"Deleted document: {document.original_filename}"}


# 2. IMPROVED document_processor.py - Better error handling and logging
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List
import logging

from app.models import Document, DocumentChunk
from app.services.pdf_processing import process_pdf_file

logger = logging.getLogger(__name__)

async def process_uploaded_document(document_id: int, db: Session) -> bool:
    """
    Process an uploaded document: extract text, chunk it, and store in database.
    
    Args:
        document_id: ID of the document to process
        db: Database session
        
    Returns:
        True if processing successful, False otherwise
    """
    
    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        logger.error(f"Document {document_id} not found in database")
        return False
    
    logger.info(f"Processing document {document_id}: {document.original_filename} (status: {document.status})")
    
    if document.status == "completed":
        logger.info(f"Document {document_id} already processed successfully")
        return True
    elif document.status == "processing":
        logger.warning(f"Document {document_id} is currently being processed")
        return False
    elif document.status != "uploaded":
        logger.warning(f"Document {document_id} status is {document.status}, cannot process")
        return False

    try:
        # Update status to processing
        document.status = "processing"
        db.commit()
        logger.info(f"Set document {document_id} status to 'processing'")
        
        # Verify file exists
        file_path = Path(document.upload_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Processing PDF file: {file_path} ({file_path.stat().st_size} bytes)")
        
        # Process the PDF file
        chunks = process_pdf_file(file_path)
        logger.info(f"PDF processing returned {len(chunks) if chunks else 0} chunks")
        
        if not chunks:
            raise ValueError("No text chunks extracted from PDF - file may be corrupt or contain no text")
        
        # Delete existing chunks if any (for reprocessing)
        existing_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
        if existing_chunks > 0:
            logger.info(f"Deleting {existing_chunks} existing chunks for reprocessing")
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        
        # Store chunks in database
        db_chunks = []
        for i, chunk_data in enumerate(chunks):
            logger.debug(f"Creating chunk {i}: page {chunk_data.page_number}, {len(chunk_data.text)} chars")
            
            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_data.text,
                chunk_index=chunk_data.chunk_index,
                page_number=chunk_data.page_number,
                embedding=None  # Will be generated separately
            )
            db_chunks.append(db_chunk)
        
        # Batch insert all chunks
        logger.info(f"Inserting {len(db_chunks)} chunks into database")
        db.add_all(db_chunks)
        
        # Update document status to completed
        document.status = "completed"
        db.commit()
        
        logger.info(f"✓ Successfully processed document {document_id}: {len(chunks)} chunks created")
        return True
        
    except Exception as e:
        # Rollback changes and mark as failed
        logger.error(f"✗ Failed to process document {document_id}: {str(e)}")
        logger.exception("Full error details:")
        
        try:
            db.rollback()
            document.status = "failed"
            db.commit()
            logger.info(f"Set document {document_id} status to 'failed'")
        except Exception as rollback_error:
            logger.error(f"Failed to rollback document {document_id}: {rollback_error}")
        
        return False

def get_document_chunks(document_id: int, db: Session) -> List[DocumentChunk]:
    """Get all chunks for a document."""
    return db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).all()

def get_document_stats(document_id: int, db: Session) -> dict:
    """Get statistics about a processed document."""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return {"error": f"Document {document_id} not found"}
    
    chunks = get_document_chunks(document_id, db)
    
    if not chunks:
        return {
            "document_id": document_id,
            "filename": document.original_filename,
            "status": document.status,
            "total_chunks": 0,
            "total_characters": 0,
            "pages": 0,
            "has_embeddings": False,
            "processing_ready": document.status == "uploaded"
        }
    
    total_chars = sum(len(chunk.chunk_text) for chunk in chunks)
    max_page = max(chunk.page_number for chunk in chunks if chunk.page_number) if chunks else 0
    has_embeddings = any(chunk.embedding is not None for chunk in chunks)
    
    return {
        "document_id": document_id,
        "filename": document.original_filename,
        "status": document.status,
        "total_chunks": len(chunks),
        "total_characters": total_chars,
        "pages": max_page,
        "avg_chunk_size": total_chars // len(chunks) if chunks else 0,
        "has_embeddings": has_embeddings,
        "embedding_coverage": sum(1 for chunk in chunks if chunk.embedding is not None) / len(chunks) * 100 if chunks else 0
    }


# 3. FIXED search service - Add better debugging
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Tuple, Optional
from app.models import DocumentChunk, Document, User
import logging

logger = logging.getLogger(__name__)

class SearchService:
    """Service for semantic search using pgvector"""
    
    def __init__(self, similarity_threshold: float = 0.5):
        self.similarity_threshold = similarity_threshold
    
    async def search_documents(
        self, 
        query: str, 
        user: User, 
        db: Session, 
        limit: int = 5
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Perform semantic search across document chunks using embeddings.
        
        Args:
            query: Search query text
            user: Current user (for permission filtering)
            db: Database session
            limit: Maximum number of results to return
            
        Returns:
            List of tuples (DocumentChunk, similarity_score)
        """
        
        logger.info(f"Starting search for user {user.id} (admin: {user.is_admin}): '{query}'")
        
        try:
            # First, check if we have any embedded chunks
            if user.is_admin:
                total_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.embedding.isnot(None)
                ).count()
                logger.info(f"Admin user: {total_chunks} total embedded chunks available")
            else:
                total_chunks = db.query(DocumentChunk).join(Document).filter(
                    Document.owner_id == user.id,
                    DocumentChunk.embedding.isnot(None)
                ).count()
                logger.info(f"Regular user: {total_chunks} embedded chunks available for user {user.id}")
            
            if total_chunks == 0:
                logger.warning("No embedded chunks found - search will return empty results")
                return []
            
            # Generate query embedding
            from app.services.embeddings import embedding_service
            query_embeddings = await embedding_service.generate_embeddings([query])
            
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions")
            
            # Build the search query with permission filtering
            if user.is_admin:
                # Admin can search all documents
                search_query = db.query(
                    DocumentChunk,
                    func.cosine_similarity(DocumentChunk.embedding, query_embedding).label('similarity')
                ).filter(
                    DocumentChunk.embedding.isnot(None)
                ).order_by(
                    func.cosine_similarity(DocumentChunk.embedding, query_embedding).desc()
                ).limit(limit)
                
                logger.info("Using admin search query (all documents)")
            else:
                # Regular users can only search their own documents
                search_query = db.query(
                    DocumentChunk,
                    func.cosine_similarity(DocumentChunk.embedding, query_embedding).label('similarity')
                ).join(Document).filter(
                    Document.owner_id == user.id,
                    DocumentChunk.embedding.isnot(None)
                ).order_by(
                    func.cosine_similarity(DocumentChunk.embedding, query_embedding).desc()
                ).limit(limit)
                
                logger.info(f"Using user search query (user {user.id} documents only)")
            
            # Execute the search
            results = search_query.all()
            logger.info(f"Search query returned {len(results)} results")
            
            # Filter by similarity threshold and log details
            filtered_results = []
            for chunk, similarity in results:
                logger.debug(f"Result: similarity={similarity:.3f}, doc={chunk.document.original_filename}, chunk={chunk.chunk_index}")
                
                if similarity >= self.similarity_threshold:
                    filtered_results.append((chunk, float(similarity)))
                else:
                    logger.debug(f"Filtered out result with similarity {similarity:.3f} (below threshold {self.similarity_threshold})")
            
            logger.info(f"Returning {len(filtered_results)} results above similarity threshold {self.similarity_threshold}")
            
            if filtered_results:
                avg_similarity = sum(sim for _, sim in filtered_results) / len(filtered_results)
                logger.info(f"Average similarity of returned results: {avg_similarity:.3f}")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            logger.exception("Full search error details:")
            return []

# Global search service instance
search_service = SearchService(similarity_threshold=0.3)  # Lower threshold for more results