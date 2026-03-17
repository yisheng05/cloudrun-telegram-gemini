import logging
from typing import Any, Dict, Optional
import os

_backend = 'generativeai'
genai = None

try:
    import google.generativeai as genai
    logging.info('Using google.generativeai backend')
except ImportError:
    logging.error('google.generativeai not found')
    _backend = None


def configure(api_key: str):
    """Configure the GenAI backend with the provided API key."""
    if _backend == 'generativeai' and genai:
        try:
            genai.configure(api_key=api_key)
            return
        except Exception:
            logging.exception('Failed to configure google.generativeai')
            pass
    # Fallback env var
    os.environ['GOOGLE_API_KEY'] = api_key


def generate_content(model_name: str, prompt: str, *, max_output_tokens: int = 512, temperature: float = 0.2) -> Dict[str, Any]:
    """Generate content using google.generativeai backend.

    Returns a dict with keys: text (str), finish_reason (str|None), token_count (int|None)
    """
    if _backend == 'generativeai' and genai:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            
            # Extract text safely
            text = ''
            if hasattr(response, 'text') and response.text:
                text = response.text
            elif hasattr(response, 'parts'):
                 text = "".join([part.text for part in response.parts])
            else:
                try:
                    text = response.candidates[0].content.parts[0].text
                except Exception:
                    text = str(response)

            finish = None
            try:
                finish = response.candidates[0].finish_reason.name
            except Exception:
                finish = str(response.candidates[0].finish_reason) if response.candidates else None

            token_count = None
            try:
                token_count = response.usage_metadata.candidates_token_count
            except Exception:
                token_count = None

            return {"text": text, "finish_reason": finish, "token_count": token_count}
        except Exception:
            logging.exception('google.generativeai backend failed')
            raise

    raise RuntimeError('No working GenAI backend available')
