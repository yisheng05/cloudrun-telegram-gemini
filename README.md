# Zero-Hallucination Tourism Concierge

A stateful, self-learning, ontology-driven Telegram bot deployed on Google Cloud Run. It uses a formal cognitive architecture to provide verified tourism information for Singapore, ensuring zero-hallucination by grounding LLM responses in a Faceted Knowledge Graph that grows dynamically based on user needs.

## 🧠 Cognitive Architecture
![AI Architecture](./architecture.png)

The agent follows a multi-stage **asynchronous** pipeline:
1.  **Async Webhook**: Immediately acknowledges Telegram messages and hands off processing to a background thread to prevent timeouts.
2.  **Perception**: Extracts a rich TMR including **Dialogue Acts** (e.g., Request, Correction) and **Negative Constraints** (e.g., "NOT in Orchard").
3.  **Memory (Situation Model)**: Persists and accumulates user state across turns, allowing for intelligent class transitions and entity persistence.
4.  **Symbolic Deliberation**: Performs ontology-driven queries while respecting complex constraints (Must/Not).
5.  **Dynamic Hydro-Fill**: Automatically triggers the ingestion pipeline on KG cache misses to fetch real-time data from OSM/OneMap.
6.  **Action Rendering**: Uses Gemini to translate verified facts into polished natural language.

## 🛠 Triple-Threat Ingestion Pipeline
The Knowledge Graph is updated via a specialized pipeline:
- **Physicality (OSM)**: Real-time node fetching via area name or coordinate-based radius fallback.
- **Geo-Hierarchy (OneMap API)**: Official resolution of coordinates into Singapore Planning Areas.
- **Enrichment (LLM)**: Distillation of cultural/historical context for every node.
- **Merge Engine**: Safe integration of new nodes into the master `knowledge_graph.json`.

## 🚀 Setup & Deployment
Environment variables:
- `TELEGRAM_BOT_TOKEN` (required)
- `GOOGLE_API_KEY` - Gemini API key
- `USE_TMR` - Set to `true` for LLM-based perception
- `ONEMAP_EMAIL` & `ONEMAP_PASSWORD` - For official geocoding
- `URA_ACCESS_KEY` & `DATA_GOV_API_KEY` - For extended geo-data enrichment

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
  --set-env-vars TELEGRAM_BOT_TOKEN=your_token,GOOGLE_API_KEY=your_key
```

After deployment, set your Telegram bot webhook to the Cloud Run URL (replace URL):

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR_CLOUD_RUN_URL/webhook"
```
