"""Builds a printable HTML page from jyotish_service.compute()'s JSON.

Джйотиш полон непереведённого санскрита и незнакомых понятий для человека,
который видит такой разбор впервые — поэтому здесь не просто таблицы с
цифрами, а рядом с каждым блоком объяснение простыми словами: термин →
что это по-человечески → как читать конкретно эти цифры.
"""
from app.render.common import esc, page_style, print_bar_html

PLANET_ORDER = ["Солнце", "Луна", "Марс", "Меркурий", "Юпитер", "Венера", "Сатурн", "Раху", "Кету"]

PLANET_MEANING = {
    "Солнце": "душа, отец, воля, статус",
    "Луна": "ум, эмоции, мать, повседневность",
    "Марс": "энергия, воля к действию, братья, конфликты",
    "Меркурий": "речь, интеллект, торговля, тексты",
    "Юпитер": "мудрость, учителя, дети, достаток, вера",
    "Венера": "любовь, красота, комфорт, искусство, партнёрство",
    "Сатурн": "дисциплина, время, труд, ограничения",
    "Раху": "жажда нового, иностранное, одержимость темой",
    "Кету": "отрешённость, прошлый опыт, интуиция",
}

HOUSE_MEANING = {
    1: "тело, личность, путь", 2: "деньги, речь, семья",
    3: "смелость, братья, навыки", 4: "дом, мать, недвижимость",
    5: "дети, творчество, романы", 6: "болезни, враги, долги, служба",
    7: "брак, партнёрства, публика", 8: "кризисы, трансформации",
    9: "дхарма, учитель, удача, странствия", 10: "карьера, статус, дела",
    11: "доходы, друзья, желания", 12: "потери, изоляция, заграница",
}

EXTRA_CSS = """
.planets td.retro { color: #c0392b; font-weight: 650; }
.dasha-current { border: 1px solid var(--accent); border-radius: 12px; padding: 14px; margin-top: 12px; }
.intro { font-size: 13px; line-height: 1.6; margin: 0 0 12px; }
.intro:last-child { margin-bottom: 0; }
dl.glossary { margin: 0; }
dl.glossary dt { font-weight: 650; margin-top: 10px; }
dl.glossary dt:first-child { margin-top: 0; }
dl.glossary dd { margin: 2px 0 0; color: var(--muted); font-size: 13px; line-height: 1.5; }
.legend-row { font-size: 12px; color: var(--muted); margin-top: 10px; line-height: 1.6; }
"""


def _glossary_html() -> str:
    items = [
        ("Лагна", "знак, который восходил на востоке в момент рождения — «скелет» всей карты: тело, характер, то, как человек в целом идёт по жизни."),
        ("Накшатра", "одна из 27 «лунных стоянок» вдоль зодиака — более тонкий и личный слой, чем просто знак; показывает глубинный психологический почерк."),
        ("Дом (бхава)", "одна из 12 сфер жизни (см. расшифровку под таблицей грах) — то, где именно проявляется энергия планеты."),
        ("Достоинство", "сила планеты в знаке: «экзальтация» — планета на пике силы, «своя обитель» — устойчиво и по-своему, «дебилитация» — ослаблена, тема даётся труднее."),
        ("Ретроградность (R)", "планета движется по знаку «попятно» с точки зрения Земли — символически: пересмотр и внутренняя переработка темы планеты, а не её обычное прямое движение."),
        ("Даша", "система периодов жизни: планеты по очереди «управляют» отрезками времени и окрашивают их своей темой (расшифровка — в блоке Вимшоттари ниже)."),
    ]
    rows = "".join(f"<dt>{esc(term)}</dt><dd>{esc(desc)}</dd>" for term, desc in items)
    return f'<dl class="glossary">{rows}</dl>'


def _planets_table(planets: dict, has_houses: bool) -> str:
    header = "<th>Граха</th><th>Отвечает за</th><th>Положение</th><th>Накшатра</th><th>Достоинство</th>"
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
            f'<td class="muted">{esc(PLANET_MEANING.get(name, ""))}</td>'
            f'<td>{esc(p["положение"])}</td>'
            f'<td>{esc(p["накшатра"])}</td>'
            f'<td>{esc(p.get("достоинство", "") or "—")}</td>'
        )
        if has_houses:
            row += f'<td>{esc(p.get("дом", "—"))}</td>'
        row += "</tr>"
        rows.append(row)
    table = f'<table><tr>{header}</tr>{"".join(rows)}</table>'
    if has_houses:
        legend = " · ".join(f"{n} — {esc(m)}" for n, m in HOUSE_MEANING.items())
        table += f'<p class="legend-row"><b>Что означает номер дома:</b> {legend}</p>'
    return table


def _karakas_html(karakas: dict) -> str:
    rows = "".join(
        f'<tr><td>{esc(name)}</td><td>{esc(value)}</td></tr>' for name, value in karakas.items()
    )
    return f'<table><tr><th>Каракака</th><th>Граха</th></tr>{rows}</table>'


