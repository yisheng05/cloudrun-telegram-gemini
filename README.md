# Telegram -> Gemini Cloud Run webhook

Files:
- `main.py` - Flask app handling Telegram webhooks and calling Gemini API
- `Dockerfile`, `.dockerignore`, `requirements.txt`

Environment variables:
- `TELEGRAM_BOT_TOKEN` (required) - your Telegram bot token
- `GEMINI_API_KEY` (optional) - Gemini/Generative Language API key (defaults to provided key)
- `GEMINI_ENDPOINT` (optional) - override model endpoint URL

Build and run locally (optional):

```bash
cd cloudrun-telegram-gemini
docker build -t telegram-gemini:latest .
docker run -e TELEGRAM_BOT_TOKEN=your_token -e GEMINI_API_KEY=your_key -p 8080:8080 telegram-gemini:latest
```

Deploy to Google Cloud Run (example):

```bash
# build and push an image (using gcloud)
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/telegram-gemini

# deploy to Cloud Run
gcloud run deploy telegram-gemini \
  --image gcr.io/$(gcloud config get-value project)/telegram-gemini \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_BOT_TOKEN=your_token,GEMINI_API_KEY=your_key
```

After deployment, set your Telegram bot webhook to the Cloud Run URL (replace URL):

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR_CLOUD_RUN_URL/webhook"
```
