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
