#!/usr/bin/env python3
"""
Собирает полную схему матрицы одной HTML-страницей: восьмиконечная звезда с
возрастной шкалой, карта здоровья по чакрам и предназначения.

Использование:
    python render_html.py ДД.ММ.ГГГГ [--out путь.html] [--name Имя] [--child]

Страница самодостаточная (стили внутри, внешних запросов нет) — её можно
открыть в браузере, сохранить или отправить. Все числа берутся из calculate.py,
здесь только оформление: если цифра неверна, чинить нужно расчёт, а не вёрстку.
"""

import argparse
import html
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calculate import calculate, parse_date, require_guide, CHILD_NOTE  # noqa: E402

CENTER = 280.0
RING = 190.0          # радиус основных точек и возрастных отметок
LABEL_RING = 232.0    # радиус подписей возраста

CSS = """
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
body { margin: 0; padding: 28px 20px 48px; background: var(--bg); color: var(--ink);
       font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1120px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; font-weight: 650; }
.sub { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
.cols { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px;
        padding: 18px; flex: 1 1 420px; min-width: 320px; }
.card h2 { font-size: 15px; margin: 0 0 14px; font-weight: 600; letter-spacing: .02em;
           text-transform: uppercase; color: var(--muted); }
svg { width: 100%; height: auto; display: block; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; font-weight: 600; color: var(--muted); font-size: 11px;
     text-transform: uppercase; letter-spacing: .04em; padding: 0 6px 8px; }
td { padding: 7px 6px; border-top: 1px solid var(--line); vertical-align: middle; }
.num { width: 46px; text-align: center; font-weight: 650; border-radius: 7px;
       padding: 5px 0; color: #1c1b22; }
.chakra-name { font-weight: 600; }
.chakra-about { color: var(--muted); font-size: 12px; display: block; margin-top: 2px; }
.arc { color: var(--muted); font-size: 11px; display: block; margin-top: 3px; line-height: 1.45; }
.purposes { display: flex; flex-wrap: wrap; gap: 18px; }
.purpose { flex: 1 1 200px; border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
.purpose .big, .mod .big { font-size: 26px; font-weight: 650; color: var(--accent); line-height: 1.2; }
.purpose .parts { color: var(--muted); font-size: 12px; margin-top: 6px; }
.gap { border-style: dashed; color: var(--muted); }
.note { color: var(--muted); font-size: 12px; line-height: 1.55; margin-top: 14px; }
.mods { display: flex; flex-wrap: wrap; gap: 16px; }
.mod { flex: 1 1 260px; border: 1px solid var(--line); border-radius: 12px; padding: 14px; }
.mod h3 { margin: 0 0 4px; font-size: 14px; font-weight: 650; }
.badge { display: inline-block; font-size: 10px; letter-spacing: .04em; text-transform: uppercase;
         padding: 2px 7px; border-radius: 20px; margin-bottom: 8px; }
.ok { background: #d8f0dd; color: #1f5130; }
.recon { background: #f6e6c9; color: #6b4a12; }
.mod ul { margin: 8px 0 0; padding-left: 16px; font-size: 13px; }
.mod li { margin-bottom: 3px; }
.mod .formula { color: var(--muted); font-size: 11px; margin-top: 8px; line-height: 1.5; }
.what { font-size: 13px; line-height: 1.55; margin: 0 0 12px; }
.mod .verdict { font-size: 13px; line-height: 1.5; margin: 0 0 6px; font-weight: 600; }
.badge { max-width: 100%; white-space: normal; }
footer { color: var(--muted); font-size: 12px; line-height: 1.6; margin-top: 26px;
         border-top: 1px solid var(--line); padding-top: 14px; }
"""


def polar(angle_deg: float, radius: float) -> tuple:
    rad = math.radians(angle_deg)
    return CENTER + radius * math.cos(rad), CENTER - radius * math.sin(rad)


def age_angle(age: float) -> float:
    """0 лет — слева (180°), дальше против часовой: 20 — верх, 40 — право, 60 — низ."""
    return 180.0 - age * 4.5


