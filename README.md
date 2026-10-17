# Receipt Box

A receipt and invoice sorter for freelancers that runs entirely on your laptop.
Photos and PDFs go to an open-weight vision model (Gemma 3 via Ollama), and the result is a
categorised expense dashboard plus a CSV or Excel file for your accountant.
Nothing is uploaded anywhere.

## Features

- Reads receipt photos (JPG / PNG) and PDF invoices (text layer or scanned) with Gemma 3.
- Dashboard: total spend, VAT to reclaim, spend by category and by month, VAT by quarter.
- Editable table: fix any cell, delete rows. Changing a category teaches the app: that vendor is
  sorted the same way from now on (saved in `rules.json`).
- Possible duplicates are highlighted.
- Several currencies: pick one, or "All currencies" to see them side by side. Amounts are never converted.
- Export to CSV or Excel (receipts, spend per category, VAT per quarter).
- Optional line-item extraction (slower).
- Files are read one at a time with visible progress; your receipts stay in your browser between visits.

## Run it

1. Install [Ollama](https://ollama.com/download) and pull the model: `ollama pull gemma3:4b`
2. `pip install -r requirements.txt`
3. `python app.py`, then open http://127.0.0.1:8050

No model yet? Click **Load demo data** to explore the dashboard. The `samples/` folder has three
fictional documents to try (`python make_samples.py` regenerates them).

A receipt takes roughly 15-20 seconds on a CPU.

## Configuration

| Variable | Default |
|---|---|
| `RECEIPT_MODEL` | `gemma3:4b` |
| `OLLAMA_URL` | `http://localhost:11434` |
| `RECEIPT_RULES` | `rules.json` next to the code |

## Deploy on Render

`render.yaml` is a Blueprint with two paid services: a private `ollama` service (Docker, Gemma 3 4B
baked into the image, `pro plus` for the RAM it needs) and the `receipt-box` web service, which
reaches Ollama over Render's private network.

1. Render dashboard, **New**, **Blueprint**, pick this repository.
2. Wait for both services to be live. The `ollama` build is long because it downloads the model.
3. Open the web service URL. The status line should read `Model: gemma3:4b (local) - ready`.

Without the `ollama` service the hosted app still works with the demo data, but cannot read uploads.

## How it works

- `extract.py` sends each image to the local model with a JSON schema, so the reply is always
  `vendor, date, total, vat, currency, category` (plus `items` if asked).
- `store.py` turns records into tables, duplicate checks, VAT per quarter, learned vendor rules and the exports.
- `app.py` is a Dash app with Plotly charts.

## Tests

`python -m pytest -q`

## License

MIT
