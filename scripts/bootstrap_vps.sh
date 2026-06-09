#!/usr/bin/env bash
# One-time VPS setup. Run as root on the server.
# Usage: bash bootstrap_vps.sh https://github.com/YOUR_USER/content-saas-bot.git

set -euo pipefail

REPO_URL="${1:-}"
APP_DIR="/opt/content-saas-bot"

if [[ -z "$REPO_URL" ]]; then
  echo "Usage: bash bootstrap_vps.sh <git-repo-url>"
  exit 1
fi

apt-get update
apt-get install -y git python3 python3-venv python3-pip

if [[ -d "$APP_DIR/.git" ]]; then
  echo "Repo already exists at $APP_DIR, pulling..."
  cd "$APP_DIR"
  git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp .env.example .env
  echo ""
  echo ">>> Created $APP_DIR/.env — edit it and set BOT_TOKEN + ADMIN_IDS:"
  echo "    nano $APP_DIR/.env"
  echo ""
fi

cp deploy/contentbot.service /etc/systemd/system/contentbot.service
systemctl daemon-reload
systemctl enable contentbot.service

echo ""
echo "Bootstrap done."
echo "1) Edit .env:  nano $APP_DIR/.env"
echo "2) Start bot:  systemctl start contentbot"
echo "3) Check logs: journalctl -u contentbot -f"
