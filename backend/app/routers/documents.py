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
async def upload_document(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
        filename=unique_filename, original_filename=file.filename,
        file_size=len(file_content), content_type=file.content_type,
        status="uploaded", upload_path=str(file_path), owner_id=current_user.id
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return DocumentResponse(
        id=db_document.id, filename=db_document.filename,
        original_filename=db_document.original_filename,
        file_size=db_document.file_size, status=db_document.status,
        created_at=db_document.created_at.isoformat()
    )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_admin:
        documents = db.query(Document).all()
    else:
        documents = db.query(Document).filter(Document.owner_id == current_user.id).all()
    
    return DocumentListResponse(
        documents=[DocumentResponse(
            id=doc.id, filename=doc.filename, original_filename=doc.original_filename,
            file_size=doc.file_size, status=doc.status, created_at=doc.created_at.isoformat()
        ) for doc in documents],
        total_count=len(documents)
    )

@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: int, limit: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_admin:
        document = db.query(Document).filter(Document.id == document_id).first()
    else:
        document = db.query(Document).filter(Document.id == document_id, Document.owner_id == current_user.id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    from app.models import DocumentChunk
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).limit(limit).all()
    
    return {
        "document_id": document_id,
        "total_chunks": len(chunks),
        "chunks": [{"index": chunk.chunk_index, "text": chunk.chunk_text[:200]} for chunk in chunks]
    }