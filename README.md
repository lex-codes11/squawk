# 📰 News Squawk Bot

Reads the latest U.S. business headlines aloud in a Discord voice channel
and posts the links in a text channel. Non‑subscribers are auto‑kicked.

---

## 1  Quick start (Docker)

```bash
# on your DigitalOcean droplet
git clone https://github.com/<you>/news-squawk-bot.git
cd news-squawk-bot
cp .env.example .env   # fill real tokens / IDs
docker build -t squawk .
docker run -d --name squawk \
  --restart unless-stopped \
  --env-file .env \
  squawk
docker logs -f squawk  # "Voice handshake complete" = success
