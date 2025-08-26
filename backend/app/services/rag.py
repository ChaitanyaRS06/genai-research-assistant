# backend/app/services/rag.py
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import openai
import json
from datetime import datetime
from ..models import DocumentChunk, User
from ..config import get_settings
from .embeddings import EmbeddingService

class RAGResponse:
    def __init__(self, answer: str, sources: List[Dict], reasoning_steps: List[Dict], 
                 retrieval_method: str, confidence: float = 0.0):
        self.answer = answer
        self.sources = sources
        self.reasoning_steps = reasoning_steps
        self.retrieval_method = retrieval_method
        self.confidence = confidence
        self.timestamp = datetime.utcnow()

class RAGService:
    def __init__(self):
        self.settings = get_settings()
        self.client = openai.OpenAI(api_key=self.settings.openai_api_key)
        self.embedding_service = EmbeddingService()
        
    async def answer_question(self, question: str, user: User, db: Session, 
                            max_chunks: int = 5, similarity_threshold: float = 0.7) -> RAGResponse:
        """Main RAG pipeline with agentic decision making"""
        
        reasoning_steps = []
        reasoning_steps.append({
            "step": "query_analysis",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "Analyzing user question for retrieval strategy",
            "details": {"question_length": len(question), "user_type": "admin" if user.is_admin else "regular"}
        })
        
        # Step 1: Analyze question to determine retrieval strategy
        retrieval_strategy = await self._determine_retrieval_strategy(question)
        reasoning_steps.append({
            "step": "strategy_decision", 
            "timestamp": datetime.utcnow().isoformat(),
            "action": f"Decided on {retrieval_strategy} retrieval",
            "details": {"strategy": retrieval_strategy}
        })
        
        # Step 2: Perform semantic search on local documents
        local_results = await self._semantic_search(question, user, db, max_chunks, similarity_threshold)
        reasoning_steps.append({
            "step": "local_search",
            "timestamp": datetime.utcnow().isoformat(), 
            "action": f"Found {len(local_results)} relevant document chunks",
            "details": {"chunks_found": len(local_results), "avg_similarity": self._avg_similarity(local_results)}
        })
        
        # Step 3: Decide if we need web search
        need_web_search = await self._should_search_web(question, local_results, retrieval_strategy)
        
        web_results = []
        if need_web_search:
            reasoning_steps.append({
                "step": "web_search_decision",
                "timestamp": datetime.utcnow().isoformat(),
                "action": "Triggering web search for additional context",
                "details": {"reason": "Local results insufficient or question requires current information"}
            })
            web_results = await self._web_search(question)
            reasoning_steps.append({
                "step": "web_search_complete",
                "timestamp": datetime.utcnow().isoformat(),
                "action": f"Web search returned {len(web_results)} results", 
                "details": {"web_results_count": len(web_results)}
            })
        
        # Step 4: Combine results and generate answer
        combined_context = self._combine_context(local_results, web_results)
        reasoning_steps.append({
            "step": "context_preparation",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "Combined local and web results into context",
            "details": {"total_context_length": len(combined_context)}
        })
        
        # Step 5: Generate final answer
        answer = await self._generate_answer(question, combined_context, reasoning_steps)
        
        # Step 6: Prepare sources and response
        sources = self._prepare_sources(local_results, web_results)
        retrieval_method = "hybrid" if web_results else "local_only" 
        confidence = self._calculate_confidence(local_results, web_results)
        
        reasoning_steps.append({
            "step": "answer_generation",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "Generated final answer using LLM",
            "details": {"answer_length": len(answer), "confidence": confidence}
        })
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            reasoning_steps=reasoning_steps,
            retrieval_method=retrieval_method,
            confidence=confidence
        )
    
    async def _determine_retrieval_strategy(self, question: str) -> str:
        """Analyze question to determine optimal retrieval strategy"""
        
        current_time_indicators = [
            "current", "latest", "recent", "today", "now", "2024", "2025", 
            "this year", "this month", "trending", "breaking"
        ]
        
        local_knowledge_indicators = [
            "document", "report", "file", "uploaded", "our", "internal",
            "according to", "in the document", "the pdf"
        ]
        
        question_lower = question.lower()
        
        has_time_indicators = any(indicator in question_lower for indicator in current_time_indicators)
        has_local_indicators = any(indicator in question_lower for indicator in local_knowledge_indicators)
        
        if has_local_indicators and not has_time_indicators:
            return "local_first"
        elif has_time_indicators and not has_local_indicators:
            return "web_first"
        elif has_time_indicators and has_local_indicators:
            return "hybrid"
        else:
            return "adaptive"  # Start with local, expand to web if needed
    
    async def _semantic_search(self, query: str, user: User, db: Session, 
                             max_chunks: int, similarity_threshold: float) -> List[Tuple[DocumentChunk, float]]:
        """Perform semantic search using pgvector"""
        
        # Generate embedding for the query
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Build SQL query for vector similarity search
        if user.is_admin:
            # Admin can search all documents
            sql_query = text("""
                SELECT dc.*, d.title, d.filename, 
                       (dc.embedding <=> :query_embedding) as similarity_score
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.embedding IS NOT NULL
                  AND (dc.embedding <=> :query_embedding) < :threshold
                ORDER BY dc.embedding <=> :query_embedding
                LIMIT :max_chunks
            """)
        else:
            # Regular users can only search their own documents
            sql_query = text("""
                SELECT dc.*, d.title, d.filename,
                       (dc.embedding <=> :query_embedding) as similarity_score  
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.embedding IS NOT NULL
                  AND d.owner_id = :user_id
                  AND (dc.embedding <=> :query_embedding) < :threshold
                ORDER BY dc.embedding <=> :query_embedding
                LIMIT :max_chunks
            """)
        
        # Execute the query
        result = db.execute(sql_query, {
            "query_embedding": json.dumps(query_embedding),
            "threshold": 1.0 - similarity_threshold,  # Convert similarity to distance
            "max_chunks": max_chunks,
            "user_id": user.id if not user.is_admin else None
        })
        
        results = []
        for row in result:
            # Create DocumentChunk object from row data
            chunk = DocumentChunk(
                id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                start_page=row.start_page,
                end_page=row.end_page,
                embedding=row.embedding
            )
            chunk.document_title = row.title
            chunk.document_filename = row.filename
            similarity_score = 1.0 - row.similarity_score  # Convert distance back to similarity
            results.append((chunk, similarity_score))
        
        return results
    
    async def _should_search_web(self, question: str, local_results: List[Tuple[DocumentChunk, float]], 
                               strategy: str) -> bool:
        """Determine if web search is needed based on local results and strategy"""
        
        if strategy == "web_first":
            return True
        elif strategy == "local_first" and len(local_results) == 0:
            return True
        elif strategy == "hybrid":
            return True
        elif strategy == "adaptive":
            # Check if local results are sufficient
            if len(local_results) == 0:
                return True
            
            avg_similarity = self._avg_similarity(local_results)
            if avg_similarity < 0.7:  # Low confidence in local results
                return True
                
            # Use LLM to assess if local results can answer the question
            return await self._assess_local_sufficiency(question, local_results)
        
        return False
    
    async def _assess_local_sufficiency(self, question: str, local_results: List[Tuple[DocumentChunk, float]]) -> bool:
        """Use LLM to assess if local results are sufficient to answer the question"""
        
        context = "\n".join([chunk.content[:200] + "..." for chunk, _ in local_results[:3]])
        
        prompt = f"""
        Question: {question}
        
        Available context from local documents:
        {context}
        
        Based on the available context, can this question be adequately answered? 
        Consider if the context contains enough relevant information to provide a complete answer.
        
        Respond with only: SUFFICIENT or INSUFFICIENT
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use faster model for assessment
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip().upper()
            return result == "INSUFFICIENT"
        
        except Exception as e:
            print(f"Error assessing local sufficiency: {e}")
            return True  # Default to web search if assessment fails
    
    async def _web_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Perform web search using Tavily API (placeholder for now)"""
        
        # TODO: Implement actual Tavily API integration
        # For now, return mock web results
        mock_results = [
            {
                "title": f"Web Result 1 for: {query}",
                "content": f"This is a mock web search result for the query: {query}. In a real implementation, this would come from Tavily API.",
                "url": "https://example.com/result1",
                "published_date": datetime.utcnow().isoformat(),
                "source": "web_search"
            },
            {
                "title": f"Web Result 2 for: {query}",
                "content": f"Another mock result with current information about: {query}. This demonstrates web search integration.",
                "url": "https://example.com/result2", 
                "published_date": datetime.utcnow().isoformat(),
                "source": "web_search"
            }
        ]
        
        return mock_results[:max_results]
    
    def _combine_context(self, local_results: List[Tuple[DocumentChunk, float]], 
                        web_results: List[Dict]) -> str:
        """Combine local and web results into a single context"""
        
        context_parts = []
        
        # Add local document context
        if local_results:
            context_parts.append("=== INTERNAL DOCUMENTS ===")
            for chunk, similarity in local_results:
                context_parts.append(f"Document: {getattr(chunk, 'document_title', 'Unknown')}")
                context_parts.append(f"Similarity: {similarity:.3f}")
                context_parts.append(f"Content: {chunk.content[:500]}...")
                context_parts.append("---")
        
        # Add web search context
        if web_results:
            context_parts.append("\n=== WEB SEARCH RESULTS ===")
            for result in web_results:
                context_parts.append(f"Title: {result['title']}")
                context_parts.append(f"URL: {result['url']}")
                context_parts.append(f"Content: {result['content']}")
                context_parts.append("---")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str, reasoning_steps: List[Dict]) -> str:
        """Generate final answer using OpenAI GPT-4o"""
        
        prompt = f"""You are an intelligent research assistant with access to both internal documents and live web information.

Question: {question}

Available Context:
{context}

Instructions:
1. Provide a comprehensive answer based on the available context
2. Clearly distinguish between information from internal documents vs web sources
3. If information is missing or uncertain, acknowledge this
4. Cite sources appropriately (use "according to [document name]" or "based on web search")
5. Be concise but thorough

Answer:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"I apologize, but I encountered an error generating the response: {str(e)}"
    
    def _prepare_sources(self, local_results: List[Tuple[DocumentChunk, float]], 
                        web_results: List[Dict]) -> List[Dict]:
        """Prepare source citations for the response"""
        
        sources = []
        
        # Add local document sources
        for chunk, similarity in local_results:
            sources.append({
                "type": "document",
                "title": getattr(chunk, 'document_title', 'Unknown Document'),
                "filename": getattr(chunk, 'document_filename', 'Unknown File'),
                "page_range": f"{chunk.start_page}-{chunk.end_page}" if chunk.start_page else "Unknown",
                "similarity_score": similarity,
                "chunk_id": chunk.id
            })
        
        # Add web sources
        for result in web_results:
            sources.append({
                "type": "web",
                "title": result['title'],
                "url": result['url'],
                "published_date": result.get('published_date'),
                "source": "Live Web Search"
            })
        
        return sources
    
    def _avg_similarity(self, results: List[Tuple[DocumentChunk, float]]) -> float:
        """Calculate average similarity score"""
        if not results:
            return 0.0
        return sum(similarity for _, similarity in results) / len(results)
    
    def _calculate_confidence(self, local_results: List[Tuple[DocumentChunk, float]], 
                            web_results: List[Dict]) -> float:
        """Calculate confidence score for the response"""
        
        base_confidence = 0.5
        
        # Boost confidence based on local results
        if local_results:
            avg_similarity = self._avg_similarity(local_results)
            base_confidence += avg_similarity * 0.3
        
        # Boost confidence if we have web results
        if web_results:
            base_confidence += 0.2
        
        # Boost confidence based on quantity of results
        total_results = len(local_results) + len(web_results)
        base_confidence += min(total_results * 0.05, 0.2)
        
        return min(base_confidence, 1.0)
    
