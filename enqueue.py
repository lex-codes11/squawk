# enqueue.py  ── helper so we don't re‑import bot.py!
import asyncio, sys, pickle, os
from multiprocessing.connection import Client

def main(title: str):
    addr = os.environ.get("QUEUE_SOCK", "/tmp/squawk.sock")
    with Client(addr) as conn:
        conn.send(title)

if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or "Test headline from helper")
