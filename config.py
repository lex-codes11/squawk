# config.py  – centralised settings pulled from the .env

import os
from dotenv import load_dotenv

load_dotenv()                              # reads the .env beside the repo

DISCORD_TOKEN   = os.getenv("DISCORD_TOKEN")          # required
GUILD_ID        = int(os.getenv("GUILD_ID", 0))       # required
VOICE_CHANNEL_ID= int(os.getenv("VOICE_CHANNEL_ID",0))
TEXT_CHANNEL_ID = int(os.getenv("TEXT_CHANNEL_ID",0))

NEWSAPI_KEY     = os.getenv("NEWSAPI_KEY")            # optional (headlines)
ELEVEN_KEY      = os.getenv("ELEVEN_KEY")             # ElevenLabs    (sk_…)
VOICE_ID        = os.getenv("VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
POLL_SEC        = int(os.getenv("POLL_SEC", 60))

# NEW ➜ absolute path where we create the unix socket
QUEUE_SOCK      = os.getenv("QUEUE_SOCK", "/tmp/squawk.sock")
