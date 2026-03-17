#!/usr/bin/env bash
set -euo pipefail

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${CLOUD_RUN_URL:-}" ]; then
  echo "Usage: set TELEGRAM_BOT_TOKEN and CLOUD_RUN_URL environment variables before running"
  echo "Example: CLOUD_RUN_URL=https://... TELEGRAM_BOT_TOKEN=... ./set_webhook.sh"
  exit 1
fi

echo "Setting webhook to ${CLOUD_RUN_URL}/webhook"
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${CLOUD_RUN_URL}/webhook" \
  | sed -n '1p'

echo
echo "Done. Check Telegram's response above for success=true"
