# tts.py
"""ElevenLabs TTS helper – returns a temp MP3 file path."""

from __future__ import annotations

import os
import tempfile
import requests

from config import ELEVEN_KEY, VOICE_ID

API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

# Choose the correct auth header for the key format
if ELEVEN_KEY.startswith("sk_"):
    HEADERS = {
        "Authorization": f"Bearer {ELEVEN_KEY}",
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
else:
    HEADERS = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }


def synthesize(text: str) -> str:
    """Convert text → TTS, return path to a temp MP3 file."""
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}
    r = requests.post(API_URL, json=payload, headers=HEADERS, stream=True, timeout=60)
    r.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    for chunk in r.iter_content(1024):
        tmp.write(chunk)
    tmp.close()
    return tmp.name
