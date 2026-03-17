import os
import logging
import time
from flask import Flask, request, jsonify
import requests
import knowledge
import middleware
import metrics

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JW1AG-hWIeC-EO7hxuC0etNHW4Fota3bfEN-cdT5N0zA")

TELEGRAM_API_URL = "https://api.telegram.org"

# Configure Gemini API via adapter
import genai_adapter
genai_adapter.configure(GEMINI_API_KEY)

# Load minimal knowledge graph at startup
WORLD_KG = knowledge.load_kg()
logging.info(f"Loaded knowledge graph with {len(WORLD_KG.get('nodes', []))} nodes")

def call_gemini(prompt: str) -> str:
    try:
        # Try multiple model names in order - newest first
        model_names = [
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ]
        response = None
        last_error = None
        
        for model_name in model_names:
            try:
                logging.info(f"Trying model: {model_name}")
                # Use adapter that supports google.genai or google.generativeai
                resp = genai_adapter.generate_content(model_name, prompt, max_output_tokens=4000, temperature=0.0)
                finish_reason = resp.get('finish_reason')
                token_count = resp.get('token_count')
                logging.info(f"Response finish_reason: {finish_reason}, tokens: {token_count}")
                if finish_reason == "MAX_TOKENS":
                    logging.warning(f"Response hit MAX_TOKENS limit with {token_count} tokens")
                    try:
                        metrics.inc('max_tokens')
                    except Exception:
                        logging.exception('Failed to increment max_tokens metric')
                text = resp.get('text')
                if text:
                    logging.info(f"Returning text from {model_name}: {text[:100]}")
                    return text
                else:
                    logging.warning(f"Model {model_name} returned empty/no text. Response: {resp}")
            except Exception as e:
                last_error = e
                logging.info(f"Model {model_name} failed: {str(e)[:100]}")
                continue
        
        logging.error(f"All models failed or no text returned. Last error: {last_error}")
        return "Sorry, I couldn't generate a response."
    except Exception as e:
        logging.exception("Gemini API call failed")
        return "Sorry, an error occurred while contacting the language model."

def send_telegram_message(chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN is not set")
        return False
    
    # Telegram has a 4096 character limit per message
    # Enforce a strict limit to be safe
    MAX_TELEGRAM_LENGTH = 4000
    
    if len(text) > MAX_TELEGRAM_LENGTH:
        text = text[:MAX_TELEGRAM_LENGTH-3] + "..."
        logging.warning(f"Message exceeded {MAX_TELEGRAM_LENGTH} chars, truncated to {len(text)}")
    
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logging.info(f"Sent message of {len(text)} chars to chat {chat_id}")
        return True
    except Exception:
        logging.exception("Failed to send Telegram message")
        return False


@app.route("/", methods=["GET"])
def index():
    return "Telegram-Gemini Cloud Run webhook. POST updates to /webhook."


@app.route('/metrics', methods=['GET'])
def metrics_endpoint():
    try:
        import metrics as _metrics
        data = _metrics.snapshot()
        return jsonify(data)
    except Exception:
        logging.exception('Failed to get metrics')
        return jsonify({'error': 'failed to get metrics'}), 500


@app.route("/webhook", methods=["POST"])  
def webhook():
    update = request.get_json(force=True)
    logging.info("Received update: %s", update)
    if not update:
        return jsonify({"ok": False, "error": "no update"}), 400

    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")
    if not text or chat_id is None:
        return jsonify({"ok": True})

    prompt = f"User: {text}\nAssistant:"
    # Constrain response to fit in a single Telegram message (4096 char limit)
    constrained_prompt = f"{prompt}\n\n[IMPORTANT: Keep your response under 3500 characters. Do NOT use markdown formatting like **bold** or __italics__. Be concise but complete.]"
    # Use the middleware pipeline (Perception -> Deliberation -> Action)
    # middleware will simulate TMR locally unless USE_TMR env var is set
    reply = middleware.handle_request(call_gemini, text)
    
    # Strip markdown bold and italic markers to reduce message length
    reply = reply.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    
    logging.info(f"Final reply length: {len(reply)} chars")
    
    # Enforce strict character limit before sending
    if len(reply) > 3900:
        reply = reply[:3897] + "..."
        logging.warning(f"Reply truncated to fit Telegram limit")
    send_telegram_message(chat_id, reply)

    return jsonify({"ok": True})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/simulate', methods=['POST'])
def simulate():
    """Non-destructive endpoint for integration testing.

    Accepts JSON: {"text": "..."}
    Returns the model-generated reply JSON without sending to Telegram.
    """
    data = request.get_json(silent=True) or {}
    text = data.get('text') or data.get('message') or ''
    if not text:
        return jsonify({'error': 'no text provided'}), 400

    try:
        # Run middleware pipeline but bypass sending to Telegram by
        # calling the model directly via call_gemini.
        # middleware.handle_request may perform extra actions; for a
        # pure simulate we call the model adapter to get raw text.
        reply = middleware.handle_request(call_gemini, text)
        return jsonify({'ok': True, 'reply': reply}), 200
    except Exception:
        logging.exception('Simulation failed')
        return jsonify({'error': 'simulation failed'}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
