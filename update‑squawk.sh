# ---  update‑squawk.sh  ----------------------------------------
cd /root/squawk                       # 1 go to the repo
git fetch origin                      # 2 grab newest commit metadata
git reset --hard origin/main          # 3 force‑sync to GitHub version
docker build -t squawk .              # 4 rebuild image
docker rm -f squawk 2>/dev/null || true
docker run -d --name squawk \
  --restart unless-stopped \
  --env-file /root/squawk/.env \
  squawk
docker logs -f squawk                 # 5 stream start‑up log
# ----------------------------------------------------------------
