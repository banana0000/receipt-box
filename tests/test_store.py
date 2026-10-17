import io

import store


def test_demo_records_have_all_columns():
    df = store.to_frame(store.demo_records())
    assert set(store.COLUMNS) <= set(df.columns)
    assert len(df) > 10


def test_category_totals_add_up():
    df = store.to_frame(store.demo_records())
    assert abs(store.by_category(df)["total"].sum() - df["total"].sum()) < 0.01


def test_bad_values_do_not_crash():
    df = store.to_frame([{"vendor": "x", "date": "garbage", "total": "n/a", "vat": None,
                          "currency": "EUR", "category": "Other", "file": "f"}])
    assert df["total"].iat[0] == 0.0
    assert store.by_month(df).empty


def test_csv_export():
    assert store.to_csv(store.to_frame(store.demo_records())).startswith("vendor,date,")


def _rec(vendor, date, total, cur="EUR", vat=0, cat="Other"):
    return {"vendor": vendor, "date": date, "total": total, "vat": vat, "currency": cur,
            "category": cat, "file": "f"}


def test_duplicates_flag_only_the_second_copy():
    df = store.to_frame([_rec("Figma", "2026-10-01", 15), _rec(" figma", "2026-10-01", 15),
                         _rec("Figma", "2026-11-01", 15), _rec("x", None, 0), _rec("x", None, 0)])
    assert store.duplicate_mask(df).tolist() == [False, True, False, False, False]


def test_vat_by_quarter_splits_currencies():
    df = store.to_frame([_rec("a", "2026-01-05", 120, vat=20), _rec("b", "2026-03-30", 60, vat=10),
                         _rec("c", "2026-04-02", 50, "HUF", vat=5)])
    q = store.vat_by_quarter(df).set_index(["currency", "quarter"])
    assert q.loc[("EUR", "2026Q1"), "vat"] == 30
    assert q.loc[("HUF", "2026Q2"), "receipts"] == 1


def test_rules_are_saved_and_applied(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RULES_FILE", tmp_path / "rules.json")
    assert store.load_rules() == {}
    store.save_rules({"figma": "Software"})
    assert store.apply_rules(_rec("Figma ", "2026-01-01", 5))["category"] == "Software"
    assert store.apply_rules(_rec("Other Co", "2026-01-01", 5))["category"] == "Other"


def test_items_become_text_and_blank_currency_is_marked():
    rec = {**_rec("a", "2026-01-01", 5, cur=""), "items": [{"description": "Coffee", "amount": 3.5}]}
    df = store.to_frame([rec])
    assert df["items"].iat[0] == "Coffee 3.5" and df["currency"].iat[0] == "?"


def test_xlsx_has_three_sheets():
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(store.to_xlsx(store.to_frame(store.demo_records()))))
    assert wb.sheetnames == ["Receipts", "By category", "VAT by quarter"]
