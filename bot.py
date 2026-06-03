import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv()

from scraper import scrape_article
from tagger import analyze_article
from notion_client_wrapper import save_article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_urls(text: str) -> list[str]:
    return [word for word in text.split() if word.startswith("http")]


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "Send me a link and I'll scrape, summarize, tag it, and save it to Notion!"
        )
        return

    for url in urls:
        status_msg = await update.message.reply_text(f"⏳ Processing {url[:60]}...")

        try:
            # 1. Scrape
            await status_msg.edit_text("🔍 Fetching article content...")
            article = scrape_article(url)

            if "error" in article:
                await status_msg.edit_text(f"❌ Couldn't fetch that URL:\n{article['error']}")
                continue

            if not article.get("text"):
                await status_msg.edit_text(
                    "⚠️ Fetched the page but couldn't extract readable text "
                    "(may be paywalled or JS-heavy). Saving with metadata only."
                )

            # 2. Analyze with Claude
            await status_msg.edit_text("🤖 Analyzing with Claude...")
            analysis = analyze_article(article)

            # 3. Save to Notion
            await status_msg.edit_text("📝 Saving to Notion...")
            notion_url = save_article(article, analysis)

            # 4. Reply with summary
            tags_str = " ".join(f"#{t}" for t in analysis.get("tags", []))
            ideas = analysis.get("key_ideas", [])
            ideas_str = "\n".join(f"  • {i}" for i in ideas)

            reply = (
                f"✅ *{article['title'][:100]}*\n\n"
                f"📂 *{analysis.get('category', 'Uncategorized')}*\n"
                f"{tags_str}\n\n"
                f"📄 {analysis.get('summary', '')}\n\n"
            )
            if ideas_str:
                reply += f"💡 Key ideas:\n{ideas_str}\n\n"
            reply += f"[Open in Notion]({notion_url})"

            await status_msg.edit_text(reply, parse_mode="Markdown")

        except Exception as e:
            logger.exception(f"Error processing {url}")
            await status_msg.edit_text(f"❌ Something went wrong: {e}")


def main():
    app = ApplicationBuilder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
