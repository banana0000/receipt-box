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
LAYOUT = dict(margin=dict(l=40, r=20, t=50, b=40), paper_bgcolor="#000000", plot_bgcolor="#000000")

EDITABLE = ["vendor", "date", "total", "vat", "currency", "category"]
TABLE_COLUMNS = ["id", *store.COLUMNS, "flag"]
EMPTY_QUEUE = {"items": [], "total": 0, "done": 0}
ALL = "All currencies"

app = Dash(__name__, title="Receipt Box")
server = app.server


def kpi(label, value):
    return html.Div([html.Div(value, className="kpi-value"), html.Div(label, className="kpi-label")], className="kpi")


def btn(label, id_, extra=""):
    return html.Button(label, id=id_, n_clicks=0, className=f"btn {extra}".strip())


app.layout = html.Div([
    html.H1("Receipt Box"),
    html.P("Drop in receipt photos. A model running on this laptop reads them. Nothing is uploaded anywhere.",
           className="sub"),
    html.Div(id="status", className="sub"),
    dcc.Upload(id="upload", multiple=True, className="upload",
               children=html.Div(["Drag receipts here or ", html.B("click to choose"), " (JPG / PNG / PDF)"])),
    html.Div([
        btn("Load demo data", "demo"),
        btn("Download CSV", "dl-btn"),
        btn("Download Excel", "dlx-btn"),
        btn("Clear", "clear", "btn-clear"),
        dcc.Checklist(id="opt-items", options=[{"label": " Also read line items (slower)", "value": "on"}],
                      value=[], className="opt"),
    ], className="row"),
    html.Div(id="progress", className="progress"),
    html.Div([html.Span("Currency", className="sub"), dcc.Dropdown(id="cur", clearable=False, className="cur")],
             id="cur-row", className="row", style={"display": "none"}),
    dcc.Download(id="dl"),
    dcc.Download(id="dlx"),
    dcc.Store(id="records", data=[], storage_type="local"),
    dcc.Store(id="queue", data=EMPTY_QUEUE),
    dcc.Interval(id="tick", interval=800, disabled=True),
    dcc.Loading(html.Div(id="content"), type="circle", color="#ff9f1a"),
    html.Div(id="notes", className="notes"),
    html.Div([
        html.H3("Receipts", className="h3"),
        html.P("Click a cell to fix it. Changing a category teaches the app: that vendor is sorted the "
               "same way from now on.", className="sub"),
        dash_table.DataTable(
            id="table", page_size=10, sort_action="native", row_deletable=True,
            columns=[{"name": c, "id": c, "editable": c in EDITABLE,
                      **({"presentation": "dropdown"} if c == "category" else {}),
                      **({"type": "numeric"} if c in ("total", "vat") else {})} for c in TABLE_COLUMNS],
            hidden_columns=["id"],
            dropdown={"category": {"options": [{"label": c, "value": c} for c in extract.CATEGORIES]}},
            style_header={"backgroundColor": "#0b0b0b", "color": "#e6edf3", "border": "1px solid #2a2a2a"},
            style_cell={"backgroundColor": "#000000", "color": "#e6edf3", "border": "1px solid #2a2a2a",
                        "maxWidth": 260, "overflow": "hidden", "textOverflow": "ellipsis"},
            style_data_conditional=[{"if": {"filter_query": '{flag} contains "duplicate"'},
                                     "backgroundColor": "#3d2a0a"}]),
    ], id="table-wrap", style={"display": "none"}),
], className="page")


@app.callback(Output("status", "children"), Input("records", "data"))
def status(_):
    ok = extract.ollama_available()
    return f"Model: {extract.MODEL} (local) - " + ("ready" if ok else "Ollama not running, demo data only")


# --- loading receipts: files go into a queue, one is read per tick so progress is visible ---

@app.callback(Output("queue", "data"), Output("progress", "children"),
              Input("upload", "contents"), State("upload", "filename"), State("queue", "data"),
              prevent_initial_call=True)
