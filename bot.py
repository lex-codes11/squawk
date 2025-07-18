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

##############################################################################
# Globals & intents
##############################################################################

intents            = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True

bot          = commands.Bot(command_prefix="!", intents=intents)
news_queue: asyncio.Queue = asyncio.Queue()

##############################################################################
# Utility helpers
##############################################################################


def spell(word: str) -> str:
    """Spell tickers (NVDA 👉 N‑V‑D‑A)."""
    if word.isalpha() and word.isupper() and len(word) <= 5:
        return "-".join(word)
    return word


def to_ssml(title: str) -> str:
    words = [spell(w) for w in title.split()]
    return f"<speak>{' '.join(words)}</speak>"


##############################################################################
# Voice handling
##############################################################################


async def ensure_voice_connection():
    """Keep the bot connected to the configured voice (or stage) channel."""
    while True:
        try:
            guild   = bot.get_guild(GUILD_ID)
            channel = guild and guild.get_channel(VOICE_CHANNEL_ID)

            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                bot.logger.warning("Configured VOICE_CHANNEL_ID is not a voice/stage channel")
                return                                         # give up – mis‑config

            voice = discord.utils.get(bot.voice_clients, guild=guild)
            if voice and voice.is_connected():
                await asyncio.sleep(30)  # already connected – check again later
                continue

            bot.logger.info("Connecting to voice…")
            voice = await channel.connect(timeout=10, reconnect=False)
            bot.logger.info("Voice connect OK")

            # unsuppress on stage channels
            try:
                await guild.change_voice_state(channel=channel, self_mute=False, self_deaf=False)
            except Exception:
                pass

        except asyncio.TimeoutError:
            bot.logger.warning("Voice connect timed out – will retry")
        except discord.ClientException as e:
            bot.logger.warning("Voice connect failed: %s", e)
        except Exception as e:
            bot.logger.exception("Unexpected voice error: %s", e)

        await asyncio.sleep(10)  # wait a bit before next (re)attempt


##############################################################################
# Events
##############################################################################


@bot.event
async def on_ready():
    bot.logger.info("✅ Logged in as %s (%s)", bot.user, bot.user.id)

    # run voice connection & background jobs without blocking on_voice failures
    bot.loop.create_task(ensure_voice_connection())
    bot.loop.create_task(fetch_news_loop(news_queue))
    bot.loop.create_task(consume_news())


##############################################################################
# News consumer
##############################################################################


async def consume_news():
    text_chan = bot.get_channel(TEXT_CHANNEL_ID)

    while True:
        item   = await news_queue.get()
        title  = item["title"]
        url    = item.get("url")
        pub_at = item.get("published") or ""

        try:
            ts = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
        except Exception:
            ts = datetime.now(timezone.utc)

        # 1) post embed
        if isinstance(text_chan, discord.TextChannel):
            embed = discord.Embed(title=title, url=url, timestamp=ts)
            embed.set_footer(text="NewsAPI.org")
            await text_chan.send(embed=embed)

        # 2) speak headline
        ssml = to_ssml(title)
        path = await bot.loop.run_in_executor(None, synthesize, ssml)

        voice = discord.utils.get(bot.voice_clients, guild=bot.get_guild(GUILD_ID))
        if not voice or not voice.is_connected():
            voice = None  # skip playing, but still delete wav/mp3 afterward

        if voice and not voice.is_playing():
            audio = discord.FFmpegPCMAudio(path)

            def _cleanup(_):
                try:
                    os.remove(path)
                except OSError:
                    pass

            voice.play(audio, after=_cleanup)
        else:
            # not connected / busy – just discard file
            os.remove(path)


##############################################################################
# Slash‑command ping
##############################################################################


@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


##############################################################################
# Kick off bot
##############################################################################

bot.run(DISCORD_TOKEN)
