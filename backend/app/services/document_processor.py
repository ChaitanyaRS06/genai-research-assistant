from sqlalchemy.orm import Session
from pathlib import Path
from typing import List

from app.models import Document, DocumentChunk
from app.services.pdf_processing import process_pdf_file
import logging

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
    
    if document.status != "uploaded":
        if document.status == "completed":
            logger.info(f"Document {document_id} already processed successfully")
            return True  # Return success since it's already done
        elif document.status == "processing":
            logger.warning(f"Document {document_id} is currently being processed")
            return False
        else:
            logger.warning(f"Document {document_id} status is {document.status}, cannot process")
            return False

    
    try:
        # Update status to processing
        document.status = "processing"
        db.commit()
        
        # Process the PDF file
        file_path = Path(document.upload_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Processing PDF: {file_path}")
        chunks = process_pdf_file(file_path)
        
        if not chunks:
            raise ValueError("No text chunks extracted from PDF")
        
        # Store chunks in database
        db_chunks = []
        for chunk_data in chunks:
            db_chunk = DocumentChunk(
                document_id=document.id,
                chunk_text=chunk_data.text,
                chunk_index=chunk_data.chunk_index,
                page_number=chunk_data.page_number,
                # embedding will be generated later
                embedding=None
            )
            db_chunks.append(db_chunk)
        
        # Batch insert all chunks
        db.add_all(db_chunks)
        
        # Update document status to completed
        document.status = "completed"
        db.commit()
        
        logger.info(f"Successfully processed document {document_id}: {len(chunks)} chunks created")
        return True
        
    except Exception as e:
        # Rollback changes and mark as failed
        db.rollback()
        document.status = "failed"
        db.commit()
        
        logger.error(f"Failed to process document {document_id}: {str(e)}")
        return False

def get_document_chunks(document_id: int, db: Session) -> List[DocumentChunk]:
    """
    Get all chunks for a document.
    
    Args:
        document_id: ID of the document
        db: Database session
        
    Returns:
        List of DocumentChunk objects
    """
    return db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index).all()

def get_document_stats(document_id: int, db: Session) -> dict:
    """
    Get statistics about a processed document.
    
    Args:
        document_id: ID of the document
        db: Database session
        
    Returns:
        Dictionary with document statistics
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return {}
    
    chunks = get_document_chunks(document_id, db)
    
    if not chunks:
        return {
            "document_id": document_id,
            "status": document.status,
            "total_chunks": 0,
            "total_characters": 0,
            "pages": 0
        }
    
    total_chars = sum(len(chunk.chunk_text) for chunk in chunks)
    max_page = max(chunk.page_number for chunk in chunks if chunk.page_number)
    
    return {
        "document_id": document_id,
        "filename": document.original_filename,
        "status": document.status,
        "total_chunks": len(chunks),
        "total_characters": total_chars,
        "pages": max_page,
        "avg_chunk_size": total_chars // len(chunks) if chunks else 0
    }