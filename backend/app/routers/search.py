from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import text

from app.models import DocumentChunk, Document
from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.search import search_service

router = APIRouter(prefix="/search", tags=["search"])

class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 10
    document_ids: Optional[List[int]] = None

class SearchResult(BaseModel):
    query: str
    total_results: int
    documents_searched: int
    similarity_threshold: float
    results: dict
    raw_results: List[dict]

@router.post("/", response_model=SearchResult)
async def semantic_search(
    search_request: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across document chunks.
    
    - **query**: Natural language search query
    - **limit**: Maximum number of results to return (default: 10)  
    - **document_ids**: Optional list of specific document IDs to search within
    
    Returns chunks ranked by semantic similarity with scores and metadata.
    Admin users can search all documents, regular users only their own.
    """
    
    if not search_request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )
    
    if len(search_request.query) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Search query too long (max 1000 characters)"
        )
    
    results = await search_service.search_with_metadata(
        query=search_request.query,
        user=current_user,
        db=db,
        limit=search_request.limit
    )
    
    return SearchResult(**results)

@router.get("/quick")
async def quick_search(
    q: str = Query(..., description="Search query", max_length=500),
    limit: int = Query(5, description="Number of results", le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick search endpoint for simple queries.
    
    - **q**: Search query string
    - **limit**: Maximum results (default: 5, max: 20)
    
    Returns simplified search results for fast queries.
    """
    
    results = await search_service.search_documents(
        query=q,
        user=current_user,
        db=db,
        limit=limit
    )
    
    return {
        "query": q,
        "results": [
            {
                "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                "document": chunk.document.original_filename,
                "page": chunk.page_number,
                "score": round(score, 3)
            }
            for chunk, score in results
        ],
        "total": len(results)
    }

@router.get("/stats")
async def get_search_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about searchable content.
    
    Shows available chunks, documents, and search configuration.
    """
    
    stats = search_service.get_search_stats(db, current_user)
    return stats

@router.post("/test")
async def test_search_similarity(
    query1: str,
    query2: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test endpoint to compare similarity between two queries.
    
    Useful for understanding how the semantic search works.
    """
    
    # Generate embeddings for both queries
    from app.services.embeddings import embedding_service
    
    embeddings = await embedding_service.generate_embeddings([query1, query2])
    if len(embeddings) != 2:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings")
    
    # Calculate cosine similarity manually
    import numpy as np
    
    embedding1 = np.array(embeddings[0])
    embedding2 = np.array(embeddings[1])
    
    # Cosine similarity formula
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    similarity = dot_product / (norm1 * norm2)
    
    return {
        "query1": query1,
        "query2": query2,
        "cosine_similarity": float(similarity),
        "similarity_percentage": round(float(similarity) * 100, 2),
        "interpretation": "high" if similarity > 0.8 else "medium" if similarity > 0.6 else "low"
    }


@router.get("/debug")
async def debug_search(db: Session = Depends(get_db)):
    """Debug endpoint to test raw SQL query"""
    
    # Get a real embedding from the database
    sample_embedding = db.execute(text("SELECT embedding FROM document_chunks LIMIT 1")).scalar()
    
    # Test the exact query with real embedding
    query = text("""
        SELECT dc.id, dc.chunk_text, dc.chunk_index, 
               1 - (dc.embedding <=> :sample_embedding::vector) as similarity
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE dc.embedding IS NOT NULL
            AND 1 - (dc.embedding <=> :sample_embedding::vector) >= 0.1
        ORDER BY similarity DESC
        LIMIT 5
    """)
    
    result = db.execute(query, {"sample_embedding": sample_embedding})
    rows = result.fetchall()
    
    return {
        "test_results": len(rows),
        "sample_embedding_type": type(sample_embedding).__name__,
        "embedding_length": len(str(sample_embedding)) if sample_embedding else 0
    }

# Replace the debug endpoint in your search.py with this version

# Replace the debug endpoint in your search.py with this version

@router.get("/debug/detailed")
async def debug_search_detailed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detailed debug endpoint to diagnose search issues"""
    
    debug_info = {
        "step_1_chunks": {},
        "step_2_model_inspection": {},
        "step_3_query_embedding": {},
        "step_4_sql_test": {},
        "step_5_search_service": {}
    }
    
    try:
        # Step 1: Check chunks with embeddings
        chunk_count = db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).count()
        
        debug_info["step_1_chunks"] = {
            "total_chunks_with_embeddings": chunk_count,
            "status": "success" if chunk_count > 0 else "error"
        }
        
        # Step 2: Inspect the actual model attributes
        sample_chunk = db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).first()
        
        if sample_chunk:
            # Get all attributes of the DocumentChunk object
            chunk_attributes = [attr for attr in dir(sample_chunk) if not attr.startswith('_')]
            
            # Try to get the text content - it might be named differently
            content_field = None
            content_value = None
            
            for field in ['content', 'text', 'chunk_text', 'chunk_content', 'data']:
                if hasattr(sample_chunk, field):
                    content_field = field
                    content_value = getattr(sample_chunk, field)
                    break
            
            embedding_str = str(sample_chunk.embedding)
            debug_info["step_2_model_inspection"] = {
                "chunk_attributes": chunk_attributes,
                "content_field_found": content_field,
                "content_preview": content_value[:100] if content_value else "No text content found",
                "embedding_type": type(sample_chunk.embedding).__name__,
                "embedding_length": len(embedding_str),
                "embedding_preview": embedding_str[:100],
                "sample_chunk_id": sample_chunk.id,
                "status": "success"
            }
        
        # Step 3: Test query embedding generation
        from app.services.embeddings import embedding_service
        
        test_query = "RAG"
        query_embeddings = await embedding_service.generate_embeddings([test_query])
        
        if query_embeddings:
            query_embedding = query_embeddings[0]
            debug_info["step_3_query_embedding"] = {
                "query": test_query,
                "embedding_generated": True,
                "embedding_length": len(query_embedding),
                "embedding_preview": query_embedding[:3],
                "status": "success"
            }
            
            # Step 4: Test direct SQL with correct column names
            # Get the actual column name from the database
            column_info = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'document_chunks' 
                AND column_name LIKE '%content%' OR column_name LIKE '%text%'
            """)).fetchall()
            
            text_column = None
            if column_info:
                text_column = column_info[0][0]
            else:
                # Fallback - try common column names
                possible_columns = ['content', 'text', 'chunk_text', 'data']
                for col in possible_columns:
                    try:
                        test_query = text(f"SELECT {col} FROM document_chunks LIMIT 1")
                        result = db.execute(test_query)
                        text_column = col
                        break
                    except:
                        continue
            
            sql_results = []
            if text_column:
                sql_formats = [
                    str(query_embedding),
                    f"[{','.join(map(str, query_embedding))}]"
                ]
                
                for i, embedding_format in enumerate(sql_formats):
                    try:
                        sql_query = text(f"""
                            SELECT dc.id, dc.{text_column},
                                   1 - (dc.embedding <=> :query_embedding) as similarity
                            FROM document_chunks dc
                            WHERE dc.embedding IS NOT NULL
                            ORDER BY similarity DESC
                            LIMIT 3
                        """)
                        
                        result = db.execute(sql_query, {"query_embedding": embedding_format})
                        rows = result.fetchall()
                        
                        sql_results.append({
                            "format_index": i,
                            "format_preview": embedding_format[:50],
                            "results_found": len(rows),
                            "text_column_used": text_column,
                            "status": "success" if len(rows) > 0 else "no_results",
                            "sample_results": [
                                {
                                    "id": row.id,
                                    "similarity": float(row.similarity),
                                    "content_preview": getattr(row, text_column, "No content")[:50]
                                }
                                for row in rows[:2]
                            ]
                        })
                        
                    except Exception as e:
                        sql_results.append({
                            "format_index": i,
                            "format_preview": embedding_format[:50],
                            "status": "error",
                            "error": str(e)
                        })
            
            debug_info["step_4_sql_test"] = {
                "text_column_detected": text_column,
                "formats_tested": len(sql_formats) if text_column else 0,
                "results": sql_results,
                "status": "completed" if text_column else "no_text_column_found"
            }
            
            # Step 5: Test current search service
            try:
                from app.services.search import search_service
                
                results = await search_service.search_documents(
                    query=test_query,
                    user=current_user,
                    db=db,
                    limit=3
                )
                
                debug_info["step_5_search_service"] = {
                    "results_found": len(results),
                    "user_is_admin": current_user.is_admin,
                    "user_id": current_user.id,
                    "status": "success" if len(results) > 0 else "no_results"
                }
                
                if len(results) > 0:
                    debug_info["step_5_search_service"]["sample_results"] = [
                        {
                            "chunk_id": chunk.id,
                            "similarity": float(score),
                            "has_content_attr": hasattr(chunk, 'content'),
                            "chunk_attrs": [attr for attr in dir(chunk) if not attr.startswith('_') and not callable(getattr(chunk, attr))][:10]
                        }
                        for chunk, score in results[:2]
                    ]
                
            except Exception as e:
                debug_info["step_5_search_service"] = {
                    "status": "error",
                    "error": str(e)
                }
                import traceback
                debug_info["step_5_search_service"]["traceback"] = traceback.format_exc()
        
        else:
            debug_info["step_3_query_embedding"] = {
                "status": "error",
                "error": "Failed to generate query embedding"
            }
    
    except Exception as e:
        debug_info["global_error"] = str(e)
        import traceback
        debug_info["traceback"] = traceback.format_exc()
    
    return debug_info