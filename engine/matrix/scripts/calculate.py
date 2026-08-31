#!/usr/bin/env python3
"""
Детерминированный расчёт точек Матрицы судьбы по дате рождения.

Использование:
    python calculate.py ДД.ММ.ГГГГ                      # обычный разбор
    python calculate.py ДД.ММ.ГГГГ --child              # детская матрица
    python calculate.py ДД.ММ.ГГГГ --partner ДД.ММ.ГГГГ # совместимость двух людей

Разделители в дате могут быть любыми из «. / -»; формат ГГГГ-ММ-ДД тоже понимается.

Печатает JSON: числа точек, названия арканов, роль каждой точки и след
редукции (как именно получилось число). Используй скрипт вместо счёта в уме —
на длинных суммах устный счёт ошибается, а разбор строится поверх этих чисел,
так что одна арифметическая ошибка портит весь ответ.
"""

import argparse
import json
import re
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

ARCANA = {
    1: "Маг",
    2: "Верховная Жрица",
    3: "Императрица",
    4: "Император",
    5: "Иерофант",
    6: "Влюблённые",
    7: "Колесница",
    8: "Справедливость",
    9: "Отшельник",
    10: "Колесо Фортуны",
    11: "Сила",
    12: "Повешенный",
    13: "Смерть",
    14: "Умеренность",
    15: "Дьявол",
    16: "Башня",
    17: "Звезда",
    18: "Луна",
    19: "Солнце",
    20: "Суд",
    21: "Мир",
    22: "Шут",
}

ROLES = {
    "A": "портрет личности, характер",
    "B": "таланты, эмоциональная природа",
    "C": "кармическая задача жизни",
    "D": "кармическое число: багаж прошлого опыта, автоматические паттерны",
    "E": "суть личности, зона комфорта",
    "F": "родовая программа (линия A+B)",
    "G": "родовая программа (линия B+C)",
    "H": "родовая программа (линия C+D)",
    "K": "родовая программа (линия D+A)",
    "karmic_total": "итоговое число матрицы: сводная тема всей жизни "
                    "(не путать с точкой D, которую в методе зовут кармическим числом)",
}

CHILD_NOTE = (
    "Детская матрица: числа считаются так же, как у взрослого, но трактовать их "
    "нужно только через позитивный полюс и в терминах «на что опираться в воспитании». "
    "Тяжёлые арканы (13 Смерть, 15 Дьявол, 16 Башня, 18 Луна) не подавай ребёнку как "
    "диагноз или ярлык."
)

COMPATIBILITY_NOTE = (
    "Это две отдельные матрицы, положенные рядом, а не одна «матрица пары». "
    "Описывай, как энергии взаимодействуют (точка E у каждого — что человек несёт в "
    "контакт; G и H — родовые программы про близость), но не выдавай вердикт "
    "«подходите / не подходите»."
)


GUIDE_PATH = Path(__file__).resolve().parent.parent / "references" / "arcana-guide.md"

ASPECTS = ("тема", "плюс", "минус", "здоровье", "финансы", "отношения", "предназначение")


@lru_cache(maxsize=1)
def arcana_meanings() -> dict:
    """Достаёт значения арканов из справочника, чтобы не дублировать их в коде.

    Один источник правды: правишь `references/arcana-guide.md` — меняется и вывод
    скрипта. Если файла нет, расчёт всё равно должен работать, просто без
    пояснений, поэтому здесь мягкий отказ, а не исключение.
    """
    try:
        text = GUIDE_PATH.read_text(encoding="utf-8")
    except OSError:
        return {}

    meanings = {}
    for number, _name, body in re.findall(r"### (\d+)\. ([^\n]+)\n(.*?)(?=\n### |\Z)",
                                          text, re.S):
        entry = {}
        for field in ("Тема", "Плюс", "Минус"):
            found = re.search(rf"\*\*{field}:\*\* *([^\n]+)", body)
            if found:
                entry[field.lower()] = found.group(1).strip().rstrip(".")
        for bullet in ("Здоровье", "Финансы", "Отношения", "Предназначение"):
            found = re.search(rf"^- {bullet}: *([^\n]+)", body, re.M)
            if found:
                entry[bullet.lower()] = found.group(1).strip().rstrip(".")
        meanings[int(number)] = entry
    return meanings


def meaning(number: int, aspect: str) -> str:
    """Значение аркана в нужном разрезе: тема, плюс, минус или сфера жизни."""
    return arcana_meanings().get(number, {}).get(aspect, "")


def guide_problems() -> list:
    """Что не так со справочником значений.

    Справочник — единственный источник смысла в этом скилле. Без него расчёт
    выдаёт номера арканов с пустыми трактовками, и это выглядит как успешная
    работа: код возврата 0, полный JSON. Агент в такой ситуации либо сочинит
    трактовку сам (что SKILL.md прямо запрещает), либо отдаст человеку пустой
    разбор. Поэтому пустой или неполный справочник — это ошибка, а не мелочь.
    """
    problems = []
    if not GUIDE_PATH.exists():
        return [f"справочник не найден: {GUIDE_PATH}"]

    meanings = arcana_meanings()
    if not meanings:
        return [f"справочник не читается или пуст: {GUIDE_PATH}"]

    missing = [n for n in range(1, 23) if n not in meanings]
    if missing:
        problems.append(
            "в справочнике нет арканов: " + ", ".join(map(str, missing))
            + " (частая причина — опечатка в заголовке, ожидается формат «### 15. Название»)")

    # Без «темы» разбор говорить не о чем, поэтому проверяем именно её.
    hollow = [n for n, entry in sorted(meanings.items()) if not entry.get("тема")]
    if hollow:
        problems.append("у арканов пустая «Тема»: " + ", ".join(map(str, hollow)))

    return problems


