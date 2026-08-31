#!/usr/bin/env python3
"""
Джйотиш-расчёты на Swiss Ephemeris (pyswisseph).
КОНФИГ ЗАФИКСИРОВАН: аянамша Lahiri, дома whole sign, узлы Mean node.

Установка (один раз):
    pip install pyswisseph --break-system-packages

Использование:
    python3 jyotish_calc.py ГГГГ-ММ-ДД ЧЧ:ММ --lat ШИРОТА --lon ДОЛГОТА --utc-offset ЧАСЫ
    python3 jyotish_calc.py ГГГГ-ММ-ДД --utc-offset ЧАСЫ        # без времени: только позиции планет, без лагны/домов/варг

Время — местное ПО ЧАСАМ (не солнечное!) + смещение от UTC на момент рождения.
Для СССР/России проверяй декретное и летнее время.
Вывод: JSON на русском.
"""
import sys, json, argparse, datetime
import swisseph as swe

swe.set_sid_mode(swe.SIDM_LAHIRI)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

SIGNS = ["Овен","Телец","Близнецы","Рак","Лев","Дева","Весы","Скорпион","Стрелец","Козерог","Водолей","Рыбы"]
SIGNS_SA = ["Меша","Вришабха","Митхуна","Карка","Симха","Канья","Тула","Вришчика","Дхану","Макара","Кумбха","Мина"]
NAKSHATRAS = ["Ашвини","Бхарани","Криттика","Рохини","Мригашира","Ардра","Пунарвасу","Пушья","Ашлеша",
              "Магха","Пурва-Пхалгуни","Уттара-Пхалгуни","Хаста","Читра","Свати","Вишакха","Анурадха","Джйештха",
              "Мула","Пурва-Ашадха","Уттара-Ашадха","Шравана","Дхаништха","Шатабхиша","Пурва-Бхадрапада","Уттара-Бхадрапада","Ревати"]
# Управители накшатр = порядок Вимшоттари
NAK_LORDS = ["Кету","Венера","Солнце","Луна","Марс","Раху","Юпитер","Сатурн","Меркурий"] * 3
DASHA_YEARS = {"Кету":7,"Венера":20,"Солнце":6,"Луна":10,"Марс":7,"Раху":18,"Юпитер":16,"Сатурн":19,"Меркурий":17}
DASHA_ORDER = ["Кету","Венера","Солнце","Луна","Марс","Раху","Юпитер","Сатурн","Меркурий"]

GRAHAS = [("Солнце",swe.SUN),("Луна",swe.MOON),("Марс",swe.MARS),("Меркурий",swe.MERCURY),
          ("Юпитер",swe.JUPITER),("Венера",swe.VENUS),("Сатурн",swe.SATURN),("Раху",swe.MEAN_NODE)]
EXALT = {"Солнце":0,"Луна":1,"Марс":9,"Меркурий":5,"Юпитер":3,"Венера":11,"Сатурн":6,"Раху":1,"Кету":7}
OWN = {"Солнце":[4],"Луна":[3],"Марс":[0,7],"Меркурий":[2,5],"Юпитер":[8,11],"Венера":[1,6],"Сатурн":[9,10],"Раху":[],"Кету":[]}
KARAKA_NAMES = ["Атмакарака (душа, цель жизни)","Аматьякарака (карьера, советник)","Бхратрикарака (братья, наставник)",
                "Матрикарака (мать, дом)","Путракарака (дети, ученики)","Гнатикарака (испытания, болезни)",
                "Даракарака (супруг/партнёр)"]
TITHI = ["Пратипада","Двитья","Тритья","Чатуртхи","Панчами","Шаштхи","Саптами","Аштами","Навами","Дашами",
         "Экадаши","Двадаши","Трайодаши","Чатурдаши","Пурнима/Амавасья"]
VARA = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

