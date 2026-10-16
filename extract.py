"""Read a receipt photo with a local open-weight vision model (Gemma via Ollama).

Nothing leaves the machine: the only network call goes to localhost.
"""
import base64
import json
import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("RECEIPT_MODEL", "gemma3:4b")
CATEGORIES = ["Software", "Hardware", "Travel", "Meals", "Office", "Marketing", "Services", "Other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "total": {"type": "number"},
        "vat": {"type": "number"},
        "currency": {"type": "string"},
        "category": {"type": "string", "enum": CATEGORIES},
    },
    "required": ["vendor", "date", "total", "vat", "currency", "category"],
}

PROMPT = (
    "You read receipts and invoices for a freelancer's bookkeeping. "
    "Return the vendor name, the date as YYYY-MM-DD, the total paid, the VAT/tax amount "
    "(0 if not shown), the 3-letter currency code, and the best category. "
    "Use only what is printed on the document. Do not guess missing numbers."
)


def ollama_available() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).ok
    except requests.RequestException:
        return False


def extract_receipt(image_bytes: bytes) -> dict:
    """Send one image to the local model and return the parsed fields."""
    payload = {
        "model": MODEL,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0},
        "messages": [{
            "role": "user",
            "content": PROMPT,
            "images": [base64.b64encode(image_bytes).decode()],
        }],
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])