def require_guide(allow_missing: bool) -> int:
    """Проверяет справочник перед расчётом. Возвращает код возврата для main()."""
    problems = guide_problems()
    if not problems:
        return 0

    where = "Предупреждение" if allow_missing else "Ошибка"
    print(f"{where}: справочник значений неисправен.", file=sys.stderr)
    for line in problems:
        print(f"  — {line}", file=sys.stderr)
    if allow_missing:
        print("  Расчёт продолжен по флагу --allow-missing-guide: числа будут верными, "
              "трактовки пустыми. Не выдумывай их — скажи пользователю, что справочник недоступен.",
              file=sys.stderr)
        return 0
    print("  Расчёт остановлен: без трактовок разбор делать нечем. "
          "Почини справочник или запусти с --allow-missing-guide, если нужны только числа.",
          file=sys.stderr)
    return 1


def read(number: int, aspect: str, role: str) -> dict:
    """Позиция модуля: число, аркан, за что отвечает и что это значит именно здесь."""
    return {
        "роль": role,
        "number": number,
        "arcanum": ARCANA[number],
        "значение": meaning(number, aspect),
    }


def reduce_to_22(n: int) -> int:
    """Сводит число к диапазону 1-22 через сумму цифр, пока не влезет."""
    while n > 22:
        n = sum(int(d) for d in str(n))
    return n


def reduce_with_trace(n: int) -> tuple:
    """Как reduce_to_22, но возвращает ещё и строку-след вида '23 → 2+3 = 5'."""
    steps = [str(n)]
    while n > 22:
        digits = [int(d) for d in str(n)]
        n = sum(digits)
        steps.append("+".join(str(d) for d in digits) + f" = {n}")
    return n, " → ".join(steps)


def point(value: int, key: str, trace: str) -> dict:
    return {
        "number": value,
        "arcanum": ARCANA[value],
        "role": ROLES[key],
        "тема": meaning(value, "тема"),
        "плюс": meaning(value, "плюс"),
        "минус": meaning(value, "минус"),
        "how": trace,
    }


def parse_date(text: str) -> tuple:
    """Разбирает дату и проверяет, что она реально существует в календаре."""
    cleaned = text.strip().replace("/", ".").replace("-", ".")
    parts = [p for p in cleaned.split(".") if p]
    if len(parts) != 3:
        raise ValueError(f"не удалось разобрать дату '{text}', ожидается ДД.ММ.ГГГГ")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"в дате '{text}' есть нечисловые части")

    if len(parts[0]) == 4:  # ГГГГ-ММ-ДД
        year, month, day = nums
    else:
        day, month, year = nums

    if year < 1000:
        raise ValueError(f"год '{year}' записан не полностью — нужен год из четырёх цифр")
    try:
        parsed = date(year, month, day)  # ловит 31.02, 30.02, 32-е число и т.п.
    except ValueError:
        raise ValueError(f"такой даты не существует в календаре: {day:02d}.{month:02d}.{year}")

    if parsed > date.today():
        raise ValueError(
            f"дата {day:02d}.{month:02d}.{year} ещё не наступила — это почти всегда опечатка в годе"
        )

    return day, month, year


def calculate(day: int, month: int, year: int, child: bool = False) -> dict:
    a, a_trace = reduce_with_trace(day)
    b, b_trace = month, f"{month} (месяц, редукция не нужна)"
    c, c_tail = reduce_with_trace(sum(int(d) for d in str(year)))
    c_trace = f"{'+'.join(str(year))} = {c_tail}"
    d, d_trace = reduce_with_trace(a + b + c)
    d_trace = f"A+B+C = {a}+{b}+{c} = {d_trace}"
    e, e_trace = reduce_with_trace(a + b + c + d)
    e_trace = f"A+B+C+D = {a}+{b}+{c}+{d} = {e_trace}"

    f, f_trace = reduce_with_trace(a + b)
    f_trace = f"A+B = {a}+{b} = {f_trace}"
    g, g_trace = reduce_with_trace(b + c)
    g_trace = f"B+C = {b}+{c} = {g_trace}"
    h, h_trace = reduce_with_trace(c + d)
    h_trace = f"C+D = {c}+{d} = {h_trace}"
    k, k_trace = reduce_with_trace(d + a)
    k_trace = f"D+A = {d}+{a} = {k_trace}"

    total, total_trace = reduce_with_trace(a + b + c + d + e + f + g + h + k)
    total_trace = f"сумма девяти точек = {total_trace}"

    scale = age_scale(a, b, c, d)
    age = age_today(day, month, year)

    result = {
        "input_date": f"{day:02d}.{month:02d}.{year}",
        "personal_square": {
            "A": point(a, "A", a_trace),
            "B": point(b, "B", b_trace),
            "C": point(c, "C", c_trace),
            "D": point(d, "D", d_trace),
            "E": point(e, "E", e_trace),
        },
        "family_square": {
            "F": point(f, "F", f_trace),
            "G": point(g, "G", g_trace),
            "H": point(h, "H", h_trace),
            "K": point(k, "K", k_trace),
        },
        "family_lines": {
            "мужская (F—H)": [f"F: {f} ({ARCANA[f]})", f"H: {h} ({ARCANA[h]})"],
            "женская (K—G)": [f"K: {k} ({ARCANA[k]})", f"G: {g} ({ARCANA[g]})"],
            "note": "Диагонали родового квадрата в методе читаются как две линии рода. "
                    "Если разговор про род, читай линию целиком, а не четыре точки по отдельности.",
        },
        "karmic_total": point(total, "karmic_total", total_trace),
        "chakra_map": chakra_map(a, b, c, d, e),
        "purposes": purposes(a, b, c, d, f, g, h, k),
        "age_scale": {
            "marks": scale,
            "по_десятилетиям": decade_periods(scale),
            "как_читать": "Отметка задаёт тему отрезка, который начинается с неё и "
                          "идёт до следующей. Прошлые периоды разбирать так же уместно, "
                          "как текущий: «в двадцать с небольшим включалась вот эта тема» — "
                          "человек узнаёт свой опыт и начинает понимать метод. Про будущие "
                          "отметки говори как о теме, которая разворачивается, а не о событии.",
            "now": current_period(scale, age),
            "note": "Середины сторон (10, 30, 50, 70 лет) совпадают с углами "
                    "родового квадрата — это не совпадение, а часть построения.",
        },
    }
    result["extra_modules"] = extra_modules(result, day, month, child)
    return result


