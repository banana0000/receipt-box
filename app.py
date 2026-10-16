"""Receipt Box - a local receipt sorter for freelancers, powered by Gemma via Ollama."""
import base64
import os

import plotly.express as px
import plotly.io as pio
from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

import extract
import store

COLORS = ["#ff9f1a", "#8b949e", "#ffc266", "#6e7681", "#cc7a00", "#b1bac4", "#e0a458", "#4d5560"]
pio.templates.default = "plotly_dark"
pio.templates["plotly_dark"].layout.colorway = COLORS
px.defaults.color_discrete_sequence = COLORS
LAYOUT = dict(margin=dict(l=40, r=20, t=50, b=40), paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")

app = Dash(__name__, title="Receipt Box")
server = app.server


def kpi(label, value):
    return html.Div([html.Div(value, className="kpi-value"), html.Div(label, className="kpi-label")], className="kpi")


app.layout = html.Div([
    html.H1("Receipt Box"),
    html.P("Drop in receipt photos. A model running on this laptop reads them. Nothing is uploaded anywhere.",
           className="sub"),
    html.Div(id="status", className="sub"),
    dcc.Upload(id="upload", multiple=True, className="upload",
               children=html.Div(["Drag receipts here or ", html.B("click to choose"), " (JPG / PNG)"])),
    html.Div([
        html.Button("Load demo data", id="demo", n_clicks=0, className="btn"),
        html.Button("Download CSV", id="dl-btn", n_clicks=0, className="btn"),
    ], className="row"),
    dcc.Download(id="dl"),
    dcc.Store(id="records", data=[]),
    dcc.Loading(html.Div(id="content"), type="circle", color="#ff9f1a"),
], className="page")


@app.callback(Output("status", "children"), Input("records", "data"))
def status(_):
    ok = extract.ollama_available()
    return f"Model: {extract.MODEL} (local) - " + ("ready" if ok else "Ollama not running, demo data only")


@app.callback(Output("records", "data"),
              Input("upload", "contents"), Input("demo", "n_clicks"),
              State("upload", "filename"), State("records", "data"),
              prevent_initial_call=True)
def load(contents, _demo, names, records):
    if ctx.triggered_id == "demo":
        return store.demo_records()
    records = list(records or [])
    for data_url, name in zip(contents or [], names or []):
        raw = base64.b64decode(data_url.split(",", 1)[1])
        try:
            rec = extract.extract_receipt(raw)
        except Exception as exc:  # model offline or unreadable image
            rec = {"vendor": f"(failed: {type(exc).__name__})", "date": None, "total": 0,
                   "vat": 0, "currency": "", "category": "Other"}
        records.append({**rec, "file": name})
    return records


@app.callback(Output("content", "children"), Input("records", "data"))
def render(records):
    if not records:
        return html.P("No receipts yet.", className="sub")
    df = store.to_frame(records)
    cur = df["currency"].mode().iat[0] if df["currency"].astype(bool).any() else ""
    cat = store.by_category(df)
    return html.Div([
        html.Div([kpi("Receipts", f"{len(df)}"), kpi("Total spend", f"{df.total.sum():,.0f} {cur}"),
                  kpi("VAT to reclaim", f"{df.vat.sum():,.0f} {cur}"),
                  kpi("Top category", cat.iloc[0]["category"])], className="kpis"),
        html.Div([
            dcc.Graph(figure=px.pie(cat, names="category", values="total", hole=0.55,
                                    title="Spend by category").update_layout(**LAYOUT), className="half"),
            dcc.Graph(figure=px.bar(store.by_month(df), x="month", y="total",
                                    title="Spend by month").update_layout(**LAYOUT), className="half"),
        ], className="row"),
        dash_table.DataTable(
            data=df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records"),
            columns=[{"name": c, "id": c} for c in store.COLUMNS], page_size=10, sort_action="native",
            style_header={"backgroundColor": "#161b22", "color": "#e6edf3", "border": "1px solid #30363d"},
            style_cell={"backgroundColor": "#0d1117", "color": "#e6edf3", "border": "1px solid #30363d"}),
    ])


@app.callback(Output("dl", "data"), Input("dl-btn", "n_clicks"), State("records", "data"),
              prevent_initial_call=True)
def download(_, records):
    if not records:
        return no_update
    return dict(content=store.to_csv(store.to_frame(records)), filename="receipts.csv")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8050)), debug=bool(os.environ.get("DEBUG")))
