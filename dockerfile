# ---------- Dockerfile ----------
# Slim Python image plus all libraries Discord voice needs
FROM python:3.12-slim

# ffmpeg     : streams MP3 → Discord
# libopus0   : Discord’s audio codec
# libsodium23: PyNaCl’s UDP encryption backend (fixes 4006 errors)
RUN apt-get update -y && \
    apt-get install -y ffmpeg libopus0 libsodium23 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