AXES = {
    "A — C": "как человек входит в мир ↔ ради чего он сюда пришёл; на схеме это"
             " противоположные концы одной оси, и читать их врозь — терять половину смысла",
    "B — D": "чем даётся легко ↔ что тянется из прошлого опыта; частая механика:"
             " талант из B не разворачивается ровно там, где включается автоматизм D",
}


def impossible_in_C(year: int) -> list:
    """Какие арканы в точке C физически недостижимы для рождённых в этом веке."""
    century_start = year - year % 100
    reachable = {
        reduce_to_22(sum(int(d) for d in str(y)))
        for y in range(century_start, century_start + 100)
    }
    return [n for n in range(1, 23) if n not in reachable]


def hidden_layers(matrix: dict, year: int) -> dict:
    """Второй слой чтения: то, что видно только если смотреть на матрицу целиком.

    Всё здесь считается детерминированно, потому что именно эти вещи легче всего
    пропустить, читая точки по одной сверху вниз.
    """
    flat = flat_numbers(matrix)

    by_number = {}
    for key, value in flat.items():
        by_number.setdefault(value, []).append(key)
    repeats = [
        {
            "number": number,
            "arcanum": ARCANA[number],
            "points": points,
            "count": len(points),
        }
        for number, points in sorted(by_number.items())
        if len(points) > 1
    ]

    e_value = flat["E"]
    e_echo = [key for key in ("A", "B", "C", "D") if flat[key] == e_value]

    family = ("F", "G", "H", "K")
    family_twins = [
        {"points": [one, two], "number": flat[one], "arcanum": ARCANA[flat[one]]}
        for i, one in enumerate(family)
        for two in family[i + 1:]
        if flat[one] == flat[two]
    ]

    caveats = [
        "Точка B — это номер месяца, поэтому в ней возможны только арканы 1–12. "
        "Отсутствие «старших» арканов (13–22) в талантах — свойство календаря, "
        "а не особенность конкретного человека, и подавать это как дефицит нельзя.",
        f"У всех, кто родился в {year - year % 100}–{year - year % 100 + 99} годах, "
        "в точке C недостижимы арканы: "
        + ", ".join(f"{n} ({ARCANA[n]})" for n in impossible_in_C(year))
        + ". Их отсутствие тоже ничего не говорит о человеке.",
        "Точек всего девять, а арканов двадцать два — большинство арканов "
        "не выпадает ни у кого. «Отсутствующая энергия» не равна нехватке; "
        "говорить о дефиците по факту невыпадения аркана — распространённая ошибка.",
        "D и E — производные одной и той же суммы A+B+C, поэтому это не два "
        "независимых свидетельства об одном, а два ракурса одного числа. "
        "Совпадение их темы — арифметика, а не «подтверждение».",
    ]
    if year < 1918:
        caveats.append(
            "Дата раньше 1918 года: она может быть записана по старому стилю "
            "(расхождение до 13 дней). Уточни у пользователя, какую дату считать, "
            "и не пересчитывай календарь сам."
        )

    return {
        "repeated_numbers": repeats,
        "repeats_meaning": (
            "Повтор одного числа в нескольких точках — самая заметная вещь в матрице "
            "и одновременно самая пропускаемая: тема звучит громче остальных и "
            "проявляется сразу в нескольких сферах. Чем больше повторов, тем уже "
            "репертуар реакций у человека — это можно назвать вслух."
        ) if repeats else "Повторов нет: темы в матрице распределены равномерно, "
                          "ни одна не перекрывает остальные.",
        "E_repeats_points": e_echo,
        "E_meaning": (
            "Ядро (E) совпадает с точками: "
            + "; ".join(f"{key} — {ROLES[key]}" for key in e_echo)
            + ". Зазора между сутью и этими гранями почти нет — одна и та же тема "
            "звучит и как ядро, и как эти стороны жизни. Она становится "
            "доминирующей во всём разборе, и её стоит поставить в центр ответа, "
            "а не упоминать наравне с остальными."
        ) if e_echo else (
            "E не совпадает ни с одной точкой личного квадрата — ядро отличается от "
            "всех «фасадов», и разрыв между тем, каким человека видят, и тем, какой "
            "он внутри, стоит проговорить."
        ),
        "family_line_twins": family_twins,
        "axes": AXES,
        "structural_caveats": caveats,
    }


CHAKRAS = [
    ("Смысл и вдохновение", "Сахасрара",
     "макушка: чем человек наполняется, ради чего вообще", "#a78bfa"),
    ("Мысли и интуиция", "Аджна",
     "лоб, «третий глаз»: как человек думает, что замечает, чему доверяет", "#818cf8"),
    ("Голос и самовыражение", "Вишудха",
     "горло: как говорит о себе и что оставляет невысказанным", "#38bdf8"),
    ("Чувства и близость", "Анахата",
     "сердце, грудная клетка: как привязывается, чего боится в близости", "#4ade80"),
    ("Воля и энергия", "Манипура",
     "живот, центр силы: как действует, откуда берёт напор", "#facc15"),
    ("Желания и удовольствие", "Свадхистана",
     "низ живота: чего хочет, как отдыхает и восстанавливается", "#fb923c"),
    ("Опора и род", "Муладхара",
     "копчик, корни: на что опирается, что досталось от семьи", "#f87171"),
]

