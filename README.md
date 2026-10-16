# Receipt Box

A receipt and invoice sorter for freelancers that runs entirely on your laptop.
Photos go to an open-weight vision model (Gemma 3 via Ollama), and the result is a
categorised expense dashboard plus a CSV for your accountant. Nothing is uploaded anywhere.

## Run it

1. Install [Ollama](https://ollama.com/download) and pull the model: `ollama pull gemma3:4b`
2. `pip install -r requirements.txt`
3. `python app.py`, then open http://127.0.0.1:8050

No model yet? Click **Load demo data** to explore the dashboard.

## Configuration

| Variable | Default |
|---|---|
| `RECEIPT_MODEL` | `gemma3:4b` |
| `OLLAMA_URL` | `http://localhost:11434` |

## How it works

- `extract.py` sends each image to the local model with a JSON schema, so the reply is always
  `vendor, date, total, vat, currency, category`.
- `store.py` turns records into tables and the CSV export.
- `app.py` is a Dash app with Plotly charts.

## Tests

`python -m pytest -q`

## License

MIT
