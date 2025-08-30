#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from services.web_search import WebSearchService

async def test_web_search():
    """Test the web search functionality"""
    search_service = WebSearchService()
    
    test_queries = [
        "who is the president of the USA in 2025",
        "Joe Biden president 2025",
        "Donald Trump election results 2024"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing query: {query}")
        print(f"{'='*50}")
        
        try:
            results = await search_service.search(query, max_results=3)
            
            if not results:
                print("No results returned")
                continue
                
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"Title: {result.title}")
                print(f"URL: {result.url}")
                print(f"Content: {result.content[:200]}...")
                print(f"Score: {result.score}")
                print("-" * 40)
                
        except Exception as e:
            print(f"Error searching for '{query}': {e}")

if __name__ == "__main__":
    asyncio.run(test_web_search())