"""
Multi-Source Web Search - Aggregates results from multiple search providers
Providers: Tavily, DuckDuckGo, SerpAPI, NewsAPI
Gracefully degrades when API keys are missing
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


@dataclass
class SearchResult:
    source: str
    title: str
    url: str
    snippet: str
    relevance_score: float = 1.0


class MultiSourceSearch:
    """
    Intelligent web search that pulls from multiple sources.
    Each source has a 'confidence' score based on reliability.
    Results are ranked and deduplicated.
    """

    def __init__(self):
        self._initialize_providers()

    def _initialize_providers(self):
        self.providers = {}

        tavily_key = settings.TAVILY_API_KEY
        if tavily_key:
            try:
                from tavily import TavilyClient

                self.providers["tavily"] = {
                    "client": TavilyClient(api_key=tavily_key),
                    "weight": 0.9,
                    "type": "news_search",
                }
                logger.info({"event": "tavily_initialized"})
            except Exception as e:
                logger.warning({"event": "tavily_init_failed", "error": str(e)})

        newsapi_key = settings.NEWS_API_KEY
        if newsapi_key:
            try:
                from newsapi import NewsApiClient

                self.providers["newsapi"] = {
                    "client": NewsApiClient(api_key=newsapi_key),
                    "weight": 0.8,
                    "type": "news",
                }
                logger.info({"event": "newsapi_initialized"})
            except Exception as e:
                logger.warning({"event": "newsapi_init_failed", "error": str(e)})

        serpapi_key = settings.SERPAPI_KEY
        if serpapi_key:
            self.providers["serpapi"] = {
                "api_key": serpapi_key,
                "weight": 0.7,
                "type": "general",
            }
            logger.info({"event": "serpapi_initialized"})

        self.providers["duckduckgo"] = {"weight": 0.5, "type": "general"}
        logger.info(
            {
                "event": "multi_source_search_initialized",
                "providers": list(self.providers.keys()),
            }
        )

    async def search(
        self,
        query: str,
        max_results_per_source: int = 5,
        include_answer: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search across all available providers and aggregate results.
        Returns deduplicated, ranked results.
        """
        legacy_max_results = kwargs.pop("max_results", None)
        if legacy_max_results is not None:
            max_results_per_source = legacy_max_results

        tasks = []

        if "tavily" in self.providers:
            tasks.append(
                self._search_tavily(query, max_results_per_source, include_answer)
            )
        if "newsapi" in self.providers:
            tasks.append(self._search_newsapi(query, max_results_per_source))
        if "serpapi" in self.providers:
            tasks.append(self._search_serpapi(query, max_results_per_source))
        if "duckduckgo" in self.providers:
            tasks.append(self._search_duckduckgo(query, max_results_per_source))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        aggregated = {"results": [], "answers": [], "sources": [], "error": None}

        seen_urls = set()

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue

            if result and result.get("results"):
                for item in result["results"]:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        item["provider"] = (
                            list(self.providers.keys())[i]
                            if i < len(self.providers)
                            else "unknown"
                        )
                        aggregated["results"].append(item)

            if result and result.get("answer"):
                aggregated["answers"].append(result["answer"])

            if result and result.get("sources"):
                aggregated["sources"].extend(result["sources"])

        aggregated["results"].sort(
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )

        if aggregated["answers"]:
            aggregated["synthesized_answer"] = self._synthesize_answers(
                aggregated["answers"]
            )

        return aggregated

    async def _search_tavily(
        self, query: str, max_results: int, include_answer: bool
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.providers["tavily"]["client"].search(
                    query=f"{query} India business 2026",
                    search_depth="advanced",
                    max_results=max_results,
                    include_answer=include_answer,
                    include_raw_content=False,
                ),
            )

            return {
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", ""),
                        "relevance_score": r.get("score", 0.5)
                        * self.providers["tavily"]["weight"],
                    }
                    for r in result.get("results", [])[:max_results]
                ],
                "answer": result.get("answer") if include_answer else None,
                "sources": [
                    r.get("url", "") for r in result.get("results", [])[:max_results]
                ],
            }
        except Exception as e:
            logger.error({"event": "tavily_search_error", "error": str(e)})
            return {}

    async def _search_newsapi(self, query: str, max_results: int) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self.providers["newsapi"]["client"].get_everything(
                    q=query, language="en", sort_by="relevancy", page_size=max_results
                ),
            )

            articles = result.get("articles", [])[:max_results]
            return {
                "results": [
                    {
                        "title": a.get("title", ""),
                        "url": a.get("url", ""),
                        "snippet": a.get("description", ""),
                        "relevance_score": 0.6 * self.providers["newsapi"]["weight"],
                        "published_at": a.get("publishedAt", ""),
                    }
                    for a in articles
                    if a.get("title")
                ],
                "sources": [a.get("url", "") for a in articles],
            }
        except Exception as e:
            logger.error({"event": "newsapi_search_error", "error": str(e)})
            return {}

    async def _search_serpapi(self, query: str, max_results: int) -> Dict[str, Any]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.providers["serpapi"]["api_key"],
                        "num": max_results,
                        "engine": "google",
                    },
                )
                data = resp.json()

                results = data.get("organic_results", [])[:max_results]
                return {
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("link", ""),
                            "snippet": r.get("snippet", ""),
                            "relevance_score": 0.5
                            * self.providers["serpapi"]["weight"],
                        }
                        for r in results
                    ],
                    "sources": [r.get("link", "") for r in results],
                }
        except Exception as e:
            logger.error({"event": "serpapi_search_error", "error": str(e)})
            return {}

    async def _search_duckduckgo(self, query: str, max_results: int) -> Dict[str, Any]:
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(f"{query} India", max_results=max_results))

            return {
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "relevance_score": 0.4 * self.providers["duckduckgo"]["weight"],
                    }
                    for r in results
                    if r.get("title")
                ],
                "sources": [r.get("href", "") for r in results if r.get("href")],
            }
        except ImportError:
            logger.warning({"event": "duckduckgo_not_installed"})
            return {}
        except Exception as e:
            logger.error({"event": "duckduckgo_search_error", "error": str(e)})
            return {}

    def _synthesize_answers(self, answers: List[str]) -> str:
        if not answers:
            return ""
        if len(answers) == 1:
            return answers[0]
        return " | ".join(answers[:3])


multi_source_search = MultiSourceSearch()
