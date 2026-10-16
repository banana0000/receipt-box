"""Turning extracted records into tables and exports."""
import numpy as np
import pandas as pd

COLUMNS = ["vendor", "date", "total", "vat", "currency", "category", "file"]


def demo_records() -> list[dict]:
    """Sample receipts so the dashboard can be explored without a model."""
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
                             "currency": "EUR", "category": cat, "file": "demo"})
    return rows


def to_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ("total", "vat"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


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
