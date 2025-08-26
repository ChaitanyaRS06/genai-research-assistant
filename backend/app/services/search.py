# backend/app/services/search.py - CORRECTED VERSION

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import DocumentChunk, Document, User
from app.services.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)

class SearchService:
    """Service for semantic search using pgvector similarity"""
    
    def __init__(self, similarity_threshold: float = 0.7, max_results: int = 10):
        """
        Initialize search service.
        
        Args:
            similarity_threshold: Minimum cosine similarity score (0-1)
            max_results: Maximum number of chunks to return
        """
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
    
    async def search_documents(
        self, 
        query: str, 
        user: User, 
        db: Session,
        limit: Optional[int] = None,
        document_ids: Optional[List[int]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Perform semantic search across document chunks.
        
        Args:
            query: Search query text
            user: Current user (for access control)
            db: Database session
            limit: Override default result limit
            document_ids: Optional filter to specific documents
            
        Returns:
            List of (DocumentChunk, similarity_score) tuples, ordered by relevance
        """
        try:
            # Generate embedding for the search query
            logger.info(f"Generating embedding for query: '{query[:50]}...'")
            query_embeddings = await embedding_service.generate_embeddings([query])
            
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            result_limit = limit or self.max_results
            
            logger.info(f"Query embedding generated, length: {len(query_embedding)}")
            
            # CORRECTED: Use actual database column names
            base_query = """
                SELECT 
                    dc.id,
                    dc.chunk_text,
                    dc.chunk_index,
                    dc.page_number,
                    dc.document_id,
                    d.filename,
                    d.owner_id,
                    1 - (dc.embedding <=> :query_embedding) as similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.embedding IS NOT NULL
                    AND (1 - (dc.embedding <=> :query_embedding)) >= :threshold
            """
            
            # Add user access control
            if not user.is_admin:
                base_query += " AND d.owner_id = :user_id"
            
            # Add document filter if specified (ignore [0] as invalid)
            if document_ids and document_ids != [0]:
                base_query += " AND d.id = ANY(:document_ids)"
            
            # Add ordering and limit
            base_query += """
                ORDER BY (1 - (dc.embedding <=> :query_embedding)) DESC
                LIMIT :limit
            """
            
            # CORRECTED: Proper embedding format for pgvector
            params = {
                'query_embedding': str(query_embedding),  # List to string
                'threshold': self.similarity_threshold,
                'limit': result_limit
            }
            
            if not user.is_admin:
                params['user_id'] = user.id
                
            if document_ids and document_ids != [0]:
                params['document_ids'] = document_ids
            
            logger.info(f"Executing search with threshold: {self.similarity_threshold}, limit: {result_limit}")
            logger.info(f"User is admin: {user.is_admin}, User ID: {user.id}")
            
            # Execute the query
            result = db.execute(text(base_query), params)
            rows = result.fetchall()
            
            logger.info(f"Query returned {len(rows)} rows")
            
            # Convert results to DocumentChunk objects with scores
            search_results = []
            for row in rows:
                # Get the full DocumentChunk object
                chunk = db.query(DocumentChunk).filter(DocumentChunk.id == row.id).first()
                if chunk:
                    # Add document info for easier access
                    chunk.document = db.query(Document).filter(Document.id == chunk.document_id).first()
                    search_results.append((chunk, float(row.similarity)))
                    logger.debug(f"Found chunk {row.id} with similarity {row.similarity:.4f}")
            
            logger.info(f"Successfully found {len(search_results)} results for query: '{query[:50]}...'")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed with error: {str(e)}")
            logger.exception("Full traceback:")
            return []
    
    async def search_with_metadata(
        self,
        query: str,
        user: User,
        db: Session,
        limit: Optional[int] = None
    ) -> dict:
        """
        Perform search and return results with additional metadata.
        
        Returns:
            Dictionary with search results, query info, and statistics
        """
        logger.info(f"Starting search_with_metadata for query: '{query}'")
        results = await self.search_documents(query, user, db, limit)
        
        # Group results by document
        documents_found = {}
        total_chunks = len(results)
        
        for chunk, score in results:
            doc_id = chunk.document_id
            if doc_id not in documents_found:
                documents_found[doc_id] = {
                    'document_name': chunk.document.filename if hasattr(chunk, 'document') else 'Unknown',
                    'chunks': [],
                    'max_score': score
                }
            
            documents_found[doc_id]['chunks'].append({
                'chunk_index': chunk.chunk_index,
                'page_number': chunk.page_number,
                'text_preview': chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                'full_text': chunk.chunk_text,
                'similarity_score': round(score, 4)
            })
            
            # Update max score for document
            documents_found[doc_id]['max_score'] = max(documents_found[doc_id]['max_score'], score)
        
        result_dict = {
            'query': query,
            'total_results': total_chunks,
            'documents_searched': len(documents_found),
            'similarity_threshold': self.similarity_threshold,
            'results': documents_found,
            'raw_results': [
                {
                    'chunk_text': chunk.chunk_text,
                    'document_name': chunk.document.filename if hasattr(chunk, 'document') else 'Unknown',
                    'page_number': chunk.page_number,
                    'similarity_score': round(score, 4)
                }
                for chunk, score in results
            ]
        }
        
        logger.info(f"Returning {total_chunks} results across {len(documents_found)} documents")
        return result_dict
    
    def get_search_stats(self, db: Session, user: User) -> dict:
        """Get statistics about searchable content for current user."""
        
        try:
            if user.is_admin:
                total_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.embedding.isnot(None)
                ).count()
                total_docs = db.query(Document).join(DocumentChunk).filter(
                    DocumentChunk.embedding.isnot(None)
                ).distinct().count()
            else:
                total_chunks = db.query(DocumentChunk).join(Document).filter(
                    Document.owner_id == user.id,
                    DocumentChunk.embedding.isnot(None)
                ).count()
                total_docs = db.query(Document).join(DocumentChunk).filter(
                    Document.owner_id == user.id,
                    DocumentChunk.embedding.isnot(None)
                ).distinct().count()
            
            return {
                'searchable_chunks': total_chunks,
                'searchable_documents': total_docs,
                'similarity_threshold': self.similarity_threshold,
                'max_results_per_query': self.max_results,
                'user_access': 'admin' if user.is_admin else 'user_only',
                'embedding_model': 'text-embedding-3-small',
                'vector_dimensions': 1536
            }
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {
                'searchable_chunks': 0,
                'searchable_documents': 0,
                'error': str(e)
            }

# Global instance
search_service = SearchService()