def enqueue(contents, names, queue):
    new = [{"name": n, "data": c} for c, n in zip(contents or [], names or [])]
    if not new:
        return no_update, no_update
    old = queue or EMPTY_QUEUE
    if old["items"]:
        queue = {"items": old["items"] + new, "total": old["total"] + len(new), "done": old["done"]}
    else:
        queue = {"items": new, "total": len(new), "done": 0}
    return queue, f"Reading {queue['done'] + 1} of {queue['total']}: {queue['items'][0]['name']} ..."


app.clientside_callback(
    "function(q) { return !(q && q.items && q.items.length > 0); }",
    Output("tick", "disabled"), Input("queue", "data"))


@app.callback(Output("records", "data"), Output("queue", "data", allow_duplicate=True),
              Output("progress", "children", allow_duplicate=True),
              Input("tick", "n_intervals"),
              State("queue", "data"), State("records", "data"), State("opt-items", "value"),
              running=[(Output("tick", "disabled"), True, False)],
              prevent_initial_call=True)
def process(_, queue, records, opt_items):
    if not queue or not queue["items"]:
        return no_update, no_update, no_update
    first, rest = queue["items"][0], queue["items"][1:]
    raw = base64.b64decode(first["data"].split(",", 1)[1])
    want_items = bool(opt_items)
    try:
        rec = (extract.extract_pdf(raw, want_items) if first["name"].lower().endswith(".pdf")
               else extract.extract_receipt(raw, want_items))
    except Exception as exc:  # model offline or unreadable image
        rec = {"vendor": f"(failed: {type(exc).__name__})", "date": None, "total": 0,
               "vat": 0, "currency": "", "category": "Other"}
    records = [*(records or []), {**store.apply_rules(rec), "file": first["name"]}]
    done = queue["done"] + 1
    queue = {"items": rest, "total": queue["total"], "done": done}
    msg = (f"Reading {done + 1} of {queue['total']}: {rest[0]['name']} ..." if rest
           else f"Done: {done} receipt{'s' if done != 1 else ''} read on this machine.")
    return records, queue, msg


@app.callback(Output("records", "data", allow_duplicate=True), Output("queue", "data", allow_duplicate=True),
              Output("progress", "children", allow_duplicate=True),
              Input("demo", "n_clicks"), Input("clear", "n_clicks"),
              prevent_initial_call=True)
def reset(*_):
    return (store.demo_records() if ctx.triggered_id == "demo" else []), EMPTY_QUEUE, ""


# --- dashboard ---

@app.callback(Output("cur", "options"), Output("cur", "value"), Output("cur-row", "style"),
              Input("records", "data"), State("cur", "value"))
def currencies(records, current):
    if not records:
        return [], None, {"display": "none"}
    cur = store.to_frame(records)["currency"]
    found = list(cur.value_counts().index)
    options = [ALL, *found] if len(found) > 1 else found
    return (options, (current if current in options else options[0]),
            {"display": "flex" if len(found) > 1 else "none"})


def money(df, col):
    """Sums per currency ('1,234 EUR · 45,000 HUF'); amounts in different currencies are never added."""
    return " · ".join(f"{v:,.0f} {c}" for c, v in df.groupby("currency")[col].sum().items()) or "0"


def charts(sel, cat, multi):
    if not multi:
        return [dcc.Graph(figure=px.pie(cat, names="category", values="total", hole=0.55,
                                        title="Spend by category").update_layout(**LAYOUT), className="half"),
                dcc.Graph(figure=px.bar(store.by_month(sel), x="month", y="total", title="Spend by month")
                          .update_traces(marker_cornerradius=6).update_layout(**LAYOUT), className="half")]
    by_cat = sel.groupby(["currency", "category"], as_index=False)["total"].sum()
    by_mon = sel.dropna(subset=["date"]).assign(month=lambda d: d["date"].dt.to_period("M").dt.to_timestamp()
                                                ).groupby(["currency", "month"], as_index=False)["total"].sum()
    height = 140 + 170 * sel["currency"].nunique()
    figs = []
    for data, x, title in ((by_cat, "category", "Spend by category"), (by_mon, "month", "Spend by month")):
        fig = px.bar(data, x=x, y="total", facet_row="currency", title=title)
        fig.update_traces(marker_cornerradius=6).update_yaxes(matches=None, title=None).update_xaxes(title=None)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        figs.append(dcc.Graph(figure=fig.update_layout(**LAYOUT, height=height), className="half"))
    return figs


