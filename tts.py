# tts.py  –  fully replace the old file
"""
ElevenLabs Text‑to‑Speech helper.
Returns the path of a temporary MP3 file containing the spoken text.
"""

from __future__ import annotations

import os
import tempfile
import requests

from config import ELEVEN_KEY, VOICE_ID  # make sure these are in .env

API_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"

HEADERS = {              # <- all‑lowercase header spelling is critical
    "xi-api-key": ELEVEN_KEY,
    "content-type": "application/json",
    "accept": "audio/mpeg",
}

PAYLOAD_TEMPLATE = {
    "model_id": "eleven_multilingual_v2",
    # add any voice_settings you like here
}


def synthesize(text: str) -> str:
    """
    Convert *text* to speech with ElevenLabs and return a temp‑file path.
    Raises `requests.HTTPError` if ElevenLabs responds with a non‑200 status.
    """
    data = PAYLOAD_TEMPLATE | {"text": text}
    # optimise latency so audio starts almost immediately
    params = {"optimize_streaming_latency": 1}

    r = requests.post(
        API_URL,
        headers=HEADERS,
        params=params,
        json=data,
        stream=True,
        timeout=60,
    )
    r.raise_for_status()                 # ⇦ will only raise if truly unauthorised

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    for chunk in r.iter_content(8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name
