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


def scrape_twitter(url: str) -> dict:
    """Use fxtwitter's JSON API to extract tweet content."""
    # Extract path: /username/status/id
    parsed = urlparse(url)
    path = parsed.path  # e.g. /JayaGup10/status/2039737982576636294

    api_url = f"https://api.fxtwitter.com{path}"
    try:
        resp = httpx.get(api_url, headers=HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Twitter fetch failed: {e}", "url": url}

    tweet = data.get("tweet", {})
    author = tweet.get("author", {})
    text = tweet.get("text", "")
    quote = tweet.get("quote", {})

    # Include quoted tweet text if present
    if quote.get("text"):
        text += f"\n\n[Quoting @{quote.get('author', {}).get('screen_name', '')}: {quote.get('text', '')}]"

    author_name = author.get("name", "")
    screen_name = author.get("screen_name", "")
    title = f"Tweet by {author_name} (@{screen_name})" if author_name else f"Tweet: {url}"

    # If tweet is just a bare link, follow it and scrape the destination instead
    if not text:
        raw_text = tweet.get("raw_text", {}).get("text", "")
        tco_match = re.search(r"https://t\.co/\S+", raw_text)
        if tco_match:
            try:
                redirect = httpx.get(tco_match.group(0), headers=HEADERS, timeout=10, follow_redirects=True)
                destination_url = str(redirect.url)
                destination = scrape_via_jina(destination_url)
                destination["url"] = url  # keep original tweet URL for Notion
                destination["author"] = f"{author_name} (@{screen_name})"
                if destination.get("text"):
                    return destination
            except Exception:
                pass
        text = f"[Tweet contained no text — may be image/video only. URL: {url}]"

    return {
        "url": url,
        "title": title,
        "author": f"{author_name} (@{screen_name})",
        "description": None,
        "text": text[:8000],
    }


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
        return scrape_twitter(url)

    result = scrape_via_jina(url)

    # Fallback: if Jina fails, return minimal info so Claude can still tag by URL
    if result.get("error") or not result.get("text"):
        result["text"] = result.get("description") or f"Could not extract content from: {url}"

    return result
