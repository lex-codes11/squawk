# news_fetcher.py
"""Poll NewsAPI every POLL_SEC seconds and push new headlines into a queue."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Set

from aiohttp import ClientSession, ClientTimeout
from config import NEWSAPI_KEY, POLL_SEC

NEWS_ENDPOINT = (
    "https://newsapi.org/v2/top-headlines?country=us&category=business&pageSize=10"
)


async def fetch_news_loop(queue: asyncio.Queue):
    """Continuously fetch headlines and put unseen ones into the queue."""
    seen: Set[str] = set()
    timeout = ClientTimeout(total=10)

    async with ClientSession(timeout=timeout) as session:
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
