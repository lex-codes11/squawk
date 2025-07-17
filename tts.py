# tts.py
"""ElevenLabs text‑to‑speech helper.

Given some text (or SSML) it returns the path to a temporary
MP3 file that contains the spoken audio.  The file is created
with `tempfile.NamedTemporaryFile(delete=False)` so **you** are
responsible for deleting it once the Discord player is finished.
"""

from __future__ import annotations

import os
import tempfile
from typing import Final

import requests

from config import ELEVEN_KEY, VOICE_ID  # e.g. VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# --------------------------------------------------------------------------- #
API_URL: Final[str] = (
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
)
HEADERS: Final[dict[str, str]] = {
    "xi-api-key": ELEVEN_KEY,      # your validated key (works w/ free tier)
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
BODY_TMPL: Final[dict[str, object]] = {
    "model_id": "eleven_multilingual_v2",
    # "voice_settings": { ... }  # optional
}


def synthesize(text_or_ssml: str) -> str:
    """
    Convert *text_or_ssml* into speech.

    Returns
    -------
    str
        Absolute path to a freshly‑written `.mp3` file.
    Raises
    ------
    requests.HTTPError
        If ElevenLabs responds with a non‑200 status
        (e.g. 401 when the API key is wrong or revoked).
    """
    payload = BODY_TMPL | {"text": text_or_ssml}

    # Stream the audio directly into a temporary file to avoid
    # loading the whole thing into memory.
    with requests.post(
        API_URL, headers=HEADERS, json=payload, stream=True, timeout=30
    ) as resp:
        resp.raise_for_status()  # will raise if the key/voice is invalid

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:  # filter out keep‑alive chunks
                    tmp.write(chunk)

            return tmp.name
