"""Builds a printable HTML page from bazi_service.compute()'s JSON."""
from app.render.common import esc, page_style, print_bar_html

PILLAR_ORDER = ["год", "месяц", "день", "час"]
PILLAR_TITLES = {"год": "Год", "месяц": "Месяц", "день": "День", "час": "Час"}

EXTRA_CSS = """
.pillars { display: flex; flex-wrap: wrap; gap: 16px; }
.pillar { flex: 1 1 220px; border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
.pillar.day { border-color: var(--accent); }
.pillar .glyphs { font-size: 30px; font-weight: 650; margin-bottom: 6px; }
.pillar dl { margin: 8px 0 0; font-size: 12px; }
.pillar dt { color: var(--muted); margin-top: 6px; }
.pillar dd { margin: 0; }
.elements { display: flex; gap: 10px; flex-wrap: wrap; }
.elements .el { flex: 1 1 90px; text-align: center; border: 1px solid var(--line);
                border-radius: 10px; padding: 10px 4px; }
.elements .el .n { font-size: 20px; font-weight: 650; color: var(--accent); }
.boundary-warning { border: 1px solid #d9a441; border-radius: 12px; padding: 14px; margin-top: 14px; }
.boundary-warning h3 { margin: 0 0 6px; font-size: 13px; }
"""


def _alt_hour_html(original: dict, alt: dict) -> str:
    hidden = ", ".join(alt.get("скрытые_стволы", [])) or "—"
    return (
        '<div class="boundary-warning">'
        '<h3>Время рождения — пограничное для столпа часа</h3>'
        '<p class="muted">Момент рождения оказался близко (в пределах 20 минут) к границе, '
        'где двухчасовой интервал меняется на следующий. Если время рождения известно неточно '
        '(округлено, «около», по памяти) — реальный столп часа мог получиться другим. '
        f'Основной вариант выше — {esc(original.get("иероглифы", ""))}. Второй вариант — если бы '
        'момент рождения был на 20–45 минут раньше или позже:</p>'
        f'<p><b>{esc(alt["иероглифы"])}</b> — {esc(alt["небесный_ствол"])}, '
        f'{esc(alt["земная_ветвь"])} ({esc(alt["животное"])}). '
        f'Скрытые стволы: {esc(hidden)}.</p>'
        '</div>'
    )


def _pillar_html(name: str, data: dict, is_day: bool) -> str:
    hidden = ", ".join(data.get("скрытые_стволы", [])) or "—"
    gods = data.get("десять_богов_ветвь")
    gods_html = ", ".join(gods) if isinstance(gods, list) else (gods or "—")
    return (
        f'<div class="pillar{" day" if is_day else ""}">'
        f'<div class="muted">{esc(PILLAR_TITLES.get(name, name))}</div>'
        f'<div class="glyphs">{esc(data["иероглифы"])}</div>'
        f'<dl>'
        f'<dt>Ствол</dt><dd>{esc(data["небесный_ствол"])} ({esc(data["стихия_ствола"])}, {esc(data["инь_ян_ствола"])})</dd>'
        f'<dt>Ветвь</dt><dd>{esc(data["земная_ветвь"])} — {esc(data["животное"])} ({esc(data["стихия_ветви"])})</dd>'
        f'<dt>Скрытые стволы</dt><dd>{esc(hidden)}</dd>'
        f'<dt>Десять богов (ствол)</dt><dd>{esc(data.get("десять_богов_ствол", "—"))}</dd>'
        f'<dt>Десять богов (ветвь)</dt><dd>{esc(gods_html)}</dd>'
        f'</dl></div>'
    )


def _dayun_html(dayun: list) -> str:
    if not dayun:
        return '<p class="muted">Такты удачи не рассчитаны (не указан пол или дата вне диапазона).</p>'
    rows = "".join(
        f'<tr><td>с {item["возраст_начала"]} лет ({item["год_начала"]})</td>'
        f'<td>{esc(item.get("столп", "—"))}</td>'
        f'<td>{esc(item.get("ствол", ""))}</td><td>{esc(item.get("ветвь", ""))}</td></tr>'
        for item in dayun
    )
    return f'<table><tr><th>Период</th><th>Столп</th><th>Ствол</th><th>Ветвь</th></tr>{rows}</table>'


