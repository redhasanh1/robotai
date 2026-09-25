"""Build robotai_BOM.xlsx from data/bom.json (the single source of truth, also read by the website).

Every price/URL was read off the live product page (or search results page where
noted). Edit data/bom.json, then run: python tools/build_bom.py
"""
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.hyperlink import Hyperlink

OUT = Path(__file__).resolve().parent.parent / "robotai_BOM.xlsx"

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "bom.json").read_text(encoding="utf-8"))
VERIFIED = DATA["updated"]


def _rows(lst):
    return [(r["item"], r["product"], r["url"], r["price"], r["qty"], r["notes"]) for r in lst]


CORE = _rows(DATA["phase1"]["core"])
OPTIONAL = _rows(DATA["phase1"]["optional"])
ALTERNATIVES = _rows(DATA["phase1"]["alternatives"])
PHASE2 = _rows(DATA["phase2"]["items"])


def build():
    wb = Workbook()
    base = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    title = Font(name="Arial", size=14, bold=True)
    hdr_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    hdr_fill = PatternFill("solid", fgColor="1F3864")
    sec_fill = PatternFill("solid", fgColor="D9E1F2")
    opt_fill = PatternFill("solid", fgColor="FFF2CC")
    tot_fill = PatternFill("solid", fgColor="E2EFDA")
    link_font = Font(name="Arial", size=10, color="0563C1", underline="single")
    input_font = Font(name="Arial", size=10, color="0000FF")
    thin = Side(style="thin", color="BFBFBF")
    box = Border(top=thin, bottom=thin, left=thin, right=thin)
    money = '"$"#,##0.00'
    cols = ["Item", "Product Name", "Link", "Unit Price (CAD)", "Quantity", "Line Total (CAD)", "Notes/Rationale"]
    widths = [34, 46, 44, 15, 10, 16, 80]

    def header(ws, r, labels):
        for c, h in enumerate(labels, 1):
            cell = ws.cell(r, c, h)
            cell.font, cell.fill, cell.border = hdr_font, hdr_fill, box
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def row(ws, r, rec, fill=None):
        item, name, url, price, qty, note = rec
        vals = [item, name, url, price, qty, f"=D{r}*E{r}", note]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(r, c, v)
            cell.font, cell.border = base, box
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if fill:
                cell.fill = fill
        ws.cell(r, 3).hyperlink = url
        ws.cell(r, 3).font = link_font
        ws.cell(r, 4).font = input_font
        ws.cell(r, 5).font = input_font
        ws.cell(r, 4).number_format = money
        ws.cell(r, 6).number_format = money

    def label_value(ws, r, label, formula, fill, fmt=money, font=bold):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        a = ws.cell(r, 1, label)
        a.font, a.fill = font, fill
        a.alignment = Alignment(horizontal="right")
        v = ws.cell(r, 6, formula)
        v.font, v.fill, v.number_format, v.border = bold, fill, fmt, box
        for c in range(1, 8):
            ws.cell(r, c).fill = fill

    def setup(ws, w=widths):
        for i, wd in enumerate(w, 1):
            ws.column_dimensions[chr(64 + i)].width = wd
        ws.sheet_view.showGridLines = False

    # ---------------- BOM sheet ----------------
    ws = wb.active
    ws.title = "BOM"
    setup(ws)
    ws["A1"] = "robotai - Phase 1: Two InMoov-style robotic hands - Bill of Materials"
    ws["A1"].font = title
    ws["A2"] = (f"All prices CAD, read from the linked pages on {VERIFIED}. 3D-printed parts excluded (printing covered). "
                "Blue cells = inputs (edit price/qty); totals recalc automatically.")
    ws["A2"].font = Font(name="Arial", size=9, italic=True)
    ws["A3"] = "Budget (CAD)"
    ws["A3"].font = bold
    ws["B3"] = DATA["budget_cad"]
    ws["B3"].font, ws["B3"].number_format = Font(name="Arial", size=10, bold=True, color="0000FF"), money
    ws["C3"] = "Sales tax rate (ON HST)"
    ws["C3"].font = bold
    ws["D3"] = DATA["tax_rate"]
    ws["D3"].font, ws["D3"].number_format = Font(name="Arial", size=10, color="0000FF"), "0%"

    r = 5
    ws.cell(r, 1, "CORE BOM").font = bold
    for c in range(1, 8):
        ws.cell(r, c).fill = sec_fill
    r += 1
    header(ws, r, cols)
    r += 1
    core_start = r
    for rec in CORE:
        row(ws, r, rec)
        r += 1
    core_end = r - 1
    sub = r
    label_value(ws, r, "Core subtotal (pre-tax)", f"=SUM(F{core_start}:F{core_end})", tot_fill); r += 1
    tax = r
    label_value(ws, r, "Est. HST on core (13%, shipping not included)", f"=F{sub}*$D$3", tot_fill, font=base); r += 1
    tot = r
    label_value(ws, r, "CORE TOTAL incl. tax", f"=F{sub}+F{tax}", tot_fill); r += 1
    label_value(ws, r, "Headroom under budget", f"=$B$3-F{tot}", tot_fill); r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    ws.cell(r, 1, "Under $500 CAD?").font = bold
    ws.cell(r, 1).alignment = Alignment(horizontal="right")
    v = ws.cell(r, 6, f'=IF(F{tot}<=$B$3,"YES - under budget","NO - over budget")')
    v.font = Font(name="Arial", size=10, bold=True, color="006100")
    for c in range(1, 8):
        ws.cell(r, c).fill = tot_fill
    r += 2

    ws.cell(r, 1, "OPTIONAL - fingertip force sensors (NOT in core total)").font = bold
    for c in range(1, 8):
        ws.cell(r, c).fill = opt_fill
    r += 1
    header(ws, r, cols)
    r += 1
    opt_start = r
    for rec in OPTIONAL:
        row(ws, r, rec, fill=opt_fill)
        r += 1
    opt_end = r - 1
    osub = r
    label_value(ws, r, "Optional subtotal (pre-tax)", f"=SUM(F{opt_start}:F{opt_end})", opt_fill); r += 1
    label_value(ws, r, "Core + optional, incl. tax", f"=(F{sub}+F{osub})*(1+$D$3)", opt_fill); r += 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    ws.cell(r, 1, "Still under $500 with sensors?").font = bold
    ws.cell(r, 1).alignment = Alignment(horizontal="right")
    ws.cell(r, 6, f'=IF(F{r-1}<=$B$3,"YES","NO")').font = bold
    for c in range(1, 8):
        ws.cell(r, c).fill = opt_fill
    r += 2

    notes = [
        "RECOMMENDATION: buy the core list + the 2 FSRs. Both fit comfortably under $500 CAD with tax, leaving room for shipping and a spare servo pack.",
        "If you later want all 10 fingertips sensed, the DigiKey 10-pack ($90.19) still keeps core + sensors under $500 with tax.",
        "Wiring rule: ESP32 3.3V/GND -> PCA9685 VCC/GND, SDA/SCL -> GPIO21/22. PSU (6V) -> PCA9685 V+ screw terminal. Common ground between PSU and ESP32. Never feed servos from the ESP32 5V pin.",
        "Not included: shipping (most Amazon.ca items ship free with Prime or over $35), tools (soldering iron, crimper), and fasteners/bearings from the InMoov print list.",
        "Prices change daily - re-check the links before ordering. See 'Alternatives' for budget/premium swaps and 'Phase 2 - Full robot' for arms/base.",
    ]
    ws.cell(r, 1, "Notes").font = bold
    r += 1
    for n in notes:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
        c = ws.cell(r, 1, n)
        c.font = base
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 28
        r += 1
    ws.freeze_panes = "A7"

    # ---------------- Alternatives ----------------
    wa = wb.create_sheet("Alternatives")
    setup(wa)
    wa["A1"] = "Alternatives & swaps (not in any total unless you swap them in)"
    wa["A1"].font = title
    alt_cols = ["Item", "Product Name", "Link", "Pack Price (CAD)", "Packs", "Line Total (CAD)", "Notes/Rationale"]
    header(wa, 3, alt_cols)
    for i, rec in enumerate(ALTERNATIVES, 4):
        row(wa, i, rec)

    # ---------------- Phase 2 ----------------
    wp = wb.create_sheet("Phase 2 - Full robot")
    setup(wp)
    P2CUR = DATA["phase2"].get("currency", "USD")
    wp["A1"] = DATA["phase2"]["title"] + f" - prices in {P2CUR}"
    wp["A1"].font = title
    wp["A2"] = " ".join(DATA["phase2"].get("notes", [])) or "Separate from the $500 CAD hands budget."
    wp["A2"].font = Font(name="Arial", size=9, italic=True)
    wp["C3"] = "USD->CAD rate (assumed, verify)"
    wp["C3"].font = bold
    wp["D3"] = DATA["usd_to_cad"]
    wp["D3"].font = input_font
    p_cols = ["Item", "Product / Vendor", "Link", f"Unit Price ({P2CUR})", "Quantity", f"Line Total ({P2CUR})", "Notes/Rationale"]
    header(wp, 5, p_cols)
    r = 6
    for rec in PHASE2:
        row(wp, r, rec)
        if P2CUR == "USD":
            wp.cell(r, 4).number_format = '"US$"#,##0.00'
            wp.cell(r, 6).number_format = '"US$"#,##0.00'
        r += 1
    if P2CUR == "USD":
        label_value(wp, r, "Phase 2 subtotal (USD, pre-tax/shipping)", f"=SUM(F6:F{r-1})", tot_fill, fmt='"US$"#,##0.00'); r += 1
        label_value(wp, r, "Phase 2 subtotal (CAD, approx.)", f"=F{r-1}*$D$3", tot_fill); r += 2
    else:
        label_value(wp, r, "Phase 2 subtotal (CAD, pre-tax/shipping)", f"=SUM(F6:F{r-1})", tot_fill); r += 1
        label_value(wp, r, "Under the C$1,500 budget by", f"=1500-F{r-1}", tot_fill); r += 2
    wp.cell(r, 1, ("Cerebras = System-2 brain (planner, voice, replanning, success checks) in the cloud; "
                   "ACT/SmolVLA motor policy runs locally at 30-50 Hz. See research brief.")).font = base

    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
