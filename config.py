"""Load and expose environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
NEWSAPI_KEY        = os.getenv("NEWSAPI_KEY")
ELEVEN_KEY         = os.getenv("ELEVEN_KEY")
VOICE_ID           = os.getenv("VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
POLL_SEC           = int(os.getenv("POLL_SEC", "60"))

GUILD_ID           = int(os.getenv("GUILD_ID", "0"))
VOICE_CHANNEL_ID   = int(os.getenv("VOICE_CHANNEL_ID", "0"))
TEXT_CHANNEL_ID    = int(os.getenv("TEXT_CHANNEL_ID", "0"))
