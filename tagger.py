import os
import json
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a research assistant that categorizes articles and extracts key insights.
Given an article's title, description, and body text, return a JSON object with:
- summary: 2-3 sentence plain English summary of the article
- category: one top-level category (e.g. "AI & Technology", "Finance & Markets", "Politics", "Health & Science", "Business & Startups", "Philosophy & Ideas", "Culture & Society", "Crypto & Web3", "Career & Productivity")
- tags: list of 3-6 specific topic tags (lowercase, e.g. ["llms", "regulation", "open source"])
- key_ideas: list of 2-4 short bullet point strings capturing the main takeaways

Return only valid JSON, no markdown fences."""


def analyze_article(article: dict) -> dict:
    """Send article to Claude for summarization and tagging."""
    content = f"""Title: {article.get('title', 'Unknown')}
Author: {article.get('author', 'Unknown')}
URL: {article.get('url', '')}

Body:
{article.get('text', '')[:6000]}"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if Claude adds them anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "summary": raw[:500],
            "category": "Uncategorized",
            "tags": [],
            "key_ideas": [],
        }

    return result