HEALTH_NOTE = (
    "«Карта здоровья» — название, принятое в методе, но это не медицинская "
    "диагностика: числа говорят об энергии и отношении к телу, а не о болезнях. "
    "Никаких диагнозов, прогнозов и рекомендаций по лечению по этой таблице не давай."
)

HEALTH_HOWTO = {
    "Небо": "внутренняя, психологическая сторона зоны: как человек в ней думает и чувствует",
    "Земля": "внешняя, телесная и практическая сторона: как это проявляется в теле, "
             "в быту, в поступках",
    "Ключ": "что складывается на стыке этих двух — итог по зоне и самая рабочая "
            "строка для разговора",
    "порядок чтения строки": [
        "1. Земля — начни с неё: это видимая, бытовая сторона, в которой человек "
        "себя узнаёт сразу.",
        "2. Небо — что стоит за этим внутри: настрой, отношение, внутренняя механика.",
        "3. Ключ — не третье отдельное число, а сумма первых двух со сведением "
        "(например 7 + 15 = 22). Это то, что получается, когда внутреннее "
        "встречается с внешним, — итог по зоне.",
        "4. Сравни Небо и Землю. Одинаковые числа — зазора нет, внутри и снаружи "
        "одно и то же, зона работает без противоречия. Разные по природе — "
        "напряжение, и оно и есть содержание строки.",
        "5. У каждого аркана есть ресурсный и теневой полюс. Строка задаёт тему, "
        "а не приговор: скажи, как энергия выглядит в плюсе и во что сваливается "
        "в минусе, чтобы человек узнал свой собственный сценарий.",
    ],
    "как объяснять": "Человек не обязан знать, что такое Анахата и чем она отличается "
                     "от Манипуры. Не перечисляй строки таблицы — переводи: назови зону "
                     "жизни обычными словами (сердце и чувства, воля и желудок, опора и "
                     "род), скажи, что там за энергия и как она обычно себя ведёт, и "
                     "только потом при необходимости назови чакру. Возьми две-три самые "
                     "яркие строки вместо ровного пересказа всех семи.",
}

PURPOSE_NOTE = (
    "Четвёртый уровень («высшее духовное предназначение») здесь не считается: "
    "формулу не удалось подтвердить по источникам, а угадывать её значит выдавать "
    "выдумку за расчёт. Три уровня ниже проверены на контрольной матрице."
)


def chakra_map(a: int, b: int, c: int, d: int, e: int) -> dict:
    """Семь чакр по двум осям: Небо — вертикаль (месяц ↔ карма), Земля — горизонталь (день ↔ год).

    Каждая половина оси делится последовательными сложениями: сначала точка между
    внешним числом и центром, потом между ней и краями. Ключ — сумма Неба и Земли.
    """
    def half(outer: int, center: int) -> tuple:
        mid = reduce_to_22(outer + center)          # Вишудха
        inner = reduce_to_22(mid + center)          # Анахата
        near = reduce_to_22(outer + mid)            # Аджна
        return near, mid, inner

    sky_near, sky_mid, sky_inner = half(b, e)
    earth_near, earth_mid, earth_inner = half(a, e)

    down_near, down_mid, down_inner = half(d, e)     # нижняя половина вертикали
    right_near, right_mid, right_inner = half(c, e)   # правая половина горизонтали

    sky = [b, sky_near, sky_mid, sky_inner, e, down_mid, d]
    earth = [a, earth_near, earth_mid, earth_inner, e, right_mid, c]

    rows = []
    for i, (zone, name, description, color) in enumerate(CHAKRAS):
        key = reduce_to_22(sky[i] + earth[i])
        rows.append({
            "зона": zone,
            "chakra": name,
            "about": description,
            "color": color,
            "Небо": {"number": sky[i], "arcanum": ARCANA[sky[i]]},
            "Земля": {"number": earth[i], "arcanum": ARCANA[earth[i]]},
            "Ключ": {"number": key, "arcanum": ARCANA[key],
                     "значение": meaning(key, "здоровье")},
        })

    sky_total = reduce_to_22(sum(sky))
    earth_total = reduce_to_22(sum(earth))
    whole = reduce_to_22(sum(sky) + sum(earth))

    return {
        "note": HEALTH_NOTE,
        "как_читать": HEALTH_HOWTO,
        "rows": rows,
        "axis_points": {
            "вверх_от_центра": [sky_near, sky_mid, sky_inner],
            "вниз_от_центра": [down_near, down_mid, down_inner],
            "влево_от_центра": [earth_near, earth_mid, earth_inner],
            "вправо_от_центра": [right_near, right_mid, right_inner],
            "note": "Каждая половина оси делится одинаково, по три точки. "
                    "В таблице чакр используются верхняя и левая половины целиком, "
                    "а от нижней и правой — только средние точки (Свадхистана). "
                    "Остальные нужны для полноты схемы.",
        },
        "organism": {
            "зона": "Тело в целом",
            "chakra": "все системы",
            "about": "свод по всей карте: как тело откликается на жизнь в целом",
            "Небо": {"number": sky_total, "arcanum": ARCANA[sky_total]},
            "Земля": {"number": earth_total, "arcanum": ARCANA[earth_total]},
            "Ключ": {"number": whole, "arcanum": ARCANA[whole],
                     "значение": meaning(whole, "здоровье")},
        },
    }


