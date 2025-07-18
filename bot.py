"""Discord bot that announces news headlines in a voice channel."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from multiprocessing.connection import Listener

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN,
    GUILD_ID,
    VOICE_CHANNEL_ID,
    TEXT_CHANNEL_ID,
    QUEUE_SOCK,
)
from news_fetcher import fetch_news_loop
from tts import synthesize

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
news_queue: asyncio.Queue = asyncio.Queue()


# ───────────────────────── helpers ──────────────────────────
def spell(word: str) -> str:
    """Spell tickers (NVDA → N‑V‑D‑A)."""
    if word.isalpha() and word.isupper() and len(word) <= 5:
        return "-".join(word)
    return word


def to_ssml(title: str) -> str:
    words = [spell(w) for w in title.split()]
    return f"<speak>{' '.join(words)}</speak>"


async def connect_voice() -> discord.VoiceProtocol | None:
    """Ensure the bot is connected and unsuppressed in the target channel."""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return None

    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
        return None

    # Connect (or re‑use existing)
    try:
        vc: discord.VoiceProtocol = await channel.connect()
    except discord.ClientException:
        vc = discord.utils.get(bot.voice_clients, guild=guild)

    if not vc:
        return None

    # Unsuppress so audio is audible (works for Stage & Voice)
    try:
        await vc.guild.change_voice_state(channel=vc.channel, suppress=False)
    except discord.HTTPException:
        pass
    return vc


# ───────────────────────── events ───────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await connect_voice()

    # start background jobs
    bot.loop.create_task(fetch_news_loop(news_queue))
    bot.loop.create_task(consume_news())
    bot.loop.create_task(listen_local_socket())  # for enqueue.py helper


@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    """Boot listeners without the News‑Pro role."""
    if member.bot:
        return

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if after.channel == channel and not any(r.name == "News-Pro" for r in member.roles):
        try:
            await member.move_to(None)
            await member.send("Subscribe here → https://buy.newspro.link")
        except discord.Forbidden:
            pass


# ─────────────────── background tasks ───────────────────────
async def consume_news():
    text_chan = bot.get_channel(TEXT_CHANNEL_ID)

    while True:
        item = await news_queue.get()
        title = item["title"]
        url = item.get("url")
        pub_str = item.get("published") or ""

        # embed
        try:
            ts = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)

        if isinstance(text_chan, discord.TextChannel):
            embed = discord.Embed(title=title, url=url, timestamp=ts)
            embed.set_footer(text="NewsAPI.org")
            await text_chan.send(embed=embed)

        # voice
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


async def listen_local_socket():
    """Allow `enqueue.py "headline"` to inject items without restarting."""
    loop = asyncio.get_running_loop()

    if os.path.exists(QUEUE_SOCK):
        os.remove(QUEUE_SOCK)

    listener = Listener(QUEUE_SOCK)
    listener._listener.setblocking(False)  # type: ignore

    while True:
        try:
            conn = await loop.run_in_executor(None, listener.accept)
            msg = await loop.run_in_executor(None, conn.recv)
            await news_queue.put({"title": str(msg)})
            conn.close()
        except Exception:
            await asyncio.sleep(0.5)


# ──────────────────── slash command ─────────────────────────
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


bot.run(DISCORD_TOKEN)