def deg_fmt(lon):
    sign = int(lon // 30); d = lon % 30
    return f"{int(d)}°{int(d%1*60):02d}′ {SIGNS[sign]}"

def nakshatra_of(lon):
    idx = int(lon / (360/27))
    pada = int((lon % (360/27)) / (360/108)) + 1
    frac = (lon % (360/27)) / (360/27)
    return idx, pada, frac

def navamsa_sign(lon):
    sign = int(lon // 30); part = int((lon % 30) / (30/9))
    if sign % 3 == 0: start = sign            # подвижные
    elif sign % 3 == 1: start = (sign + 8) % 12  # фиксированные: от 9-го
    else: start = (sign + 4) % 12             # двойственные: от 5-го
    return (start + part) % 12

def dashamsa_sign(lon):
    sign = int(lon // 30); part = int((lon % 30) / 3)
    start = sign if sign % 2 == 0 else (sign + 8) % 12
    return (start + part) % 12

def dignity(name, sign):
    if sign == EXALT.get(name, -1): return "экзальтация (максимальная сила)"
    if sign == (EXALT.get(name, -1) + 6) % 12: return "дебилитация (ослабление)"
    if sign in OWN.get(name, []): return "своя обитель (устойчивая сила)"
    return ""

def vimshottari(moon_lon, birth_dt, levels=3, horizon_years=120):
    nak_idx, _, frac = nakshatra_of(moon_lon)
    lord0 = NAK_LORDS[nak_idx]
    i0 = DASHA_ORDER.index(lord0)
    balance = (1 - frac) * DASHA_YEARS[lord0]
    Y = 365.25
    periods = []
    t = birth_dt
    # первая (частичная) маха-даша
    seq = [(lord0, balance)] + [(DASHA_ORDER[(i0+k) % 9], DASHA_YEARS[DASHA_ORDER[(i0+k) % 9]]) for k in range(1, 12)]
    for lord, yrs in seq:
        end = t + datetime.timedelta(days=yrs * Y)
        maha = {"планета": lord, "с": t.date().isoformat(), "по": end.date().isoformat(), "антар_даши": []}
        if levels >= 2:
            t2 = t
            j0 = DASHA_ORDER.index(lord)
            for k in range(9):
                al = DASHA_ORDER[(j0 + k) % 9]
                a_yrs = yrs * DASHA_YEARS[al] / 120.0
                a_end = t2 + datetime.timedelta(days=a_yrs * Y)
                antar = {"планета": al, "с": t2.date().isoformat(), "по": a_end.date().isoformat()}
                maha["антар_даши"].append(antar)
                t2 = a_end
        periods.append(maha)
        t = end
        if (t - birth_dt).days > horizon_years * Y: break
    return lord0, periods

def current_dasha(periods, now):
    ns = now.date().isoformat()
    for m in periods:
        if m["с"] <= ns <= m["по"]:
            for a in m["антар_даши"]:
                if a["с"] <= ns <= a["по"]:
                    return m["планета"], a["планета"], m["по"], a["по"]
            return m["планета"], None, m["по"], None
    return None, None, None, None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("date"); p.add_argument("time", nargs="?", default=None)
    p.add_argument("--lat", type=float, default=None); p.add_argument("--lon", type=float, default=None)
    p.add_argument("--utc-offset", type=float, required=True)
    args = p.parse_args()

    try:
        y, m, d = map(int, args.date.split("-")); datetime.date(y, m, d)
    except Exception:
        print(json.dumps({"ошибка": f"Некорректная дата: {args.date}"}, ensure_ascii=False)); sys.exit(1)

    has_time = args.time is not None
    if has_time:
        try:
            hh, mm = map(int, args.time.split(":")); assert 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            print(json.dumps({"ошибка": f"Некорректное время: {args.time}"}, ensure_ascii=False)); sys.exit(1)
    else:
        hh, mm = 12, 0

    ut_hour = hh + mm/60 - args.utc_offset
    jd = swe.julday(y, m, d, ut_hour)
    birth_dt = datetime.datetime(y, m, d, hh, mm) - datetime.timedelta(hours=args.utc_offset)

    # --- Грахи ---
    planets = {}
    lons = {}
    for name, pid in GRAHAS:
        xx, _ = swe.calc_ut(jd, pid, FLAGS)
        lon, speed = xx[0], xx[3]
        lons[name] = lon
        nidx, pada, _ = nakshatra_of(lon)
        sign = int(lon // 30)
        planets[name] = {
            "положение": deg_fmt(lon),
            "знак_санскрит": SIGNS_SA[sign],
            "накшатра": f"{NAKSHATRAS[nidx]} (управитель {NAK_LORDS[nidx]}), пада {pada}",
            "ретроградность": bool(speed < 0) if name not in ("Солнце","Луна","Раху") else (name == "Раху"),
            "достоинство": dignity(name, sign),
            "навамша_D9": SIGNS[navamsa_sign(lon)],
            "дашамша_D10": SIGNS[dashamsa_sign(lon)],
            "варготтама": navamsa_sign(lon) == sign,
        }
    ketu_lon = (lons["Раху"] + 180) % 360
    lons["Кету"] = ketu_lon
    nidx, pada, _ = nakshatra_of(ketu_lon)
    ksign = int(ketu_lon // 30)
    planets["Кету"] = {"положение": deg_fmt(ketu_lon), "знак_санскрит": SIGNS_SA[ksign],
                       "накшатра": f"{NAKSHATRAS[nidx]} (управитель {NAK_LORDS[nidx]}), пада {pada}",
                       "ретроградность": True, "достоинство": dignity("Кету", ksign),
                       "навамша_D9": SIGNS[navamsa_sign(ketu_lon)], "дашамша_D10": SIGNS[dashamsa_sign(ketu_lon)],
                       "варготтама": navamsa_sign(ketu_lon) == ksign}

    out = {"конфигурация": "аянамша Lahiri, дома whole sign, узлы mean node",
           "дата_время": f"{args.date}" + (f" {args.time} (UTC{args.utc_offset:+g})" if has_time else " (время неизвестно, позиции на полдень)"),
           "аянамша_на_дату": round(swe.get_ayanamsa_ut(jd), 4)}

    # --- Лагна и дома (нужны время + координаты) ---
    if has_time and args.lat is not None and args.lon is not None:
        cusps, ascmc = swe.houses_ex(jd, args.lat, args.lon, b'W', FLAGS)
        asc = ascmc[0]; asc_sign = int(asc // 30)
        nidx, pada, _ = nakshatra_of(asc)
        out["лагна"] = {"положение": deg_fmt(asc), "знак_санскрит": SIGNS_SA[asc_sign],
                        "накшатра": f"{NAKSHATRAS[nidx]}, пада {pada}",
                        "навамша_лагна_D9": SIGNS[navamsa_sign(asc)]}
        for name in planets:
            planets[name]["дом"] = (int(lons[name] // 30) - asc_sign) % 12 + 1
        # чувствительность лагны ко времени: ±5 минут
        for dt_min, key in ((-5, "лагна_минус_5_минут"), (5, "лагна_плюс_5_минут")):
            jd2 = swe.julday(y, m, d, ut_hour + dt_min/60)
            _, a2 = swe.houses_ex(jd2, args.lat, args.lon, b'W', FLAGS)
            if int(a2[0] // 30) != asc_sign:
                out.setdefault("предупреждение_лагна", "Лагна меняет знак в пределах ±5 минут от указанного времени — карта чувствительна к точности времени, скажи об этом клиенту и рассчитай обе версии.")
    elif has_time:
        out["примечание_лагна"] = "Координаты не переданы (--lat/--lon) — лагна, дома и предупреждения не рассчитаны."

    out["грахи"] = planets

    # --- Чара-караки (Джаймини, 7-каракная схема без Раху) ---
    kar = sorted([(name, lons[name] % 30) for name, _ in GRAHAS if name != "Раху"], key=lambda x: -x[1])
    out["чара_караки_джаймини"] = {KARAKA_NAMES[i]: f"{kar[i][0]} ({kar[i][1]:.2f}° в знаке)" for i in range(7)}

    # --- Панчанга ---
    tithi_n = int(((lons["Луна"] - lons["Солнце"]) % 360) / 12)
    paksha = "шукла (растущая Луна)" if tithi_n < 15 else "кришна (убывающая Луна)"
    out["панчанга"] = {"титхи": f"{TITHI[tithi_n % 15]} ({paksha})",
                       "вара": VARA[datetime.date(y, m, d).weekday()],
                       "накшатра_луны": NAKSHATRAS[nakshatra_of(lons['Луна'])[0]]}

    # --- Вимшоттари ---
    lord0, periods = vimshottari(lons["Луна"], birth_dt)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    mah, ant, mah_end, ant_end = current_dasha(periods, now)
    out["вимшоттари"] = {
        "стартовая_маха_даша": lord0,
        "текущая": {"маха_даша": mah, "до": mah_end, "антар_даша": ant, "антар_до": ant_end},
        "маха_даши": [{"планета": p["планета"], "с": p["с"], "по": p["по"]} for p in periods],
        "антар_даши_текущей_махи": next((p["антар_даши"] for p in periods if p["планета"] == mah), []),
    }
    if not has_time:
        out["примечание"] = "Время неизвестно: лагна/дома/варги недоступны, позиция Луны и даши могут сдвигаться (Луна проходит ~13° в сутки — накшатра Луны может отличаться). Проверь границы."

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
