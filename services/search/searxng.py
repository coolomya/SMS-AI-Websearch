import httpx
import logging

from config.settings import settings

logger = logging.getLogger("search_assistant")


class SearXNGClient:
    def __init__(self):
        # Ensure settings.SEARXNG_URL points to the base URL
        # e.g. http://localhost:8080
        self.url = settings.SEARXNG_URL.rstrip("/")

        # SearXNG API request.
        # We don't need to spoof all Chrome navigation headers.
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        }

        # SearXNG may query multiple engines, so 6 seconds
        # is unnecessarily aggressive.
        self.timeout = httpx.Timeout(
            connect=5.0,
            read=20.0,
            write=5.0,
            pool=5.0,
        )

    async def fetch_results(self, query: str, retry_count: int) -> str:
        """
        Query SearXNG using its normal general-search configuration.

        We intentionally do NOT specify individual engines here.
        SearXNG will use the engines configured/enabled on the server.
        """

        params = {
            "q": query,
            "categories": "general",
            "language": "auto",
            "format": "json",
            "safesearch": 0,
        }

        logger.info(
            f"[SearXNG] Searching: {query!r} "
            f"(attempt {retry_count + 1})"
        )

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:

            try:
                response = await client.get(
                    f"{self.url}/search",
                    params=params,
                )

                logger.info(
                    f"[SearXNG] HTTP {response.status_code} "
                    f"URL={response.url}"
                )

                response.raise_for_status()

                data = response.json()
                results = data.get("results", [])

                logger.info(
                    f"[SearXNG] Received {len(results)} results"
                )

                # Log engine distribution for diagnostics.
                engine_counts = {}

                for result in results:
                    engine = result.get("engine", "unknown")
                    engine_counts[engine] = (
                        engine_counts.get(engine, 0) + 1
                    )

                logger.info(
                    f"[SearXNG] Engine distribution: {engine_counts}"
                )

                if not results:
                    logger.warning(
                        f"[SearXNG] No results returned for query: "
                        f"{query!r}"
                    )
                    return ""

                snippets = []

                for result in results[:5]:
                    title = result.get("title", "").strip()
                    content = result.get("content", "").strip()

                    if title or content:
                        snippets.append(
                            f"{title} - {content}"
                        )

                output = "\n".join(snippets)

                logger.info(
                    f"[SearXNG] Returning {len(snippets)} snippets"
                )

                return output

            except httpx.TimeoutException as e:
                logger.error(
                    f"[SearXNG] Request timed out for query "
                    f"{query!r}: {e}"
                )
                return ""

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"[SearXNG] HTTP error "
                    f"{e.response.status_code} for query "
                    f"{query!r}: {e}"
                )
                return ""

            except httpx.HTTPError as e:
                logger.error(
                    f"[SearXNG] Network error for query "
                    f"{query!r}: {e}"
                )
                return ""

            except ValueError as e:
                logger.error(
                    f"[SearXNG] Invalid JSON response for query "
                    f"{query!r}: {e}"
                )
                return ""

            except Exception as e:
                logger.exception(
                    f"[SearXNG] Unexpected error for query "
                    f"{query!r}: {e}"
                )
                return ""