def purposes(a: int, b: int, c: int, d: int,
             f: int, g: int, h: int, k: int) -> dict:
    """Предназначения: личное, родовое и духовное как их сумма."""
    sky_line = reduce_to_22(b + d)
    earth_line = reduce_to_22(a + c)
    personal = reduce_to_22(sky_line + earth_line)

    father = reduce_to_22(f + h)   # мужская диагональ родового квадрата
    mother = reduce_to_22(k + g)   # женская диагональ
    ancestral = reduce_to_22(father + mother)

    spiritual = reduce_to_22(personal + ancestral)

    def named(n: int) -> dict:
        return {"number": n, "arcanum": ARCANA[n],
                "значение": meaning(n, "предназначение")}

    return {
        "note": PURPOSE_NOTE,
        "личное": {
            "Небо": named(sky_line), "Земля": named(earth_line),
            "итог": named(personal),
            "about": "как реализуется сам человек; линия Неба — духовная часть, линия Земли — материальная",
        },
        "родовое": {
            "отец": named(father), "мать": named(mother),
            "итог": named(ancestral),
            "about": "что приходит через род: отец — мужская диагональ F—H, мать — женская K—G",
        },
        "духовное": {
            "итог": named(spiritual),
            "about": "сумма личного и родового: тема, которая собирает оба уровня",
        },
        "личное_совпало_с_центром": personal == reduce_to_22(a + b + c + d),
        "про_совпадение": "Личное предназначение и центр E выводятся из одной "
                          "суммы A+B+C+D, поэтому совпадают примерно в трёх случаях "
                          "из пяти. Если совпало — это арифметика, а не отдельный "
                          "знак, и подавать это как «подтверждение судьбы» нечестно.",
        "высшее духовное": None,
    }


def age_scale(a: int, b: int, c: int, d: int) -> list:
    """Возрастная шкала 0–80 по периметру: A(0) → B(20) → C(40) → D(60) → A(80).

    Каждая сторона делится пополам последовательными сложениями, шаг — 2,5 года.
    Середины сторон совпадают с углами родового квадрата: это и есть отметки
    10, 30, 50 и 70 лет.
    """
    scale = []
    for side, (start_value, end_value) in enumerate(
            ((a, b), (b, c), (c, d), (d, a))):
        base_age = side * 20
        mid = reduce_to_22(start_value + end_value)
        quarter = reduce_to_22(start_value + mid)
        three_quarter = reduce_to_22(mid + end_value)
        marks = [
            (0.0, start_value),
            (2.5, reduce_to_22(start_value + quarter)),
            (5.0, quarter),
            (7.5, reduce_to_22(quarter + mid)),
            (10.0, mid),
            (12.5, reduce_to_22(mid + three_quarter)),
            (15.0, three_quarter),
            (17.5, reduce_to_22(three_quarter + end_value)),
        ]
        for offset, value in marks:
            scale.append({
                "age": base_age + offset,
                "number": value,
                "arcanum": ARCANA[value],
            })
    scale.append({"age": 80.0, "number": a, "arcanum": ARCANA[a],
                  "note": "круг замыкается: 80 лет возвращает к точке A"})
    return scale


def decade_periods(scale: list) -> list:
    """Крупные вехи по десятилетиям — каркас для разговора об этапах жизни."""
    periods = []
    for mark in scale:
        if mark["age"] % 10 or mark["age"] >= 80:
            continue
        age = int(mark["age"])
        periods.append({
            "период": f"{age}–{age + 10} лет",
            "number": mark["number"],
            "arcanum": mark["arcanum"],
            "значение": meaning(mark["number"], "тема"),
            "в плюсе": meaning(mark["number"], "плюс"),
            "в минусе": meaning(mark["number"], "минус"),
        })
    return periods


def age_today(day: int, month: int, year: int) -> int:
    today = date.today()
    return today.year - year - ((today.month, today.day) < (month, day))


def current_period(scale: list, age: int) -> dict:
    """Какая отметка шкалы действует сейчас."""
    if age < 0:
        return {"age": age, "note": "возраст не может быть отрицательным — шкала начинается с 0 лет"}
    if age > 80:
        return {"age": age, "note": "шкала рассчитана до 80 лет; дальше метод её не продолжает"}
    active = max((m for m in scale if m["age"] <= age), key=lambda m: m["age"])
    following = [m for m in scale if m["age"] > age]
    next_mark = min(following, key=lambda m: m["age"]) if following else None
    return {
        "возраст": age,
        "следующая_отметка": (
            {"age": next_mark["age"], "number": next_mark["number"],
             "arcanum": next_mark["arcanum"],
             "значение": meaning(next_mark["number"], "тема")}
            if next_mark else None
        ),
        "отметка": active["age"],
        "number": active["number"],
        "arcanum": active["arcanum"],
        "значение": meaning(active["number"], "тема"),
        "в плюсе": meaning(active["number"], "плюс"),
        "в минусе": meaning(active["number"], "минус"),
        "note": "Это тема периода, а не событие и не прогноз. Говори про энергию "
                "отрезка жизни, не про то, что «случится».",
    }


MILLIONAIRE_CODE = (5, 14, 19)
GOLDEN_GIFT = (15, 4, 19)

STATUS_LEGEND = {
    "проверено": "считается однозначно, разночтений между школами нет",
    "реконструкция": "у школ формулы расходятся; здесь один из вариантов, "
                     "и об этом нужно сказать человеку",
}

MODULE_DISCLAIMER = (
    "Эти пять модулей — поздние надстройки разных школ, а не исходный метод. "
    "У каждого ниже стоит поле «статус»: «проверено» — арифметика однозначна и "
    "сверена; «реконструкция» — формула собрана по описанию метода, потому что "
    "единого стандарта у школ нет. Реконструкцию обязательно называй вслух: "
    "«в этой версии считается так, в других школах бывает иначе». Выдавать её за "
    "канон нечестно — человек может пойти сверять и решить, что его обманули."
)


