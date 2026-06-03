import os
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


def save_article(article: dict, analysis: dict) -> str:
    """Save article + analysis to Notion database. Returns the Notion page URL."""

    tags = analysis.get("tags", [])
    key_ideas = analysis.get("key_ideas", [])
    summary = analysis.get("summary", "")
    category = analysis.get("category", "Uncategorized")
    title = article.get("title") or article.get("url")

    # Build key ideas as a bulleted list in the page body
    children = []
    if key_ideas:
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Key Ideas"}}]
            },
        })
        for idea in key_ideas:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": idea}}]
                },
            })

    response = notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Title": {
                "title": [{"text": {"content": title[:200]}}]
            },
            "URL": {
                "url": article.get("url")
            },
            "Summary": {
                "rich_text": [{"text": {"content": summary[:2000]}}]
            },
            "Category": {
                "select": {"name": category}
            },
            "Tags": {
                "multi_select": [{"name": tag} for tag in tags[:10]]
            },
            "Author": {
                "rich_text": [{"text": {"content": article.get("author") or ""}}]
            },
        },
        children=children,
    )

    page_id = response["id"].replace("-", "")
    return f"https://notion.so/{page_id}"
