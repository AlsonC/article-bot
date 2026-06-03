import re
import httpx
from urllib.parse import urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "substack.com" in domain:
        return "substack"
    if "twitter.com" in domain or "x.com" in domain:
        return "twitter"
    if "linkedin.com" in domain:
        return "linkedin"
    return "generic"


def scrape_via_jina(url: str) -> dict:
    """Use Jina AI reader to extract clean text from any URL (free, no key needed)."""
    jina_url = f"https://r.jina.ai/{url}"
    try:
        resp = httpx.get(jina_url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        return {"error": f"Jina reader failed: {e}", "url": url}

    raw = resp.text

    # Parse the structured Jina markdown response
    title = None
    author = None
    text = raw

    title_match = re.search(r"^Title:\s*(.+)$", raw, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Strip the header block to get just the content
    content_match = re.search(r"Markdown Content:\s*\n(.*)", raw, re.DOTALL)
    if content_match:
        text = content_match.group(1).strip()

    return {
        "url": url,
        "title": title or url,
        "author": author,
        "description": None,
        "text": text[:8000],  # cap to avoid huge token usage
    }


def scrape_article(url: str) -> dict:
    """Main entry point — routes all URLs through Jina for clean text extraction."""
    platform = detect_platform(url)

    if platform == "twitter":
        # Route through fxtwitter.com which mirrors tweets in scrapable HTML
        fx_url = re.sub(r"https://(www\.)?(twitter\.com|x\.com)", "https://fxtwitter.com", url)
        result = scrape_via_jina(fx_url)
        result["url"] = url  # keep original URL for Notion
        if result.get("text"):
            return result
        # If fxtwitter also fails, return minimal info
        return {
            "url": url,
            "title": f"Tweet: {url}",
            "author": None,
            "description": None,
            "text": f"[Twitter/X post — content could not be extracted. URL: {url}]",
        }

    result = scrape_via_jina(url)

    # Fallback: if Jina fails, return minimal info so Claude can still tag by URL
    if result.get("error") or not result.get("text"):
        result["text"] = result.get("description") or f"Could not extract content from: {url}"

    return result