def money_channel(chakras: dict) -> dict:
    """Денежный канал: три точки материальной вертикали.

    Реконструкция по описанию метода (вход в поток → источник → блок): берём
    столбец Ключа на трёх нижних чакрах, где в методе и располагают финансовые
    позиции. Другие школы строят канал по столбцу Земли или добавляют четвёртую
    точку — числа тогда будут другими.
    """
    rows = chakras["rows"]
    return {
        "статус": "реконструкция",
        "что_это": "Денежный канал — три точки, которые в методе читают как "
                   "денежную историю человека: чем он зарабатывает по своей природе, "
                   "что включает поток, и что мешает деньгам задерживаться.",
        "формула": "столбец «Ключ» на чакрах Манипура, Свадхистана, Муладхара",
        "точки": [
            read(rows[4]["Ключ"]["number"], "финансы", "источник дохода (Манипура)"),
            read(rows[5]["Ключ"]["number"], "финансы", "точка входа в поток (Свадхистана)"),
            read(rows[6]["Ключ"]["number"], "финансы", "материальная карма, блок (Муладхара)"),
        ],
        "как подавать": "Про отношение к деньгам, способ зарабатывать и то, что "
                        "мешает брать. Без сумм, сроков и советов вкладывать — "
                        "рамка про финансы в SKILL.md здесь действует полностью.",
    }


def love_triangle(chakras: dict) -> dict:
    """Любовный треугольник: три точки на сердечном уровне.

    Реконструкция: в методе линия отношений описывается тремя позициями —
    вход в отношения, характер связи, блокировки — и располагается на Анахате.
    Здесь это три её числа: Земля, Ключ и Небо.
    """
    heart = chakras["rows"][3]
    return {
        "статус": "реконструкция",
        "что_это": "Линия отношений — три точки: с чем человек приходит в близость, "
                   "каким получается партнёрство и что чаще всего его осложняет.",
        "формула": "три числа чакры Анахата: Земля, Ключ, Небо",
        "точки": [
            read(heart["Земля"]["number"], "отношения", "с чем человек входит в отношения"),
            read(heart["Ключ"]["number"], "отношения", "характер связи, каким получается партнёрство"),
            read(heart["Небо"]["number"], "минус", "что осложняет близость"),
        ],
        "как подавать": "Описывай механику контакта, а не вердикт о партнёре. "
                        "«Подходит / не подходит» матрица не решает.",
    }


def talents(chakras: dict, f: int, g: int, h: int, k: int) -> dict:
    """Зона талантов: три основных и шесть родовых.

    Счёт «3 + 6 = 9» взят из описания метода: три верхние чакры дают личные
    таланты, родовые линии — шесть чисел (по две точки диагонали и её итог).
    """
    rows = chakras["rows"]
    father = reduce_to_22(f + h)
    mother = reduce_to_22(k + g)

    def named(n: int, role: str) -> dict:
        return read(n, "предназначение", role)

    return {
        "статус": "реконструкция",
        "что_это": "Зона талантов — то, что даётся легче остального: три личных "
                   "способности и шесть, которые в методе считают доставшимися по роду.",
        "формула": "личные — столбец «Ключ» верхних трёх чакр; родовые — точки "
                   "мужской (F, H) и женской (K, G) диагоналей плюс итог каждой",
        "личные": [
            read(rows[0]["Ключ"]["number"], "предназначение", "духовный талант (Сахасрара)"),
            read(rows[1]["Ключ"]["number"], "предназначение", "интеллектуальный талант (Аджна)"),
            read(rows[2]["Ключ"]["number"], "предназначение", "талант самовыражения (Вишудха)"),
        ],
        "родовые": {
            "мужская линия": [named(f, "F"), named(h, "H"), named(father, "итог линии")],
            "женская линия": [named(k, "K"), named(g, "G"), named(mother, "итог линии")],
        },
        "как подавать": "Талант — это не гарантия успеха и не обязанность. "
                        "Говори «здесь есть предрасположенность», а не «вы должны».",
    }


def personal_year(day: int, month: int, a: int, b: int) -> dict:
    """Личный год: отсчитывается от дня рождения, а не от 1 января."""
    today = date.today()
    start_year = today.year if (today.month, today.day) >= (month, day) else today.year - 1
    year_number = reduce_to_22(sum(int(d) for d in str(start_year)))
    value = reduce_to_22(a + b + year_number)
    return {
        "статус": "проверено",
        "что_это": "Личный год — тема ближайшего года жизни. Отсчитывается от дня "
                   "рождения, а не от 1 января, поэтому он не совпадает с календарным.",
        "формула": "A + B + сумма цифр года текущего личного цикла, со сведением",
        "период": f"с {day:02d}.{month:02d}.{start_year} до следующего дня рождения",
        "number": value,
        "arcanum": ARCANA[value],
        "значение": meaning(value, "тема"),
        "в плюсе": meaning(value, "плюс"),
        "в минусе": meaning(value, "минус"),
        "как подавать": "Тема года, а не расписание событий. «В этот год "
                        "разворачивается тема…» — да; «в этом году произойдёт» — нет.",
    }


