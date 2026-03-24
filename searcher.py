from duckduckgo_search import DDGS
import time


def search_brand(brand_name: str, max_results: int = 3) -> str:
    """
    Search the web for a brand and return combined snippets.
    Used as context for LLM extraction.
    """
    try:
        query = f"{brand_name} parent company stock ticker NAICS industry"
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"{r['title']}: {r['body']}")

        if not results:
            return f"No search results found for {brand_name}."

        # Small delay to avoid rate limiting
        time.sleep(0.5)

        return "\n".join(results)

    except Exception as e:
        return f"Search failed for {brand_name}: {str(e)}"


def search_naics(brand_name: str, industry: str) -> str:
    """Search specifically for NAICS code."""
    try:
        query = f"{brand_name} {industry} NAICS code classification"
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=2):
                results.append(r['body'])

        time.sleep(0.3)
        return "\n".join(results) if results else ""

    except Exception:
        return ""