def circle(x: float, y: float, r: float, value: int, fill: str,
           text_color: str = "#1c1b22", font: int = 15) -> str:
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
        f'stroke="var(--line)" stroke-width="1"/>'
        f'<text x="{x:.1f}" y="{y + font * 0.35:.1f}" text-anchor="middle" '
        f'font-size="{font}" font-weight="650" fill="{text_color}">{value}</text>'
    )


def build_svg(matrix: dict) -> str:
    personal = {key: value["number"] for key, value in matrix["personal_square"].items()}
    family = {key: value["number"] for key, value in matrix["family_square"].items()}
    rows = matrix["chakra_map"]["rows"]

    parts = ['<svg viewBox="0 0 560 560" xmlns="http://www.w3.org/2000/svg" '
             'role="img" aria-label="Схема матрицы судьбы">']

    principal = [(0, personal["A"]), (10, family["F"]), (20, personal["B"]),
                 (30, family["G"]), (40, personal["C"]), (50, family["H"]),
                 (60, personal["D"]), (70, family["K"])]
    coords = {age: polar(age_angle(age), RING) for age, _ in principal}

    # каркас: восьмиугольник по периметру, ромб личного квадрата, прямой родовой
    octagon = " ".join(f"{coords[age][0]:.1f},{coords[age][1]:.1f}" for age, _ in principal)
    diamond = " ".join(f"{coords[age][0]:.1f},{coords[age][1]:.1f}" for age in (0, 20, 40, 60))
    square = " ".join(f"{coords[age][0]:.1f},{coords[age][1]:.1f}" for age in (10, 30, 50, 70))
    parts.append(
        f'<g fill="none" stroke="var(--line)" stroke-width="1.2">'
        f'<polygon points="{octagon}" opacity="0.7"/>'
        f'<polygon points="{diamond}"/><polygon points="{square}"/>'
        f'<line x1="{CENTER - RING}" y1="{CENTER}" x2="{CENTER + RING}" y2="{CENTER}"/>'
        f'<line x1="{CENTER}" y1="{CENTER - RING}" x2="{CENTER}" y2="{CENTER + RING}"/>'
        f'<circle cx="{CENTER}" cy="{CENTER}" r="{RING}" opacity="0.45"/>'
        f'</g>'
    )

    # мелкие отметки возраста каждые 5 лет + подписи
    for step in range(16):
        age = step * 5
        if age % 10 == 0:
            continue
        mark = next(m for m in matrix["age_scale"]["marks"] if m["age"] == float(age))
        x, y = polar(age_angle(age), RING)
        parts.append(circle(x, y, 12, mark["number"], "var(--card)",
                            "var(--ink)", 12))
    for age in range(0, 80, 5):
        lx, ly = polar(age_angle(age), LABEL_RING)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="10" '
            f'fill="var(--muted)">{age} лет</text>'
        )

    # чакровые точки на осях: каждая половина делится на три, радиусы 0.75/0.5/0.25
    axis = matrix["chakra_map"]["axis_points"]
    neutral = "var(--card)"
    upper_colors = (rows[1]["color"], rows[2]["color"], rows[3]["color"])
    lower_colors = (neutral, rows[5]["color"], neutral)
    for key, (dx, dy), colors in (
            ("вверх_от_центра", (0, -1), upper_colors),
            ("вниз_от_центра", (0, 1), lower_colors),
            ("влево_от_центра", (-1, 0), upper_colors),
            ("вправо_от_центра", (1, 0), lower_colors)):
        for value, fraction, color in zip(axis[key], (0.75, 0.5, 0.25), colors):
            x = CENTER + dx * RING * fraction
            y = CENTER + dy * RING * fraction
            ink = "var(--ink)" if color == neutral else "#1c1b22"
            parts.append(circle(x, y, 13, value, color, ink, 13))

    # основные точки поверх всего
    palette = {0: rows[0]["color"], 20: rows[0]["color"],
               40: rows[6]["color"], 60: rows[6]["color"]}
    for age, value in principal:
        x, y = coords[age]
        parts.append(circle(x, y, 20, value, palette.get(age, "var(--card)"),
                            "var(--ink)" if age % 20 else "#1c1b22", 17))
    parts.append(circle(CENTER, CENTER, 22, personal["E"], rows[4]["color"], "#1c1b22", 18))

    # подписи осей
    axis_labels = (
        ("НЕБО", (CENTER, CENTER - RING - 62)),
        ("НЕБО", (CENTER, CENTER + RING + 62)),
        ("ЗЕМЛЯ", (CENTER - RING - 56, CENTER - 26)),
        ("ЗЕМЛЯ", (CENTER + RING + 56, CENTER - 26)),
    )
    for text, (x, y) in axis_labels:
        parts.append(
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" '
            f'font-weight="650" letter-spacing="1" fill="var(--accent)">{text}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def build_table(matrix: dict) -> str:
    rows = matrix["chakra_map"]["rows"]
    organism = matrix["chakra_map"]["organism"]
    howto = matrix["chakra_map"]["как_читать"]
    cells = [f'<p class="what"><b>Небо</b> — {html.escape(howto["Небо"])}. '
             f'<b>Земля</b> — {html.escape(howto["Земля"])}. '
             f'<b>Ключ</b> — {html.escape(howto["Ключ"])}.</p>',
             '<table><tr><th>Небо</th><th>Земля</th><th>Ключ</th><th>Зона жизни</th></tr>']
    for row in rows:
        cells.append(
            f'<tr>'
            f'<td><div class="num" style="background:{row["color"]}">{row["Небо"]["number"]}</div></td>'
            f'<td><div class="num" style="background:{row["color"]}">{row["Земля"]["number"]}</div></td>'
            f'<td><div class="num" style="background:{row["color"]}">{row["Ключ"]["number"]}</div></td>'
            f'<td><span class="chakra-name">{html.escape(row["зона"])}</span>'
            f'<span class="chakra-about">{html.escape(row["chakra"])} — '
            f'{html.escape(row["about"])}</span>'
            f'<span class="arc">ключ {row["Ключ"]["number"]} — '
            f'{html.escape(row["Ключ"]["значение"])}</span></td>'
            f'</tr>'
        )
    cells.append(
        f'<tr>'
        f'<td><div class="num" style="background:#d1d5db">{organism["Небо"]["number"]}</div></td>'
        f'<td><div class="num" style="background:#d1d5db">{organism["Земля"]["number"]}</div></td>'
        f'<td><div class="num" style="background:#d1d5db">{organism["Ключ"]["number"]}</div></td>'
        f'<td><span class="chakra-name">{html.escape(organism["зона"])}</span>'
        f'<span class="chakra-about">{html.escape(organism["about"])}</span>'
        f'<span class="arc">ключ {organism["Ключ"]["number"]} — '
        f'{html.escape(organism["Ключ"]["значение"])}</span></td>'
        f'</tr></table>'
    )
    cells.append(f'<p class="note">{html.escape(matrix["chakra_map"]["note"])}</p>')
    return "".join(cells)


def build_purposes(matrix: dict) -> str:
    data = matrix["purposes"]
    personal, ancestral, spiritual = data["личное"], data["родовое"], data["духовное"]

    def card(title: str, value, parts_text: str, arcanum: str = "",
             sense: str = "") -> str:
        big = value if value is not None else "—"
        arc = (f'<div class="parts"><b>{html.escape(arcanum)}</b>'
               + (f' — {html.escape(sense)}' if sense else "")
               + '</div>') if arcanum else ""
        return (f'<div class="purpose{"" if value is not None else " gap"}">'
                f'<div class="chakra-about">{html.escape(title)}</div>'
                f'<div class="big">{big}</div>{arc}'
                f'<div class="parts">{html.escape(parts_text)}</div></div>')

    return (
        '<div class="purposes">'
        + card("Личное предназначение", personal["итог"]["number"],
               f'Небо {personal["Небо"]["number"]} + Земля {personal["Земля"]["number"]}',
               personal["итог"]["arcanum"], personal["итог"]["значение"])
        + card("Родовое предназначение", ancestral["итог"]["number"],
               f'отец {ancestral["отец"]["number"]} + мать {ancestral["мать"]["number"]}',
               ancestral["итог"]["arcanum"], ancestral["итог"]["значение"])
        + card("Духовное предназначение", spiritual["итог"]["number"],
               "личное + родовое", spiritual["итог"]["arcanum"],
               spiritual["итог"]["значение"])
        + card("Высшее духовное", None, "формула не подтверждена — не считается")
        + '</div>'
        + f'<p class="note">{html.escape(data["note"])}</p>'
    )


def build_modules(matrix: dict) -> str:
    data = matrix["extra_modules"]

    def shell(title: str, block: dict, body: str) -> str:
        status = block["статус"]
        css = "ok" if status == "проверено" else "recon"
        hint = ("считается однозначно" if status == "проверено"
                else "у разных школ формулы расходятся — это один из вариантов")
        return (f'<div class="mod"><h3>{html.escape(title)}</h3>'
                f'<span class="badge {css}">{html.escape(status)}: {html.escape(hint)}</span>'
                f'<p class="what">{html.escape(block.get("что_это", ""))}</p>'
                f'{body}'
                f'<div class="formula">как считается: {html.escape(block["формула"])}</div>'
                f'</div>')

    def points(block: dict) -> str:
        return "<ul>" + "".join(
            f'<li><b>{point["number"]}</b> {html.escape(point["arcanum"])} — '
            f'{html.escape(point["роль"])}'
            f'<span class="arc">{html.escape(point["значение"])}</span></li>'
            for point in block["точки"]) + "</ul>"

    cards = []
    for title, key in (("Денежный канал", "денежный канал"),
                       ("Линия отношений", "любовный треугольник")):
        if key in data:  # в детской матрице этих модулей нет
            cards.append(shell(title, data[key], points(data[key])))

    talents_block = data["зона талантов"]
    talents_body = "<ul>" + "".join(
        f'<li><b>{item["number"]}</b> {html.escape(item["arcanum"])} — '
        f'{html.escape(item["роль"])}'
        f'<span class="arc">{html.escape(item["значение"])}</span></li>'
        for item in talents_block["личные"]) + "</ul>"
    for line, items in talents_block["родовые"].items():
        listed = ", ".join(f'{item["number"]} ({item["arcanum"]})' for item in items)
        talents_body += f'<div class="formula">{html.escape(line)}: {html.escape(listed)}</div>'
    cards.append(shell("Зона талантов", talents_block, talents_body))

    year = data["личный год"]
    cards.append(shell("Личный год", year,
                       f'<div class="big">{year["number"]}</div>'
                       f'<div class="parts"><b>{html.escape(year["arcanum"])}</b> — '
                       f'{html.escape(year["значение"])}</div>'
                       f'<div class="parts">в плюсе: {html.escape(year["в плюсе"])}</div>'
                       f'<div class="parts">в минусе: {html.escape(year["в минусе"])}</div>'
                       f'<div class="parts">{html.escape(year["период"])}</div>'))

    for title, key in (("Код миллионера 5-14-19", "код миллионера"),
                       ("Золотой дар 15-4-19", "золотой дар")):
        block = data[key]
        body = f'<p class="verdict">{html.escape(block["итог"])}</p><ul>'
        for item in block["где_стоят_эти_арканы"]:
            body += (f'<li><b>{item["number"]}</b> {html.escape(item["arcanum"])} — '
                     f'{html.escape(", ".join(item["линии"]))}</li>')
        body += "</ul>"
        cards.append(shell(title, block, body))

    notes = [data["note"]]
    if "не считается для ребёнка" in data:
        notes.insert(0, data["не считается для ребёнка"])
    return (f'<div class="mods">{"".join(cards)}</div>'
            + "".join(f'<p class="note">{html.escape(text)}</p>' for text in notes))


def build_stages(matrix: dict) -> str:
    now = matrix["age_scale"]["now"]
    current = now.get("возраст")
    rows = ['<table><tr><th>Период</th><th>Аркан</th><th>Тема этапа</th></tr>']
    for stage in matrix["age_scale"]["по_десятилетиям"]:
        start = int(stage["период"].split("–")[0])
        active = current is not None and start <= current < start + 10
        mark = ' style="font-weight:650"' if active else ""
        label = stage["период"] + (" · сейчас" if active else "")
        rows.append(
            f'<tr{mark}><td>{html.escape(label)}</td>'
            f'<td><b>{stage["number"]}</b> {html.escape(stage["arcanum"])}</td>'
            f'<td>{html.escape(stage["значение"])}'
            f'<span class="arc">в плюсе: {html.escape(stage["в плюсе"])}</span>'
            f'<span class="arc">в минусе: {html.escape(stage["в минусе"])}</span></td></tr>'
        )
    rows.append("</table>")
    return "".join(rows) + f'<p class="note">{html.escape(matrix["age_scale"]["как_читать"])}</p>'


def build_page(matrix: dict, person: str, child: bool) -> str:
    now = matrix["age_scale"]["now"]
    age_line = (f'возраст {now["возраст"]} — активна отметка {now["отметка"]:g} лет: '
                f'{now["number"]} ({now["arcanum"]})') if "возраст" in now else now.get("note", "")
    heading = html.escape(person) if person else matrix["input_date"]
    subtitle = f'{matrix["input_date"]} · {age_line}' if person else age_line

    footer = (
        "Матрица судьбы — эзотерический инструмент для саморефлексии, а не наука, "
        "не медицина и не финансовая консультация. Числа описывают темы и энергии, "
        "а не диагнозы, события или предопределённые исходы."
    )
    if child:
        footer = CHILD_NOTE + " " + footer

    return (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Матрица судьбы · {html.escape(matrix["input_date"])}</title>'
        f'<style>{CSS}</style></head><body><div class="wrap">'
        f'<h1>{heading}</h1><div class="sub">{html.escape(subtitle)}</div>'
        f'<div class="cols">'
        f'<div class="card"><h2>Схема матрицы</h2>{build_svg(matrix)}</div>'
        f'<div class="card"><h2>Карта здоровья</h2>{build_table(matrix)}</div>'
        f'</div>'
        f'<div class="card" style="margin-top:24px"><h2>Этапы жизни</h2>'
        f'{build_stages(matrix)}</div>'
        f'<div class="card" style="margin-top:24px"><h2>Предназначения</h2>'
        f'{build_purposes(matrix)}</div>'
        f'<div class="card" style="margin-top:24px"><h2>Дополнительные модули</h2>'
        f'{build_modules(matrix)}</div>'
        f'<footer>{html.escape(footer)}</footer>'
        f'</div></body></html>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML-схема матрицы судьбы.")
    parser.add_argument("date", help="дата рождения, ДД.ММ.ГГГГ")
    parser.add_argument("--out", help="куда сохранить (по умолчанию matrix-ДАТА.html рядом)")
    parser.add_argument("--name", default="", help="имя для заголовка страницы")
    parser.add_argument("--child", action="store_true", help="детская матрица: мягкая рамка")
    parser.add_argument("--allow-missing-guide", action="store_true",
                        help="собрать страницу без справочника значений (трактовки будут пустыми)")
    args = parser.parse_args()

    # Та же проверка, что и в расчёте: без справочника страница собирается,
    # выглядит готовой и молча теряет все трактовки.
    guide_code = require_guide(args.allow_missing_guide)
    if guide_code:
        return guide_code

    try:
        day, month, year = parse_date(args.date)
    except ValueError as exc:
        print(f"Ошибка: {exc}. Переспроси дату у пользователя, не досчитывай наугад.",
              file=sys.stderr)
        return 1

    matrix = calculate(day, month, year, child=args.child)
    out = Path(args.out) if args.out else Path(f"matrix-{day:02d}.{month:02d}.{year}.html")
    out.write_text(build_page(matrix, args.name, args.child), encoding="utf-8")
    print(out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