def code_check(matrix_lines: dict, wanted: tuple, title: str) -> dict:
    """Собрались ли три конкретных аркана в пределах одной линии матрицы."""
    found_in = [name for name, values in matrix_lines.items()
                if all(number in values for number in wanted)]
    where = {
        number: [name for name, values in matrix_lines.items() if number in values]
        for number in wanted
    }
    present = [n for n in wanted if where[n]]
    missing = [n for n in wanted if not where[n]]

    names = ", ".join(f"{n} ({ARCANA[n]})" for n in wanted)
    if found_in:
        verdict = (f"Собран: все три аркана ({names}) оказались в одной линии — "
                   + ", ".join(found_in) + ".")
    elif missing:
        verdict = ("Не собран. В матрице вообще нет арканов: "
                   + ", ".join(f"{n} ({ARCANA[n]})" for n in missing)
                   + ". Код считается собранным, только когда все три стоят в одной линии.")
    else:
        verdict = ("Не собран, хотя все три аркана в матрице есть — они просто "
                   "разошлись по разным линиям. Код засчитывается, только когда "
                   "все три оказываются в пределах одной линии.")

    return {
        "статус": "проверено",
        "что_это": f"«{title}» — популярное поверье: считается, что если арканы "
                   f"{'-'.join(str(n) for n in wanted)} собираются в одной линии "
                   "матрицы, у человека силён финансовый потенциал. Это позднее "
                   "маркетинговое дополнение, а не часть исходного метода.",
        "итог": verdict,
        "где_стоят_эти_арканы": [
            {"number": n, "arcanum": ARCANA[n],
             "линии": where[n] or ["в матрице нет"],
             "значение": meaning(n, "финансы")}
            for n in wanted
        ],
        "формула": f"все три аркана {'-'.join(str(n) for n in wanted)} в пределах одной линии",
        "как подавать": "Даже если код собрался — это про интерес к теме денег и "
                        "потенциал, а не обещание богатства. Если не собрался — прямо "
                        "скажи, что это ничего не говорит о достатке: поверье не имеет "
                        "отношения к тому, как человек живёт и зарабатывает.",
    }


CHILD_SKIPPED = (
    "Денежный канал и любовный треугольник в детской матрице не считаются. "
    "Разбирать у ребёнка «с чем он входит в отношения» или «что мешает брать "
    "деньги» — значит примерять к нему взрослые сценарии, которых у него ещё нет, "
    "и подсовывать родителю ярлык вместо ребёнка. Если родитель спросит про них "
    "прямо — так и объясни, а не считай молча."
)


def extra_modules(matrix: dict, day: int, month: int, child: bool = False) -> dict:
    """Поздние надстройки, о которых чаще всего спрашивают.

    В детском режиме денежный и любовный блоки не выдаются совсем: у ребёнка нет
    той жизни, которую они описывают.
    """
    personal = {key: value["number"] for key, value in matrix["personal_square"].items()}
    family = {key: value["number"] for key, value in matrix["family_square"].items()}
    chakras = matrix["chakra_map"]

    lines = {
        "личный квадрат": list(personal.values()),
        "родовой квадрат": list(family.values()),
        "линия Неба": [row["Небо"]["number"] for row in chakras["rows"]],
        "линия Земли": [row["Земля"]["number"] for row in chakras["rows"]],
        "линия Ключа": [row["Ключ"]["number"] for row in chakras["rows"]],
    }

    modules = {
        "note": MODULE_DISCLAIMER,
        "что означает статус": STATUS_LEGEND,
        "зона талантов": talents(chakras, family["F"], family["G"],
                                 family["H"], family["K"]),
        "личный год": personal_year(day, month, personal["A"], personal["B"]),
        "код миллионера": code_check(lines, MILLIONAIRE_CODE, "код миллионера"),
        "золотой дар": code_check(lines, GOLDEN_GIFT, "золотой дар (метка Мидаса)"),
    }
    if child:
        modules["не считается для ребёнка"] = CHILD_SKIPPED
    else:
        modules["денежный канал"] = money_channel(chakras)
        modules["любовный треугольник"] = love_triangle(chakras)
    return modules


def flat_numbers(matrix: dict) -> dict:
    """Плоский словарь точка → число, для сравнения двух матриц."""
    flat = {}
    for square in ("personal_square", "family_square"):
        for key, value in matrix[square].items():
            flat[key] = value["number"]
    return flat


def compare(one: dict, two: dict) -> dict:
    """Наложение двух матриц: где числа совпали, что каждый несёт в контакт."""
    first, second = flat_numbers(one), flat_numbers(two)

    same_position = {
        key: {"number": first[key], "arcanum": ARCANA[first[key]], "role": ROLES[key]}
        for key in first
        if first[key] == second[key]
    }
    shared_arcana = sorted(set(first.values()) & set(second.values()))

    return {
        "note": COMPATIBILITY_NOTE,
        "same_number_in_same_point": same_position,
        "arcana_present_in_both_matrices": [
            {"number": n, "arcanum": ARCANA[n]} for n in shared_arcana
        ],
        "core_E": {
            "person_1": one["personal_square"]["E"],
            "person_2": two["personal_square"]["E"],
        },
        "relationship_points_G_H": {
            "person_1": {"G": one["family_square"]["G"], "H": one["family_square"]["H"]},
            "person_2": {"G": two["family_square"]["G"], "H": two["family_square"]["H"]},
        },
    }


