import openai
from typing import List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Document, DocumentChunk
import logging
import asyncio

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and managing document embeddings"""
    
    def __init__(self, model: str = "text-embedding-3-small", batch_size: int = 100):
        """
        Initialize embedding service.
        
        Args:
            model: OpenAI embedding model to use
            batch_size: Number of texts to process in one API call
        """
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.batch_size = batch_size
        self.embedding_dimension = 1536  # text-embedding-3-small dimension
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI API.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is list of floats)
        """
        if not texts:
            return []
        
        try:
            # OpenAI API call (synchronous in async wrapper)
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Generated {len(embeddings)} embeddings using {self.model}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def embed_document_chunks(self, document_id: int, db: Session) -> bool:
        """
        Generate embeddings for all chunks of a specific document.
        
        Args:
            document_id: ID of document to process
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get document and verify it exists
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return False
            
            # Get all chunks for this document that don't have embeddings yet
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.embedding.is_(None)
            ).all()
            
            if not chunks:
                logger.info(f"Document {document_id} already has embeddings or no chunks")
                return True
            
            logger.info(f"Processing {len(chunks)} chunks for document {document_id}")
            
            # Process chunks in batches
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                texts = [chunk.chunk_text for chunk in batch]
                
                # Generate embeddings for this batch
                embeddings = await self.generate_embeddings(texts)
                
                # Store embeddings in database
                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding
                
                # Commit this batch
                db.commit()
                
                logger.info(f"Processed batch {i//self.batch_size + 1}/{(len(chunks)-1)//self.batch_size + 1}")
                
                # Rate limiting - avoid hitting OpenAI limits
                if i + self.batch_size < len(chunks):
                    await asyncio.sleep(0.5)  # Small delay between batches
            
            logger.info(f"Successfully embedded all chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed document {document_id}: {str(e)}")
            db.rollback()
            return False
    
    async def embed_all_documents(self, db: Session) -> dict:
        """
        Generate embeddings for all documents that don't have them yet.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with processing results
        """
        # Get all documents with chunks but no embeddings
        documents = db.query(Document).join(DocumentChunk).filter(
            DocumentChunk.embedding.is_(None)
        ).distinct().all()
        
        if not documents:
            return {"message": "All documents already have embeddings", "processed": 0, "failed": 0}
        
        results = {"processed": 0, "failed": 0, "details": []}
        
        logger.info(f"Processing embeddings for {len(documents)} documents")
        
        for document in documents:
            success = await self.embed_document_chunks(document.id, db)
            
            if success:
                results["processed"] += 1
                results["details"].append({
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "status": "failed"
                })
        
        return results
    
    def get_embedding_stats(self, db: Session) -> dict:
        """
        Get statistics about embeddings in the database.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with embedding statistics
        """
        total_chunks = db.query(DocumentChunk).count()
        embedded_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).count()
        
        documents_with_embeddings = db.query(Document).join(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).distinct().count()
        
        total_documents = db.query(Document).join(DocumentChunk).distinct().count()
        
        return {
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_chunks,
            "chunks_without_embeddings": total_chunks - embedded_chunks,
            "embedding_coverage": round((embedded_chunks / total_chunks * 100), 2) if total_chunks > 0 else 0,
            "documents_with_embeddings": documents_with_embeddings,
            "total_documents_with_chunks": total_documents,
            "embedding_model": self.model,
            "embedding_dimension": self.embedding_dimension
        }

# Global instance
embedding_service = EmbeddingService()