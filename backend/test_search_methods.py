#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('.')

from app.services.web_search import WebSearchService

async def test_search_methods():
    """Test each web search method individually"""
    
    search_service = WebSearchService()
    query = "who is the president of the USA in 2025"
    
    print(f"Testing search methods for query: '{query}'")
    print(f"Tavily API Key configured: {bool(search_service.tavily_api_key)}")
    print(f"SerpAPI Key configured: {bool(search_service.serpapi_key)}")
    print("=" * 60)
    
    # Test DuckDuckGo
    print("\n1. Testing DuckDuckGo Search:")
    try:
        results = await search_service._duckduckgo_search(query, 3)
        print(f"   Results: {len(results)}")
        for i, result in enumerate(results[:2], 1):
            print(f"   {i}. {result.title}")
            print(f"      URL: {result.url}")
            print(f"      Content: {result.content[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test GPT-4o fallback
    print("\n2. Testing GPT-4o Web Search:")
    try:
        results = await search_service._gpt4o_web_search(query, 3)
        print(f"   Results: {len(results)}")
        for i, result in enumerate(results[:2], 1):
            print(f"   {i}. {result.title}")
            print(f"      URL: {result.url}")
            print(f"      Content: {result.content[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test overall search (which method gets used)
    print("\n3. Testing Overall Search (which method is actually used):")
    try:
        results = await search_service.search(query, 3)
        print(f"   Results: {len(results)}")
        for i, result in enumerate(results[:2], 1):
            print(f"   {i}. {result.title}")
            print(f"      URL: {result.url}")
            print(f"      Content: {result.content[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_methods())