def selftest() -> int:
    """Две контрольные матрицы: базовые точки и производные блоки.

    Вторая сверена с разбором стороннего калькулятора (26.09.1988) — если
    какая-то из этих цифр разойдётся, значит поехала формула, а не оформление.
    """
    failures = []

    # Справочник проверяем первым: раньше самопроверка рапортовала «пройдена»
    # на пустом справочнике, то есть именно тогда, когда скилл был сломан.
    failures.extend(guide_problems())

    base = flat_numbers(calculate(15, 5, 1985))
    base["итог"] = calculate(15, 5, 1985)["karmic_total"]["number"]
    expected_base = {"A": 15, "B": 5, "C": 5, "D": 7, "E": 5,
                     "F": 20, "G": 10, "H": 12, "K": 22, "итог": 2}
    if base != expected_base:
        failures.append(f"точки 15.05.1985: ожидалось {expected_base}, получено {base}")

    ref = calculate(26, 9, 1988)
    got_points = flat_numbers(ref)
    expected_points = {"A": 8, "B": 9, "C": 8, "D": 7, "E": 5,
                       "F": 17, "G": 17, "H": 15, "K": 15}
    if got_points != expected_points:
        failures.append(f"точки 26.09.1988: ожидалось {expected_points}, получено {got_points}")

    got_chakras = [
        (row["Небо"]["number"], row["Земля"]["number"], row["Ключ"]["number"])
        for row in ref["chakra_map"]["rows"]
    ]
    expected_chakras = [(9, 8, 17), (5, 21, 8), (14, 13, 9), (19, 18, 10),
                        (5, 5, 10), (12, 13, 7), (7, 8, 15)]
    if got_chakras != expected_chakras:
        failures.append(f"карта здоровья: ожидалось {expected_chakras}, получено {got_chakras}")

    organism = ref["chakra_map"]["organism"]
    got_organism = (organism["Небо"]["number"], organism["Земля"]["number"],
                    organism["Ключ"]["number"])
    if got_organism != (8, 14, 13):
        failures.append(f"строка «организм»: ожидалось (8, 14, 13), получено {got_organism}")

    purpose = ref["purposes"]
    got_purposes = (purpose["личное"]["итог"]["number"],
                    purpose["родовое"]["итог"]["number"],
                    purpose["духовное"]["итог"]["number"])
    if got_purposes != (5, 10, 15):
        failures.append(f"предназначения: ожидалось (5, 10, 15), получено {got_purposes}")

    marks = {m["age"]: m["number"] for m in ref["age_scale"]["marks"]}
    expected_marks = {0.0: 8, 10.0: 17, 20.0: 9, 30.0: 17, 40.0: 8,
                      50.0: 15, 60.0: 7, 70.0: 15, 80.0: 8}
    wrong = {age: marks[age] for age, value in expected_marks.items() if marks[age] != value}
    if wrong:
        failures.append(f"возрастная шкала: не сошлись отметки {wrong}, ожидалось {expected_marks}")

    extras = ref["extra_modules"]
    got_money = tuple(t["number"] for t in extras["денежный канал"]["точки"])
    if got_money != (10, 7, 15):
        failures.append(f"денежный канал: ожидалось (10, 7, 15), получено {got_money}")

    got_love = tuple(t["number"] for t in extras["любовный треугольник"]["точки"])
    if got_love != (18, 10, 19):
        failures.append(f"любовный треугольник: ожидалось (18, 10, 19), получено {got_love}")

    got_talents = tuple(t["number"] for t in extras["зона талантов"]["личные"])
    if got_talents != (17, 8, 9):
        failures.append(f"личные таланты: ожидалось (17, 8, 9), получено {got_talents}")

    code_verdict = extras["код миллионера"]["итог"]
    if not code_verdict.startswith("Собран") or "линия Неба" not in code_verdict:
        failures.append(f"код миллионера: ожидалось «собран в линии Неба», получено: {code_verdict}")

    if not extras["золотой дар"]["итог"].startswith("Не собран"):
        failures.append("золотой дар: не должен собираться на этой матрице")

    year_value = extras["личный год"]["number"]
    if not 1 <= year_value <= 22:
        failures.append(f"личный год вне диапазона 1-22: {year_value}")

    if failures:
        print("Самопроверка НЕ пройдена:", file=sys.stderr)
        for line in failures:
            print(f"  — {line}", file=sys.stderr)
        return 1

    print("Самопроверка пройдена: справочник, точки, карта здоровья, предназначения, "
          "шкала возрастов и дополнительные модули.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Расчёт точек Матрицы судьбы по дате рождения."
    )
    parser.add_argument("date", nargs="?", help="дата рождения, ДД.ММ.ГГГГ")
    parser.add_argument("--partner", metavar="ДД.ММ.ГГГГ",
                        help="вторая дата: считает обе матрицы и их наложение")
    parser.add_argument("--child", action="store_true",
                        help="детская матрица: те же числа, но с пометкой о мягкой трактовке")
    parser.add_argument("--age", type=int, metavar="N",
                        help="показать период жизни для конкретного возраста")
    parser.add_argument("--selftest", action="store_true",
                        help="проверить расчёт на контрольном примере")
    parser.add_argument("--allow-missing-guide", action="store_true",
                        help="считать числа даже без справочника значений (трактовки будут пустыми)")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.date:
        parser.error("нужна дата рождения в формате ДД.ММ.ГГГГ")

    guide_code = require_guide(args.allow_missing_guide)
    if guide_code:
        return guide_code

    try:
        person = calculate(*parse_date(args.date), child=args.child)
        if args.partner:
            partner = calculate(*parse_date(args.partner), child=args.child)
    except ValueError as exc:
        print(f"Ошибка: {exc}. Переспроси дату у пользователя, не досчитывай наугад.",
              file=sys.stderr)
        return 1

    if args.age is not None:
        marks = person["age_scale"]["marks"]
        print(json.dumps({
            "input_date": person["input_date"],
            "запрошенный_возраст": args.age,
            "период": current_period(marks, args.age),
            "по_десятилетиям": person["age_scale"]["по_десятилетиям"],
            "как_читать": person["age_scale"]["как_читать"],
        }, ensure_ascii=False, indent=2))
        return 0

    if args.partner:
        person["hidden_layers"] = hidden_layers(person, parse_date(args.date)[2])
        partner["hidden_layers"] = hidden_layers(partner, parse_date(args.partner)[2])
        result = {"mode": "compatibility", "person_1": person,
                  "person_2": partner, "comparison": compare(person, partner)}
        if args.child:
            result["child_note"] = CHILD_NOTE
    else:
        result = {"mode": "child" if args.child else "single", **person}
        result["hidden_layers"] = hidden_layers(person, parse_date(args.date)[2])
        if args.child:
            result["child_note"] = CHILD_NOTE

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
