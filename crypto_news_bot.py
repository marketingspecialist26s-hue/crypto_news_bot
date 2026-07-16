import os
import json
import time
import threading
import requests
import feedparser
from flask import Flask

# ==========================
# CONFIG
# ==========================
BOT_TOKEN = os.environ.get("8756908212:AAFxcIAxNyvAL_AD_FEegKW4iHJKGJsGRiE", "")
CHAT_ID = os.environ.get("8930580236", "")

CHECK_INTERVAL_SECONDS = 15 * 60  # 15 minutes

SEEN_FILE = "seen_news.json"

# Free RSS feeds - koi API key nahi chahiye
RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
}

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN environment variable not found.")
if not CHAT_ID:
    raise Exception("CHAT_ID environment variable not found.")

# ==========================
# Flask App (Render ko ek open port chahiye taaki service "live" mane)
# ==========================
app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Crypto News Alert Bot is running."


# ==========================
# Functions
# ==========================
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()


def save_seen(seen):
    # Bahut purane entries trim karo taaki file zyada bada na ho
    seen_list = list(seen)
    if len(seen_list) > 3000:
        seen_list = seen_list[-3000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_list, f)


def send_telegram_alert(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, data=payload, timeout=20)
        if r.status_code == 200:
            print("Telegram Alert Sent")
        else:
            print(r.text)
    except Exception as e:
        print(e)


def fetch_feed(source_name, feed_url):
    try:
        feed = feedparser.parse(feed_url)
        return feed.entries
    except Exception as e:
        print(f"Feed error ({source_name}):", e)
        return []


def format_alert(source_name, entry):
    title = entry.get("title", "No title")
    link = entry.get("link", "")
    published = entry.get("published", "")

    return f"""
📰 <b>{source_name}</b>
{title}

🕒 {published}
🔗 {link}
"""


def news_loop():
    print("Crypto News Bot Started...")
    seen = load_seen()

    while True:
        try:
            new_count = 0

            for source_name, feed_url in RSS_FEEDS.items():
                entries = fetch_feed(source_name, feed_url)

                for entry in entries:
                    link = entry.get("link", "")
                    if not link:
                        continue

                    key = f"{source_name}:{link}"
                    if key in seen:
                        continue

                    seen.add(key)
                    send_telegram_alert(format_alert(source_name, entry))
                    new_count += 1
                    time.sleep(1)  # Telegram rate limit se bachne ke liye

            if new_count:
                save_seen(seen)
                print(f"{new_count} new news item(s) alerted.")
            else:
                print("No new news this round.")

        except Exception as e:
            print("Loop Error:", e)

        time.sleep(CHECK_INTERVAL_SECONDS)


# ==========================
# Main
# ==========================
if __name__ == "__main__":
    threading.Thread(target=news_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
