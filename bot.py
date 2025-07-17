# bot.py ────────────────────────────────────────────────────────────────
"""Discord bot that announces news headlines in a voice channel."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime, timezone
from multiprocessing.connection import Listener

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN,
    GUILD_ID,
    VOICE_CHANNEL_ID,
    TEXT_CHANNEL_ID,
    QUEUE_SOCK,          # add to .env → QUEUE_SOCK=/tmp/squawk.sock  (or leave unset for default)
)
from news_fetcher import fetch_news_loop
from tts import synthesize

# ────────────────── discord setup ──────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
news_queue: asyncio.Queue = asyncio.Queue()


# ────────────────── helper functions ───────────────────────────────────
def spell(word: str) -> str:
    """Spell tickers (NVDA ➜ N‑V‑D‑A)."""
    if word.isalpha() and word.isupper() and len(word) <= 5:
        return "-".join(word)
    return word


def to_ssml(title: str) -> str:
    words = [spell(w) for w in title.split()]
    return f"<speak>{' '.join(words)}</speak>"


async def connect_voice() -> discord.VoiceProtocol | None:
    """Join (or retrieve) the configured voice channel and ensure we can speak."""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return None
    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        return None

    try:
        vc: discord.VoiceProtocol = await channel.connect()
    except discord.ClientException:
        vc = discord.utils.get(bot.voice_clients, guild=guild)

    if not vc:
        return None

    # Allow speaking even in Stage channels
    try:
        await vc.guild.change_voice_state(channel=vc.channel, suppressed=False)
    except (discord.HTTPException, AttributeError):
        pass
    return vc


# ────────────────── background socket to enqueue headlines ─────────────
def _queue_socket_listener(q: asyncio.Queue):
    """Local UNIX socket listener – lets docker exec enqueue headlines without re‑importing bot.py."""
    socket_path = QUEUE_SOCK or "/tmp/squawk.sock"
    if os.path.exists(socket_path):
        os.remove(socket_path)
    listener = Listener(socket_path)  # multiprocessing.connection.Listener (AF_UNIX)

    print(f"[helper‑sock] listening on {socket_path!s}")
    while True:
        try:
            conn = listener.accept()
            title = conn.recv()        # we expect a simple str
            asyncio.run_coroutine_threadsafe(
                q.put({"title": title}),
                bot.loop,
            )
            conn.close()
        except Exception as e:
            print("[helper‑sock] error:", e)


threading.Thread(
    target=_queue_socket_listener,
    args=(news_queue,),
    daemon=True,
).start()


# ────────────────── discord events ─────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await connect_voice()
    bot.loop.create_task(fetch_news_loop(news_queue))
    bot.loop.create_task(consume_news())


@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    """Kick listeners without the News‑Pro role."""
    if member.bot:
        return
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if after.channel == channel and not any(r.name == "News-Pro" for r in member.roles):
        try:
            await member.move_to(None)
            await member.send("Subscribe here → https://buy.newspro.link")
        except discord.Forbidden:
            pass


# ────────────────── headline consumer ──────────────────────────────────
async def consume_news():
    text_chan = bot.get_channel(TEXT_CHANNEL_ID)
    while True:
        item = await news_queue.get()

        # ----- embed ----------------------------------------------------
        title = item["title"]
        url = item.get("url")
        pub_str = item.get("published") or ""
        try:
            ts = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)

        if isinstance(text_chan, discord.TextChannel):
            embed = discord.Embed(title=title, url=url, timestamp=ts)
            embed.set_footer(text="NewsAPI.org")
            await text_chan.send(embed=embed)

        # ----- TTS ------------------------------------------------------
        ssml = to_ssml(title)
        path = await bot.loop.run_in_executor(None, synthesize, ssml)

        voice = discord.utils.get(bot.voice_clients, guild=bot.get_guild(GUILD_ID))
        if not voice or not voice.is_connected():
            voice = await connect_voice()

        if voice and not voice.is_playing():
            audio = discord.FFmpegPCMAudio(path)

            def _cleanup(_):
                try:
                    os.remove(path)
                except OSError:
                    pass

            voice.play(audio, after=_cleanup)
        else:
            os.remove(path)


# ────────────────── simple slash‑command ‐ ping ------------------------
@bot.tree.command(name="ping", description="Check bot responsiveness")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


# ────────────────── bot entry‑point ────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
