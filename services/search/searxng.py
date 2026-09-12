import httpx
import logging
from config.settings import settings

logger = logging.getLogger("search_assistant")

class SearXNGClient:
    def __init__(self):
        self.url = settings.SEARXNG_URL
        self.headers = {
            "User-Agent": "Mozilla/5.5 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    async def fetch_results(self, query: str, retry_count: int) -> str:
        """Executes resilient query fallback tactics based on graph cycle counts."""
        # Dynamic engine adjustment parameters
        engine_selection = "google,bing,duckduckgo,brave,wikipedia"
        if retry_count > 0:
            engine_selection = "wikipedia,duckduckgo,brave"
            logger.info(f"   [Search Strategy] Dynamic routing pivot applied: {engine_selection}")

        params = {
            "q": query,
            "format": "json",
            "engines": engine_selection,
            "language": "en-US"
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(self.url, params=params, headers=self.headers, timeout=6.0)
                res.raise_for_status()
                results = res.json().get("results", [])
                
                snippets = [f"{r.get('title')} - {r.get('content')}" for r in results[:5]]
                return "\n".join(snippets)
            except Exception as e:
                logger.error(f"Network error querying SearXNG: {str(e)}")
                return ""
