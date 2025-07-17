# bot.py
"""Discord bot that announces news headlines in a voice channel."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN,
    GUILD_ID,
    VOICE_CHANNEL_ID,
    TEXT_CHANNEL_ID,
)
from news_fetcher import fetch_news_loop
from tts import synthesize

# --------------------------------------------------------------------------- #
#  Discord setup
# --------------------------------------------------------------------------- #
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
news_queue: asyncio.Queue = asyncio.Queue()


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def spell(word: str) -> str:
    """Spell stock tickers (e.g. NVDA → N‑V‑D‑A) for clearer TTS."""
    if word.isalpha() and word.isupper() and len(word) <= 5:
        return "-".join(word)
    return word


def to_ssml(title: str) -> str:
    words = [spell(w) for w in title.split()]
    return f"<speak>{' '.join(words)}</speak>"


async def connect_voice() -> discord.VoiceProtocol | None:
    """Join the configured voice/stage channel and unsuppress the bot."""
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

    # Ensure the bot is unsuppressed (works for both Voice & Stage)
    try:
        await vc.channel.edit(suppress=False)
    except discord.HTTPException:
        pass

    return vc


# --------------------------------------------------------------------------- #
#  Events
# --------------------------------------------------------------------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await connect_voice()
    bot.loop.create_task(fetch_news_loop(news_queue))
    bot.loop.create_task(consume_news())


@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    """Kick listeners who lack the News‑Pro role."""
    if member.bot:
        return

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if after.channel == channel and not any(r.name == "News-Pro" for r in member.roles):
        try:
            await member.move_to(None)
            await member.send("Subscribe here → https://buy.newspro.link")
        except discord.Forbidden:
            pass


# --------------------------------------------------------------------------- #
#  Background task
# --------------------------------------------------------------------------- #
async def consume_news():
    text_chan = bot.get_channel(TEXT_CHANNEL_ID)

    while True:
        item = await news_queue.get()

        # ----- send embed -----
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

        # ----- speak headline -----
        ssml = to_ssml(title)
        path = await bot.loop.run_in_executor(None, synthesize, ssml)

        voice = discord.utils.get(bot.voice_clients, guild=bot.get_guild(GUILD_ID))
        if not voice or not voice.is_connected():
            voice = await connect_voice()

        if voice and not voice.is_playing():
            audio = discord.FFmpegPCMAudio(path)

            def _cleanup(_: object):
                try:
                    os.remove(path)
                except OSError:
                    pass

            voice.play(audio, after=_cleanup)
        else:
            os.remove(path)


# --------------------------------------------------------------------------- #
#  Slash command
# --------------------------------------------------------------------------- #
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


# --------------------------------------------------------------------------- #
#  Run the bot
# --------------------------------------------------------------------------- #
bot.run(DISCORD_TOKEN)
