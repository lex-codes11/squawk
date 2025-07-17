"""Poll NewsAPI every POLL_SEC seconds and push new headlines into a queue."""

import asyncio
import hashlib
import http.client
from aiohttp import ClientSession
from config import NEWSAPI_KEY, POLL_SEC

NEWS_ENDPOINT = (
    "https://newsapi.org/v2/top-headlines?country=us&category=business&pageSize=10"
)


async def fetch_news_loop(queue: asyncio.Queue):
    seen: set[str] = set()

    async with ClientSession(timeout=http.client.Timeout(total=10)) as session:
        while True:
            try:
                headers = {"X-Api-Key": NEWSAPI_KEY}
                async with session.get(NEWS_ENDPOINT, headers=headers) as resp:
                    data = await resp.json()
                    for article in data.get("articles", []):
                        title = article["title"]
                        uid = hashlib.sha256(title.encode()).hexdigest()
                        if uid in seen:
                            continue
                        seen.add(uid)
                        await queue.put(
                            {
                                "title": title,
                                "url": article.get("url"),
                                "published": article.get("publishedAt"),
                            }
                        )
            except Exception as e:
                print("News fetch error:", e)

            await asyncio.sleep(POLL_SEC)
