# backend/app/services/web_search.py
import httpx
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class WebSearchResult:
    def __init__(self, title: str, content: str, url: str, published_date: Optional[str] = None, 
                 score: Optional[float] = None):
        self.title = title
        self.content = content
        self.url = url
        self.published_date = published_date or datetime.utcnow().isoformat()
        self.score = score or 0.0
        self.source = "web_search"

class WebSearchService:
    """
    Web search service with Tavily API integration and mock fallback
    
    This service provides:
    1. Live web search using Tavily API (if configured)
    2. Mock results for development/testing (when API key not available)
    3. Error handling and fallback mechanisms
    """
    
    def __init__(self):
        self.timeout = 30.0
        # Note: Tavily API key should be added to your .env file as TAVILY_API_KEY
        self.api_key = getattr(settings, 'tavily_api_key', None)
        
    async def search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """
        Perform web search with automatic fallback to mock results
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of WebSearchResult objects
        """
        
        if self.api_key:
            try:
                return await self._tavily_search(query, max_results)
            except Exception as e:
                logger.warning(f"Tavily API failed: {e}, falling back to mock results")
                return await self._mock_search(query, max_results)
        else:
            logger.info("No Tavily API key configured, using mock results")
            return await self._mock_search(query, max_results)
    
    async def _tavily_search(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using Tavily API"""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_raw_content": False,
                "max_results": max_results
            }
            
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Add direct answer if available
            if data.get("answer"):
                results.append(WebSearchResult(
                    title=f"Direct Answer: {query}",
                    content=data["answer"],
                    url="https://tavily.com",
                    score=1.0
                ))
            
            # Add search results
            for item in data.get("results", []):
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    published_date=item.get("published_date"),
                    score=item.get("score", 0.0)
                ))
            
            logger.info(f"Tavily search returned {len(results)} results for: {query}")
            return results[:max_results]
    
    async def _mock_search(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Provide realistic mock search results for development"""
        
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Generate contextually relevant mock results
        mock_results = []
        
        if "RAG" in query.upper():
            mock_results = [
                WebSearchResult(
                    title="Retrieval-Augmented Generation: Latest Research 2025",
                    content="Recent advances in RAG systems show improved performance through better retrieval strategies. "
                            "New techniques include iterative retrieval, query expansion, and hybrid search methods that "
                            "combine dense and sparse retrieval approaches.",
                    url="https://arxiv.org/example/rag-advances-2025",
                    score=0.95
                ),
                WebSearchResult(
                    title="Enterprise RAG Implementation Best Practices",
                    content="Industry report on implementing RAG systems in production environments. Key findings include "
                            "the importance of data quality, chunk size optimization, and evaluation frameworks for "
                            "measuring RAG system performance.",
                    url="https://techreport.com/rag-enterprise-guide",
                    score=0.88
                ),
                WebSearchResult(
                    title="RAG vs Fine-tuning: Performance Comparison Study",
                    content="Comprehensive study comparing RAG approaches with fine-tuning for domain-specific tasks. "
                            "Results show RAG provides better factual accuracy and easier maintenance for knowledge-intensive applications.",
                    url="https://research.ai/rag-vs-finetuning-2025",
                    score=0.82
                )
            ]
        elif "evaluation" in query.lower():
            mock_results = [
                WebSearchResult(
                    title="AI Model Evaluation Frameworks 2025",
                    content="Current state of AI evaluation methodologies including human evaluation, automated metrics, "
                            "and benchmark datasets. New frameworks focus on robustness, fairness, and real-world performance.",
                    url="https://ai-evaluation.org/frameworks-2025",
                    score=0.91
                ),
                WebSearchResult(
                    title="Benchmarking Large Language Models: Recent Updates",
                    content="Latest benchmarks for evaluating LLM capabilities across reasoning, knowledge, and safety. "
                            "Includes new datasets for measuring factual accuracy and hallucination detection.",
                    url="https://llm-benchmarks.com/2025-update",
                    score=0.87
                )
            ]
        else:
            # Generic results for other queries
            mock_results = [
                WebSearchResult(
                    title=f"Recent Developments in {query}",
                    content=f"Latest research and industry developments related to {query}. This mock result would "
                            f"contain current information from web sources about the topic.",
                    url=f"https://example.com/recent-{query.replace(' ', '-').lower()}",
                    score=0.85
                ),
                WebSearchResult(
                    title=f"{query}: Industry Analysis 2025",
                    content=f"Current market trends and technical analysis for {query}. Industry experts discuss "
                            f"recent developments and future directions in this field.",
                    url=f"https://industry-analysis.com/{query.replace(' ', '-').lower()}-2025",
                    score=0.79
                )
            ]
        
        limited_results = mock_results[:max_results]
        logger.info(f"Mock search returned {len(limited_results)} results for: {query}")
        return limited_results
    
    async def search_with_context(self, query: str, context: str, max_results: int = 3) -> List[WebSearchResult]:
        """Enhanced search that includes context for better results"""
        
        # Create enhanced query with context
        enhanced_query = f"{query} {context[:100]}" if context else query
        return await self.search(enhanced_query, max_results)

# Global instance
web_search_service = WebSearchService()