def _stars_html(stars: dict) -> str:
    parts = []
    for key, title in (("персиковый_цвет_таохуа", "Персиковый цвет (таохуа)"),
                        ("небесный_конь_има", "Небесный конь (има)")):
        block = stars.get(key, {})
        items = "".join(
            f'<li>{esc(basis)}: {esc(info["ветвь"])} — '
            f'{"<b>есть в карте</b>" if info["в_карте"] else "нет в карте"}</li>'
            for basis, info in block.items()
        )
        parts.append(f'<div class="pill"><h3>{esc(title)}</h3><ul>{items}</ul></div>')
    nobles = stars.get("дворянин_тяньи", {})
    in_chart = nobles.get("в_карте") or []
    parts.append(
        f'<div class="pill"><h3>Дворянин (тяньи)</h3>'
        f'<p>Ветви-покровители: {esc(", ".join(nobles.get("ветви", [])))}</p>'
        f'<p>{"<b>В карте есть: " + esc(", ".join(in_chart)) + "</b>" if in_chart else "в карте нет"}</p></div>'
    )
    return f'<div class="grid">{"".join(parts)}</div>'


def build_page(data: dict, person: str = "") -> str:
    heading = esc(person) if person else "Ба-цзы"
    subtitle = f'{esc(data["дата_григорианская"])} · {esc(data["животное_года"])}'

    pillars_html = '<div class="pillars">' + "".join(
        _pillar_html(name, data["четыре_столпа"][name], name == "день")
        for name in PILLAR_ORDER if name in data["четыре_столпа"]
    ) + "</div>"

    alt_pillar = data.get("альтернативный_столп_часа")
    if alt_pillar:
        pillars_html += _alt_hour_html(data["четыре_столпа"].get("час", {}), alt_pillar)

    elements = data["баланс_стихий"]
    elements_html = '<div class="elements">' + "".join(
        f'<div class="el"><div class="n">{value:g}</div><div class="muted">{esc(name)}</div></div>'
        for name, value in elements.items()
    ) + "</div>"

    nayin_html = "<table><tr><th>Столп</th><th>На-инь</th></tr>" + "".join(
        f'<tr><td>{esc(PILLAR_TITLES.get(name, name))}</td><td>{esc(value)}</td></tr>'
        for name, value in data.get("на_инь", {}).items()
    ) + "</table>"

    kong_wang = data.get("неочевидное", {}).get("пустоты_кун_ван", {})
    kw_in_chart = kong_wang.get("пустые_ветви_в_карте")
    kw_html = (
        f'<p><b>Пустые ветви (кун-ван):</b> {esc(", ".join(kong_wang.get("пустые_ветви", [])))}</p>'
        f'<p>{"<b>Задеты в карте: " + esc(", ".join(kw_in_chart)) + "</b>" if isinstance(kw_in_chart, list) and kw_in_chart else esc(kw_in_chart) if isinstance(kw_in_chart, str) else "пустоты не задеты"}</p>'
    )

    day_master = data["хозяин_дня"]
    note_html = f'<p class="note">{esc(data["примечание"])}</p>' if data.get("примечание") else ""

    footer = (
        "Ба-цзы — традиционная символическая система для саморефлексии, а не наука "
        "и не замена решений человека. Столкновения и напряжения в карте — это зоны "
        "роста с инструкцией, а не приговор."
    )

    return (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Ба-цзы · {esc(data["дата_григорианская"])}</title>'
        f'{page_style(EXTRA_CSS)}</head><body><div class="wrap">'
        f'{print_bar_html()}'
        f'<h1>{heading}</h1><div class="sub">{subtitle}</div>'
        f'<div class="card"><h2>Хозяин дня</h2>'
        f'<div class="big">{esc(day_master["ствол"])}</div>'
        f'<p class="muted">{esc(day_master["стихия"])}, {esc(day_master["инь_ян"])} — '
        f'лунная дата {esc(data.get("дата_лунная", ""))}</p></div>'
        f'<div class="card"><h2>Четыре столпа</h2>{pillars_html}</div>'
        f'<div class="cols">'
        f'<div class="card"><h2>Баланс стихий</h2>{elements_html}</div>'
        f'<div class="card"><h2>На-инь</h2>{nayin_html}</div>'
        f'</div>'
        f'<div class="card"><h2>Такты удачи (да юнь)</h2>{_dayun_html(data.get("такты_удачи_да_юнь", []))}</div>'
        f'<div class="card"><h2>Неочевидное</h2>{kw_html}{_stars_html(data.get("неочевидное", {}).get("символические_звёзды", {}))}</div>'
        f'<div class="card"><h2>Конвенции расчёта</h2>'
        f'<p class="note">{esc(data.get("конвенции", ""))}</p>'
        f'{note_html}'
        f'</div>'
        f'<footer>{esc(footer)}</footer>'
        f'</div></body></html>'
    )
