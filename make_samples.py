"""Generate fictional demo documents in samples/ (one PDF invoice, two receipt images)."""
from pathlib import Path

import pymupdf

OUT = Path(__file__).parent / "samples"


def invoice_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    t = page.insert_text
    t((50, 70), "NORTHWIND CLOUD LTD.", fontsize=20, fontname="hebo")
    t((50, 90), "12 Harbour Street, Dublin D02 X285, Ireland", fontsize=9)
    t((50, 103), "VAT ID: IE1234567T", fontsize=9)
    t((400, 70), "INVOICE", fontsize=22, fontname="hebo")
    t((400, 92), "No. INV-2026-0418", fontsize=10)
    t((400, 106), "Date: 2026-10-14", fontsize=10)
    t((50, 160), "Billed to:", fontsize=10, fontname="hebo")
    t((50, 175), "Eszter Kovacs (freelance)", fontsize=10)
    rows = [("Description", "Qty", "Unit", "Amount"),
            ("Cloud hosting - Pro plan, Oct 2026", "1", "62.00", "62.00"),
            ("Object storage 500 GB", "1", "18.50", "18.50"),
            ("Priority support add-on", "1", "9.90", "9.90")]
    y = 230
    for i, r in enumerate(rows):
        f = "hebo" if i == 0 else "helv"
        for x, v in zip((50, 330, 400, 480), r):
            t((x, y), v, fontsize=10, fontname=f)
        y += 22
    page.draw_line((50, y - 10), (545, y - 10))
    for label, val, bold in (("Subtotal", "90.40", False), ("VAT 23%", "20.79", False),
                             ("TOTAL DUE (EUR)", "111.19", True)):
        f = "hebo" if bold else "helv"
        t((330, y + 12), label, fontsize=11, fontname=f)
        t((480, y + 12), val, fontsize=11, fontname=f)
        y += 22
    t((50, 780), "Paid by card. Thank you for your business.", fontsize=9)
    doc.save(path)


def receipt_png(path: Path, lines: list[tuple[str, str]], height: int) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=260, height=height)
    page.draw_rect(page.rect, color=None, fill=(0.97, 0.96, 0.92))
    y = 30
    for text, style in lines:
        font, size = ("cobo", 12) if style == "b" else ("cour", 9)
        w = pymupdf.get_text_length(text, fontname=font, fontsize=size)
        x = (260 - w) / 2 if style in ("b", "c") else 18
        page.insert_text((x, y), text, fontname=font, fontsize=size)
        y += size + 6
    page.get_pixmap(dpi=200).save(path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    invoice_pdf(OUT / "invoice-northwind-cloud.pdf")
    receipt_png(OUT / "receipt-cafe-linden.png", [
        ("CAFE LINDEN", "b"), ("Linden ut 5, Budapest", "c"), ("Tel: 06 1 555 0142", "c"), ("", ""),
        ("2026-10-12  13:47", "l"), ("------------------------", "l"),
        ("2x Flat white      3 800", "l"), ("1x Club sandwich    4 200", "l"),
        ("1x Sparkling water   900", "l"), ("------------------------", "l"),
        ("VAT 27% incl.      1 892", "l"),
        ("TOTAL HUF          8 900", "b"), ("", ""), ("Card payment", "c"), ("Thank you!", "c"),
    ], 330)
    receipt_png(OUT / "receipt-papirbolt.png", [
        ("PAPIRBOLT KFT.", "b"), ("Vaci utca 22, Budapest", "c"), ("", ""),
        ("2026-10-09  10:12", "l"), ("------------------------", "l"),
        ("A4 paper 500 sh     2 490", "l"), ("Ink cartridge x2    11 980", "l"),
        ("Stapler               1 650", "l"), ("------------------------", "l"),
        ("Net               16 120", "l"), ("VAT 27%            4 352", "l"),
        ("TOTAL HUF         20 472", "b"), ("", ""), ("Cash", "c"),
    ], 310)
    print("wrote", *sorted(p.name for p in OUT.iterdir()))
