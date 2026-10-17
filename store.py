"""Turning extracted records into tables and exports."""
import io
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["vendor", "date", "total", "vat", "currency", "category", "items", "file"]
RULES_FILE = Path(os.getenv("RECEIPT_RULES", Path(__file__).with_name("rules.json")))


def demo_records() -> list[dict]:
    """Sample receipts (all USD) so the dashboard can be explored without a model."""
    rng = np.random.default_rng(7)
    vendors = [("Figma", "Software", 15), ("GitHub", "Software", 4), ("Notion", "Software", 10),
               ("Lufthansa", "Travel", 240), ("Cafe Central", "Meals", 18), ("IKEA", "Office", 90),
               ("Canva", "Marketing", 13), ("Apple Store", "Hardware", 420), ("Upwork", "Services", 60)]
    rows = []
    for m in range(1, 10):
        for v, cat, base in vendors:
            if rng.random() < 0.55:
                total = round(float(base * rng.uniform(0.8, 1.3)), 2)
                rows.append({"vendor": v, "date": f"2026-{m:02d}-{int(rng.integers(1, 28)):02d}",
                             "total": total, "vat": round(total * 0.2 / 1.2, 2),
                             "currency": "USD", "category": cat, "file": "demo"})
    return rows


def items_text(items) -> str:
    """Line items as one readable string ('Coffee 3.5; Cake 4')."""
    if isinstance(items, str):
        return items
    if not isinstance(items, list):
        return ""
    return "; ".join(f"{i.get('description', '?')} {i.get('amount', '')}".strip()
                     for i in items if isinstance(i, dict))


def to_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ("total", "vat"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["currency"] = df["currency"].fillna("").astype(str).str.strip().str.upper().replace("", "?")
    df["items"] = df["items"].map(items_text)
    return df


def duplicate_mask(df: pd.DataFrame) -> pd.Series:
    """True for the 2nd+ copy of a receipt with the same vendor, date, total and currency."""
    key = df.assign(_vendor=df["vendor"].fillna("").astype(str).str.strip().str.lower())
    dup = key.duplicated(subset=["_vendor", "date", "total", "currency"], keep="first")
    return dup & df["date"].notna() & (df["total"] > 0)


def vat_by_quarter(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["date"]).copy()
    d["quarter"] = d["date"].dt.to_period("Q").astype(str)
    out = d.groupby(["currency", "quarter"], as_index=False).agg(
        receipts=("total", "size"), total=("total", "sum"), vat=("vat", "sum"))
    return out.round({"total": 2, "vat": 2})


def load_rules() -> dict:
    """Vendor -> category overrides the user taught the app (lower-case vendor keys)."""
    try:
        return json.loads(RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_rules(rules: dict) -> None:
    RULES_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_rules(rec: dict, rules: dict | None = None) -> dict:
    rules = load_rules() if rules is None else rules
    cat = rules.get(str(rec.get("vendor") or "").strip().lower())
    return {**rec, "category": cat} if cat else rec



def by_category(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("category", as_index=False)["total"].sum().sort_values("total", ascending=False)


def by_month(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["date"]).copy()
    d["month"] = d["date"].dt.to_period("M").dt.to_timestamp()
    return d.groupby("month", as_index=False)["total"].sum()


def to_csv(df: pd.DataFrame) -> str:
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False)


def to_xlsx(df: pd.DataFrame) -> bytes:
    """Workbook for the accountant: receipts, spend per category, VAT per quarter."""
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    cats = df.groupby(["currency", "category"], as_index=False)["total"].sum().round(2)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        out.to_excel(xl, sheet_name="Receipts", index=False)
        cats.to_excel(xl, sheet_name="By category", index=False)
        vat_by_quarter(df).to_excel(xl, sheet_name="VAT by quarter", index=False)
        for ws in xl.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(
                    40, max(len(str(c.value or "")) for c in col) + 2)
    return buf.getvalue()