@app.callback(Output("content", "children"), Output("table", "data"), Output("table-wrap", "style"),
              Output("notes", "children"),
              Input("records", "data"), Input("cur", "value"))
def render(records, cur):
    if not records:
        return html.P("No receipts yet. Drop some in, or load the demo data.", className="sub"), [], \
            {"display": "none"}, ""
    df = store.to_frame(records)
    dup = store.duplicate_mask(df)
    multi = cur == ALL
    sel = df if multi or not cur else df[df["currency"] == cur]
    cat = store.by_category(sel)
    vat_q = store.vat_by_quarter(sel)
    vat_q = vat_q if multi else vat_q.drop(columns="currency")
    top = (sel["category"].value_counts().index[0] if multi else cat.iloc[0]["category"]) if len(sel) else "-"

    table = df.assign(date=df["date"].dt.strftime("%Y-%m-%d").fillna(""),
                      flag=dup.map({True: "possible duplicate", False: ""}), id=range(len(df)))[TABLE_COLUMNS]
    notes = []
    if dup.any():
        notes.append(html.P(f"{int(dup.sum())} possible duplicate receipt(s), highlighted in the table.",
                            className="warn"))
    if not multi and df["currency"].nunique() > 1:
        notes.append(html.P(f"Showing {cur} only. Pick \"{ALL}\" to see every currency side by side "
                            "(amounts are never converted).", className="sub"))

    content = html.Div([
        html.Div([kpi("Receipts", f"{len(df)}"), kpi("Total spend", money(sel, "total")),
                  kpi("VAT to reclaim", money(sel, "vat")), kpi("Top category", top)], className="kpis"),
        html.Div(charts(sel, cat, multi), className="row"),
        html.H3("VAT to reclaim by quarter", className="h3"),
        dash_table.DataTable(
            data=vat_q.to_dict("records"), columns=[{"name": c, "id": c} for c in vat_q.columns],
            style_header={"backgroundColor": "#0b0b0b", "color": "#e6edf3", "border": "1px solid #2a2a2a"},
            style_cell={"backgroundColor": "#000000", "color": "#e6edf3", "border": "1px solid #2a2a2a"},
            style_table={"maxWidth": "520px"}),
    ])
    return content, table.to_dict("records"), {"display": "block"}, notes


# --- editing: table changes flow back into records; category changes become rules ---

def _num(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


@app.callback(Output("records", "data", allow_duplicate=True),
              Input("table", "data_timestamp"), State("table", "data"), State("records", "data"),
              prevent_initial_call=True)
def edit(_ts, rows, records):
    records, rules, kept, taught = list(records or []), store.load_rules(), [], {}
    for row in rows or []:
        i = int(row["id"])
        if i >= len(records):
            continue
        old = records[i]
        new = {**old,
               "vendor": str(row.get("vendor") or "").strip(),
               "date": row.get("date") or old.get("date"),
               "total": _num(row.get("total"), old.get("total", 0)),
               "vat": _num(row.get("vat"), old.get("vat", 0)),
               "currency": old.get("currency", "") if row.get("currency") == "?" else (row.get("currency") or "").upper(),
               "category": row.get("category") or old.get("category", "Other")}
        if new["category"] != old.get("category") and new["vendor"]:
            taught[new["vendor"].lower()] = new["category"]
        kept.append(new)
    if taught:
        store.save_rules({**rules, **taught})
        kept = [store.apply_rules(r, taught) for r in kept]
    return kept if kept != records else no_update


# --- downloads ---

@app.callback(Output("dl", "data"), Input("dl-btn", "n_clicks"), State("records", "data"),
              prevent_initial_call=True)
def download_csv(_, records):
    if not records:
        return no_update
    return dict(content=store.to_csv(store.to_frame(records)), filename="receipts.csv")


@app.callback(Output("dlx", "data"), Input("dlx-btn", "n_clicks"), State("records", "data"),
              prevent_initial_call=True)
def download_xlsx(_, records):
    if not records:
        return no_update
    return dcc.send_bytes(store.to_xlsx(store.to_frame(records)), "receipts.xlsx")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8050)), debug=bool(os.environ.get("DEBUG")))
