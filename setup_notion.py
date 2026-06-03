"""
Run once to add the required properties to your Notion database.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


def setup():
    print("Updating Notion database schema...")
    notion.databases.update(
        database_id=DATABASE_ID,
        properties={
            "URL": {"url": {}},
            "Summary": {"rich_text": {}},
            "Category": {"select": {}},
            "Tags": {"multi_select": {}},
            "Author": {"rich_text": {}},
        },
    )
    print("Done! Your Notion database is ready.")


if __name__ == "__main__":
    setup()
