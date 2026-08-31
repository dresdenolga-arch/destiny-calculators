"""Builds a printable HTML page from jyotish_service.compute()'s JSON."""
from app.render.common import esc, page_style, print_bar_html

PLANET_ORDER = ["Солнце", "Луна", "Марс", "Меркурий", "Юпитер", "Венера", "Сатурн", "Раху", "Кету"]

EXTRA_CSS = """
.planets td.retro { color: #c0392b; font-weight: 650; }
.dasha-current { border: 1px solid var(--accent); border-radius: 12px; padding: 14px; margin-top: 12px; }
"""


def _planets_table(planets: dict, has_houses: bool) -> str:
    header = "<th>Граха</th><th>Положение</th><th>Накшатра</th><th>Достоинство</th>"
    if has_houses:
        header += "<th>Дом</th>"
    rows = []
    for name in PLANET_ORDER:
        if name not in planets:
            continue
        p = planets[name]
        retro = ' <span class="tag">R</span>' if p.get("ретроградность") else ""
        row = (
            f'<tr><td><b>{esc(name)}</b>{retro}</td>'
            f'<td>{esc(p["положение"])}</td>'
            f'<td>{esc(p["накшатра"])}</td>'
            f'<td>{esc(p.get("достоинство", "") or "—")}</td>'
        )
        if has_houses:
            row += f'<td>{esc(p.get("дом", "—"))}</td>'
        row += "</tr>"
        rows.append(row)
    return f'<table><tr>{header}</tr>{"".join(rows)}</table>'


def _karakas_html(karakas: dict) -> str:
    return "<table><tr><th>Каракака</th><th>Граха</th></tr>" + "".join(
        f'<tr><td>{esc(name)}</td><td>{esc(value)}</td></tr>' for name, value in karakas.items()
    ) + "</table>"


def _vimshottari_html(vim: dict) -> str:
    current = vim.get("текущая", {})
    current_html = ""
    if current.get("маха_даша"):
        antar = f' → антар-даша {esc(current["антар_даша"])} (до {esc(current["антар_до"])})' if current.get("антар_даша") else ""
        current_html = (
            f'<div class="dasha-current"><b>Сейчас идёт:</b> маха-даша {esc(current["маха_даша"])} '
            f'(до {esc(current["до"])}){antar}</div>'
        )
    rows = "".join(
        f'<tr><td>{esc(p["планета"])}</td><td>{esc(p["с"])}</td><td>{esc(p["по"])}</td></tr>'
        for p in vim.get("маха_даши", [])
    )
    table = f'<table><tr><th>Планета</th><th>С</th><th>По</th></tr>{rows}</table>'
    return current_html + table


def build_page(data: dict, person: str = "") -> str:
    heading = esc(person) if person else "Джйотиш"
    subtitle = esc(data.get("дата_время", ""))
    has_houses = "лагна" in data
    planets = data.get("грахи", {})

    lagna_html = ""
    if has_houses:
        lagna = data["лагна"]
        lagna_html = (
            f'<div class="card"><h2>Лагна</h2>'
            f'<div class="big">{esc(lagna["положение"])}</div>'
            f'<p class="muted">Накшатра: {esc(lagna["накшатра"])} · '
            f'навамша-лагна: {esc(lagna["навамша_лагна_D9"])}</p></div>'
        )
    elif data.get("примечание_лагна"):
        lagna_html = f'<div class="card"><h2>Лагна</h2><p class="note">{esc(data["примечание_лагна"])}</p></div>'

    warning_html = ""
    if data.get("предупреждение_лагна"):
        warning_html = f'<div class="card"><h2>Внимание</h2><p class="note">{esc(data["предупреждение_лагна"])}</p></div>'

    panchanga = data.get("панчанга", {})
    panchanga_html = ""
    if panchanga:
        panchanga_html = (
            '<div class="grid">'
            f'<div class="pill"><h3>Титхи</h3><p>{esc(panchanga.get("титхи", "—"))}</p></div>'
            f'<div class="pill"><h3>Вара (день недели)</h3><p>{esc(panchanga.get("вара", "—"))}</p></div>'
            f'<div class="pill"><h3>Накшатра Луны</h3><p>{esc(panchanga.get("накшатра_луны", "—"))}</p></div>'
            '</div>'
        )

    note_html = f'<p class="note">{esc(data["примечание"])}</p>' if data.get("примечание") else ""

    footer = (
        "Джйотиш — традиционная символическая система, не наука и не замена решений "
        "человека. Даша задаёт общую тему периода, а не расписание конкретных событий."
    )

    return (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Джйотиш · {subtitle}</title>'
        f'{page_style(EXTRA_CSS)}</head><body><div class="wrap">'
        f'{print_bar_html()}'
        f'<h1>{heading}</h1><div class="sub">{subtitle}</div>'
        f'{warning_html}'
        f'<div class="cols">{lagna_html}'
        f'<div class="card"><h2>Аянамша на дату</h2>'
        f'<div class="big">{esc(data.get("аянамша_на_дату", "—"))}°</div>'
        f'<p class="muted">{esc(data.get("конфигурация", ""))}</p></div>'
        f'</div>'
        f'<div class="card"><h2>Девять грах</h2>{_planets_table(planets, has_houses)}</div>'
        f'<div class="card"><h2>Чара-караки (Джаймини)</h2>{_karakas_html(data.get("чара_караки_джаймини", {}))}</div>'
        f'<div class="card"><h2>Панчанга</h2>{panchanga_html}</div>'
        f'<div class="card"><h2>Вимшоттари-даша</h2>{_vimshottari_html(data.get("вимшоттари", {}))}</div>'
        f'{note_html}'
        f'<footer>{esc(footer)}</footer>'
        f'</div></body></html>'
    )