def _vimshottari_html(vim: dict) -> str:
    current = vim.get("текущая", {})
    current_html = ""
    if current.get("маха_даша"):
        theme = PLANET_MEANING.get(current["маха_даша"], "")
        antar = f' → антар-даша {esc(current["антар_даша"])} (до {esc(current["антар_до"])})' if current.get("антар_даша") else ""
        current_html = (
            f'<div class="dasha-current"><b>Сейчас идёт:</b> маха-даша {esc(current["маха_даша"])} '
            f'— тема периода: {esc(theme)} (до {esc(current["до"])}){antar}</div>'
        )
    rows = "".join(
        f'<tr><td>{esc(p["планета"])}</td><td class="muted">{esc(PLANET_MEANING.get(p["планета"], ""))}</td>'
        f'<td>{esc(p["с"])}</td><td>{esc(p["по"])}</td></tr>'
        for p in vim.get("маха_даши", [])
    )
    table = f'<table><tr><th>Планета</th><th>Тема периода</th><th>С</th><th>По</th></tr>{rows}</table>'
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
            f'<p class="intro">Лагна — знак, который восходил на востоке в момент рождения: '
            'скелет всей карты, то, с чем человек идёт по жизни и как выглядит для мира.</p>'
            f'<p class="muted">Накшатра: {esc(lagna["накшатра"])} · '
            f'навамша-лагна: {esc(lagna["навамша_лагна_D9"])}</p></div>'
        )
    elif data.get("примечание_лагна"):
        lagna_html = (
            f'<div class="card"><h2>Лагна</h2>'
            f'<p class="intro">Лагна — знак, восходивший на востоке в момент рождения, скелет всей карты. '
            'Без точного времени рождения её не посчитать.</p>'
            f'<p class="note">{esc(data["примечание_лагна"])}</p></div>'
        )

    warning_html = ""
    if data.get("предупреждение_лагна"):
        warning_html = f'<div class="card"><h2>Внимание</h2><p class="note">{esc(data["предупреждение_лагна"])}</p></div>'

    panchanga = data.get("панчанга", {})
    panchanga_html = ""
    if panchanga:
        panchanga_html = (
            '<p class="intro">Панчанга — «календарь дня» по традиционной астрологии: не про личность, '
            'а про общий фон именно этих суток.</p>'
            '<div class="grid">'
            f'<div class="pill"><h3>Титхи</h3><p class="muted">лунный день — одна из 30 фаз Луны, задаёт общий тон дня</p>'
            f'<p>{esc(panchanga.get("титхи", "—"))}</p></div>'
            f'<div class="pill"><h3>Вара (день недели)</h3><p class="muted">управитель дня, как в западной астрологии</p>'
            f'<p>{esc(panchanga.get("вара", "—"))}</p></div>'
            f'<div class="pill"><h3>Накшатра Луны</h3><p class="muted">лунная стоянка дня — эмоциональный фон суток</p>'
            f'<p>{esc(panchanga.get("накшатра_луны", "—"))}</p></div>'
            '</div>'
        )

    note_html = f'<p class="note">{esc(data["примечание"])}</p>' if data.get("примечание") else ""

    conventions_html = (
        f'<p class="note">{esc(data.get("конфигурация", ""))} · аянамша на дату рождения: '
        f'{esc(data.get("аянамша_на_дату", "—"))}° (поправка между тропическим и сидерическим зодиаком, '
        'без неё Джйотиш и западная астрология давали бы разные знаки для одной даты).</p>'
    )

    footer = (
        "Джйотиш — традиционная символическая система, не наука и не замена решений "
        "человека. Даша задаёт общую тему периода, а не расписание конкретных событий."
    )
    glossary_html = _glossary_html()

    return (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>Джйотиш · {subtitle}</title>'
        f'{page_style(EXTRA_CSS)}</head><body><div class="wrap">'
        f'{print_bar_html()}'
        f'<h1>{heading}</h1><div class="sub">{subtitle}</div>'
        f'<div class="card"><h2>Как читать этот разбор</h2>'
        f'<p class="intro">Джйотиш — ведическая (индийская) астрология: расчёт по эфемеридам планет '
        'на момент рождения, а не гадание по знаку. Ниже — глоссарий терминов, которые дальше '
        f'встретятся в таблицах.</p>{glossary_html}</div>'
        f'{warning_html}'
        f'{lagna_html}'
        f'<div class="card"><h2>Девять грах</h2>'
        f'<p class="intro">Граха — планета в этой системе (включая две теневые точки — Раху и Кету). '
        'Ниже — где какая планета оказалась на момент рождения и в какой она силе.</p>'
        f'{_planets_table(planets, has_houses)}</div>'
        f'<div class="card"><h2>Чара-караки (Джаймини)</h2>'
        f'<p class="intro">Дополнительный слой: планеты распределены по ролям в зависимости от градуса '
        'в своём знаке. Главные две — <b>Атмакарака</b> (главная планета души, её тема — центральный '
        'урок жизни) и <b>Даракарака</b> (сигнификатор партнёра/супруга).</p>'
        f'{_karakas_html(data.get("чара_караки_джаймини", {}))}</div>'
        f'<div class="card"><h2>Панчанга</h2>{panchanga_html}</div>'
        f'<div class="card"><h2>Вимшоттари-даша</h2>'
        f'<p class="intro">Система периодов жизни: она делится на отрезки, которыми по очереди '
        '«управляют» 9 планет (полный цикл — 120 лет), отсчёт — от накшатры Луны при рождении. '
        'Каждый период окрашен темой своей планеты — это не расписание событий, а общая глава жизни.</p>'
        f'{_vimshottari_html(data.get("вимшоттари", {}))}</div>'
        f'{note_html}'
        f'<div class="card"><h2>Конвенции расчёта</h2>{conventions_html}</div>'
        f'<footer>{esc(footer)}</footer>'
        f'</div></body></html>'
    )
