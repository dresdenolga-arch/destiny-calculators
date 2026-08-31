"""Shared look for the printable result pages (Matrix/Bazi/Jyotish/compatibility).

Same visual language as engine/matrix/scripts/render_html.py, plus a
print stylesheet and a "Скачать PDF" button that just calls window.print() —
no extra dependency, works in every browser via its own "Save as PDF".
"""
import html

BASE_CSS = """
:root {
  color-scheme: light dark;
  --bg: #f7f7fb; --card: #ffffff; --ink: #1c1b22; --muted: #6b6a76;
  --line: #d8d6e3; --accent: #7c6bb0;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #16151c; --card: #1f1e27; --ink: #ecebf2; --muted: #a3a1b0;
          --line: #35333f; --accent: #a996e0; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 0 20px 48px; background: var(--bg); color: var(--ink);
       font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1120px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; font-weight: 650; }
.sub { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
.cols { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px;
        padding: 18px; flex: 1 1 420px; min-width: 320px; margin-top: 24px; }
.cols .card { margin-top: 0; }
.card h2 { font-size: 15px; margin: 0 0 14px; font-weight: 600; letter-spacing: .02em;
           text-transform: uppercase; color: var(--muted); }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; font-weight: 600; color: var(--muted); font-size: 11px;
     text-transform: uppercase; letter-spacing: .04em; padding: 0 6px 8px; }
td { padding: 7px 6px; border-top: 1px solid var(--line); vertical-align: top; }
.big { font-size: 26px; font-weight: 650; color: var(--accent); line-height: 1.2; }
.tag { display: inline-block; font-size: 10px; letter-spacing: .04em; text-transform: uppercase;
       padding: 2px 7px; border-radius: 20px; margin: 2px 4px 2px 0; background: var(--bg);
       border: 1px solid var(--line); color: var(--muted); }
.tag.hit { background: #d8f0dd; color: #1f5130; border-color: transparent; }
.grid { display: flex; flex-wrap: wrap; gap: 16px; }
.pill { flex: 1 1 220px; border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
.pill h3 { margin: 0 0 6px; font-size: 13px; font-weight: 650; }
.muted { color: var(--muted); }
.note { color: var(--muted); font-size: 12px; line-height: 1.55; margin-top: 14px; }
footer { color: var(--muted); font-size: 12px; line-height: 1.6; margin-top: 26px;
         border-top: 1px solid var(--line); padding-top: 14px; }
details.collapsible { margin-top: 24px; }
details.collapsible > summary { cursor: pointer; font-size: 15px; font-weight: 650;
  color: var(--muted); text-transform: uppercase; letter-spacing: .02em; padding: 4px 0; }
"""

PRINT_CSS = """
@media print {
  .no-print { display: none !important; }
  body { background: #fff !important; padding: 0 12px 12px; }
  .card { break-inside: avoid; box-shadow: none; }
  a { color: inherit; text-decoration: none; }
  details.collapsible { break-before: page; }
  details.collapsible > summary { list-style: none; }
}
"""

PRINT_BAR_CSS = """
.print-bar { position: sticky; top: 0; z-index: 5; display: flex; justify-content: flex-end;
             gap: 8px; padding: 16px 0 8px; background: var(--bg); }
.print-btn { background: var(--accent); color: #fff; border: none; border-radius: 8px;
             padding: 10px 16px; font-size: 14px; font-weight: 600; cursor: pointer; }
.print-btn:hover { opacity: .9; }
"""


def page_style(extra_css: str = "") -> str:
    return f"<style>{BASE_CSS}{extra_css}{PRINT_BAR_CSS}{PRINT_CSS}</style>"


def print_bar_html() -> str:
    return (
        '<div class="print-bar no-print">'
        '<button class="print-btn" onclick="window.print()">Скачать PDF</button>'
        '</div>'
    )


def esc(value) -> str:
    return html.escape(str(value)) if value is not None else ""


def error_page(message: str) -> str:
    return (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Ошибка расчёта</title>{page_style()}</head>'
        f'<body><div class="wrap"><div class="card" style="margin-top:24px">'
        f'<h2>Не получилось посчитать</h2><p>{esc(message)}</p>'
        f'</div></div></body></html>'
    )
