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
ITEMS_PROPERTY = {"type": "array", "items": {"type": "object", "properties": {
    "description": {"type": "string"}, "amount": {"type": "number"}},
    "required": ["description", "amount"]}}
ITEMS_PROMPT = (" Also list up to 8 purchased line items (description and amount, no tax or total rows); "
                "use an empty list if none are legible.")


def schema_for(items: bool) -> dict:
    if not items:
        return SCHEMA
    return {**SCHEMA, "properties": {**SCHEMA["properties"], "items": ITEMS_PROPERTY},
            "required": SCHEMA["required"] + ["items"]}


def ollama_available() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).ok
    except requests.RequestException:
        return False


def pdf_to_image(pdf_bytes: bytes) -> bytes:
    """Render the first page of a PDF invoice to a PNG the vision model can read."""
    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc[0].get_pixmap(dpi=150).tobytes("png")


def pdf_text(pdf_bytes: bytes) -> str:
    """Text layer of the first page ('' for scanned PDFs)."""
    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return " ".join(doc[0].get_text().split())


def _chat(message: dict, items: bool = False) -> dict:
    message = {**message, "content": message["content"] + (ITEMS_PROMPT if items else "")}
    payload = {
        "model": MODEL,
        "stream": False,
        "format": schema_for(items),
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 600 if items else 200},
        "messages": [message],
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def extract_receipt(image_bytes: bytes, items: bool = False) -> dict:
    """Send one image to the local model and return the parsed fields (plus line items if asked)."""
    return _chat({"role": "user", "content": PROMPT,
                  "images": [base64.b64encode(image_bytes).decode()]}, items)


def extract_pdf(pdf_bytes: bytes, items: bool = False) -> dict:
    """PDFs with a text layer go in as plain text (fast); scans fall back to the vision path."""
    text = pdf_text(pdf_bytes)
    if len(text) > 40:
        return _chat({"role": "user", "content": f"{PROMPT}\n\nDocument text:\n{text[:6000]}"})
    return extract_receipt(pdf_to_image(pdf_bytes))
