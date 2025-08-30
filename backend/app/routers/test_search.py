from fastapi import APIRouter
from app.services.web_search import web_search_service
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["test"])

@router.get("/env-debug")
async def debug_environment():
    """Debug endpoint to check environment variables"""
    return {
        "travily_from_env": os.getenv("TRAVILY_API_KEY") is not None,
        "travily_from_env_value": os.getenv("TRAVILY_API_KEY", "NOT_SET")[:10] + "..." if os.getenv("TRAVILY_API_KEY") else "NOT_SET",
        "travily_from_settings": bool(settings.tavily_api_key),
        "travily_from_settings_value": settings.tavily_api_key[:10] + "..." if settings.tavily_api_key else "NOT_SET",
        "all_env_keys_with_travily": [key for key in os.environ.keys() if "TRAVILY" in key.upper() or "TAVILY" in key.upper()]
    }

@router.get("/search-methods")
async def test_search_methods():
    """Test which search methods are actually working"""
    
    query = "who is the president of the USA in 2025"
    results = {
        "query": query,
        "tavily_configured": bool(web_search_service.tavily_api_key),
        "serpapi_configured": bool(web_search_service.serpapi_key),
        "methods_tested": {}
    }
    
    # Test DuckDuckGo
    try:
        logger.info("Testing DuckDuckGo search")
        duckduckgo_results = await web_search_service._duckduckgo_search(query, 2)
        results["methods_tested"]["duckduckgo"] = {
            "success": True,
            "result_count": len(duckduckgo_results),
            "sample_result": {
                "title": duckduckgo_results[0].title if duckduckgo_results else None,
                "url": duckduckgo_results[0].url if duckduckgo_results else None,
                "score": duckduckgo_results[0].score if duckduckgo_results else None
            } if duckduckgo_results else None
        }
    except Exception as e:
        results["methods_tested"]["duckduckgo"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test GPT-4o
    try:
        logger.info("Testing GPT-4o search")
        gpt_results = await web_search_service._gpt4o_web_search(query, 2)
        results["methods_tested"]["gpt4o"] = {
            "success": True,
            "result_count": len(gpt_results),
            "sample_result": {
                "title": gpt_results[0].title if gpt_results else None,
                "url": gpt_results[0].url if gpt_results else None,
                "score": gpt_results[0].score if gpt_results else None
            } if gpt_results else None
        }
    except Exception as e:
        results["methods_tested"]["gpt4o"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test overall search (to see which method is actually used)
    try:
        logger.info("Testing overall search method selection")
        overall_results = await web_search_service.search(query, 2)
        results["overall_search"] = {
            "success": True,
            "result_count": len(overall_results),
            "sample_result": {
                "title": overall_results[0].title if overall_results else None,
                "url": overall_results[0].url if overall_results else None,
                "score": overall_results[0].score if overall_results else None
            } if overall_results else None
        }
    except Exception as e:
        results["overall_search"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test Tavily API directly with hardcoded key for verification
    try:
        logger.info("Testing Tavily API directly")
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "api_key": "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",
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "include_raw_content": False,
                "max_results": 2
            }
            
            response = await client.post(
                "https://api.tavily.com/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                tavily_results = data.get("results", [])
                results["methods_tested"]["tavily_direct"] = {
                    "success": True,
                    "result_count": len(tavily_results),
                    "answer": data.get("answer", ""),
                    "sample_result": {
                        "title": tavily_results[0].get("title", "") if tavily_results else None,
                        "url": tavily_results[0].get("url", "") if tavily_results else None,
                        "content": tavily_results[0].get("content", "")[:100] + "..." if tavily_results else None
                    } if tavily_results else None
                }
            else:
                results["methods_tested"]["tavily_direct"] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
    except Exception as e:
        results["methods_tested"]["tavily_direct"] = {
            "success": False,
            "error": str(e)
        }
    
    return results