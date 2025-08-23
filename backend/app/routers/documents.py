from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
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
async def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger processing of an uploaded document.
    
    - **document_id**: ID of the document to process
    """
    
    # Verify document belongs to current user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Process the document
    success = await process_uploaded_document(document_id, db)
    
    if success:
        stats = get_document_stats(document_id, db)
        return {
            "message": "Document processed successfully",
            "stats": stats
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed"
        )

@router.get("/{document_id}/stats")
async def get_document_statistics(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get processing statistics for a document.
    
    - **document_id**: ID of the document
    """
    
    # Verify document belongs to current user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    stats = get_document_stats(document_id, db)
    return stats
from app.auth import get_current_user
from app.models import User, Document
from pydantic import BaseModel

router = APIRouter(prefix="/documents", tags=["documents"])

# Pydantic schemas for responses
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

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

def validate_pdf_file(file: UploadFile) -> None:
    """Validate uploaded file is a PDF and within size limits"""
    
    # Check file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not allowed. Only PDF files are supported."
        )
    
    # Check content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are supported."
        )

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for processing.
    
    - **file**: PDF file to upload (max 10MB)
    
    Returns document metadata. The document will be processed asynchronously.
    """
    
    # Validate file
    validate_pdf_file(file)
    
    # Read file content and check size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {len(file_content)} bytes exceeds maximum allowed size of {MAX_FILE_SIZE} bytes"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    unique_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        db_document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type,
            status="uploaded",  # Will change to "processing" then "completed"
            upload_path=str(file_path),
            owner_id=current_user.id
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # TODO: Trigger async processing task here
        # For now, we'll process synchronously in the next step
        
        return DocumentResponse(
            id=db_document.id,
            filename=db_document.filename,
            original_filename=db_document.original_filename,
            file_size=db_document.file_size,
            status=db_document.status,
            created_at=db_document.created_at.isoformat()
        )
        
    except Exception as e:
        # Clean up file if database operation fails
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document"
        )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of user's uploaded documents.
    
    Returns all documents belonging to the current user.
    """
    
    documents = db.query(Document).filter(Document.owner_id == current_user.id).all()
    
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                status=doc.status,
                created_at=doc.created_at.isoformat()
            )
            for doc in documents
        ],
        total_count=len(documents)
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific document.
    
    - **document_id**: ID of the document to retrieve
    """
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        status=document.status,
        created_at=document.created_at.isoformat()
    )

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated data.
    
    - **document_id**: ID of the document to delete
    """
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    try:
        # Delete file from disk
        if document.upload_path and Path(document.upload_path).exists():
            Path(document.upload_path).unlink()
        
        # Delete from database (cascading delete will remove chunks too)
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

@router.post("/{document_id}/process")
async def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger processing of an uploaded document.
    
    - **document_id**: ID of the document to process
    """
    
    # Verify document belongs to current user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Process the document
    success = await process_uploaded_document(document_id, db)
    
    if success:
        stats = get_document_stats(document_id, db)
        return {
            "message": "Document processed successfully",
            "stats": stats
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed"
        )

@router.get("/{document_id}/stats")
async def get_document_statistics(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get processing statistics for a document.
    
    - **document_id**: ID of the document
    """
    
    # Verify document belongs to current user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    stats = get_document_stats(document_id, db)
    return stats

@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get text chunks for a document (for debugging)"""
    
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).limit(limit).all()
    
    return [{
        "chunk_index": chunk.chunk_index,
        "page_number": chunk.page_number,
        "text_preview": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
        "char_count": len(chunk.chunk_text)
    } for chunk in chunks]