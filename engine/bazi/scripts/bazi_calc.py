#!/usr/bin/env python3
"""
Расчёт Ба-цзы (Четыре столпа судьбы) по григорианской дате.
Использует lunar_python (солнечные термины цзеци, точный лунный календарь).

Установка зависимости (один раз):
    pip install lunar_python --break-system-packages

Использование:
    python3 bazi_calc.py ГГГГ-ММ-ДД [ЧЧ:ММ] [--gender m|f] [--lon ДОЛГОТА --utc-offset ЧАСЫ]

Если время неизвестно — не передавать, столп часа будет опущен.
Если известны долгота места и смещение часов от UTC на момент рождения —
время конвертируется в ИСТИННОЕ СОЛНЕЧНОЕ (обязательно для СССР/России:
декретное время расходится с солнцем до 2 часов).
Вывод: JSON на русском со всеми данными для интерпретации.
"""
import sys, json, argparse, math
from lunar_python import Solar

NAYIN_RU = {"海中金":"Золото в море","炉中火":"Огонь в очаге","大林木":"Дерево большого леса","路旁土":"Земля у дороги",
"剑锋金":"Золото острия меча","山头火":"Огонь на вершине горы","涧下水":"Вода горного ручья","城头土":"Земля городской стены",
"白蜡金":"Золото белого воска","杨柳木":"Дерево ивы","泉中水":"Вода родника","屋上土":"Земля на крыше",
"霹雳火":"Огонь молнии","松柏木":"Дерево сосны и кипариса","长流水":"Вода длинного потока","砂中金":"Золото в песке",
"山下火":"Огонь под горой","平地木":"Дерево равнины","壁上土":"Земля стены","金箔金":"Золото фольги",
"覆灯火":"Огонь лампады","天河水":"Вода Небесной реки","大驿土":"Земля большого тракта","钗钏金":"Золото украшений",
"桑柘木":"Дерево тутовника","大溪水":"Вода большого ручья","沙中土":"Земля в песках","天上火":"Огонь небесный",
"石榴木":"Дерево граната","大海水":"Вода океана"}
def nayin(s):
    return f"{s} — {NAYIN_RU.get(s, s)}"

def equation_of_time_minutes(day_of_year):
    """Уравнение времени (минуты), приближение NOAA, точность ~1 мин."""
    b = 2 * math.pi * (day_of_year - 81) / 364.0
    return 9.87 * math.sin(2*b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

def to_solar_time(y, m, d, hh, mm, lon, utc_offset):
    """Часовое время -> истинное солнечное. Возвращает (y,m,d,hh,mm, сдвиг_в_минутах)."""
    import datetime
    dt = datetime.datetime(y, m, d, hh, mm)
    doy = dt.timetuple().tm_yday
    shift = (lon * 4.0 - utc_offset * 60.0) + equation_of_time_minutes(doy)
    dt2 = dt + datetime.timedelta(minutes=shift)
    return dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute, round(shift)

GAN_RU = {"甲":"Цзя (Ян-Дерево)","乙":"И (Инь-Дерево)","丙":"Бин (Ян-Огонь)","丁":"Дин (Инь-Огонь)",
          "戊":"У (Ян-Земля)","己":"Цзи (Инь-Земля)","庚":"Гэн (Ян-Металл)","辛":"Синь (Инь-Металл)",
          "壬":"Жэнь (Ян-Вода)","癸":"Гуй (Инь-Вода)"}
GAN_ELEM = {"甲":"Дерево","乙":"Дерево","丙":"Огонь","丁":"Огонь","戊":"Земля",
            "己":"Земля","庚":"Металл","辛":"Металл","壬":"Вода","癸":"Вода"}
GAN_YINYANG = {"甲":"Ян","乙":"Инь","丙":"Ян","丁":"Инь","戊":"Ян","己":"Инь","庚":"Ян","辛":"Инь","壬":"Ян","癸":"Инь"}
ZHI_RU = {"子":"Цзы (Крыса)","丑":"Чоу (Бык)","寅":"Инь (Тигр)","卯":"Мао (Кролик)",
          "辰":"Чэнь (Дракон)","巳":"Сы (Змея)","午":"У (Лошадь)","未":"Вэй (Коза)",
          "申":"Шэнь (Обезьяна)","酉":"Ю (Петух)","戌":"Сюй (Собака)","亥":"Хай (Свинья)"}
ZHI_ANIMAL = {"子":"Крыса","丑":"Бык","寅":"Тигр","卯":"Кролик","辰":"Дракон","巳":"Змея",
              "午":"Лошадь","未":"Коза","申":"Обезьяна","酉":"Петух","戌":"Собака","亥":"Свинья"}
ZHI_ELEM = {"子":"Вода","丑":"Земля","寅":"Дерево","卯":"Дерево","辰":"Земля","巳":"Огонь",
            "午":"Огонь","未":"Земля","申":"Металл","酉":"Металл","戌":"Земля","亥":"Вода"}
# Скрытые небесные стволы в земных ветвях
HIDDEN = {"子":["癸"],"丑":["己","癸","辛"],"寅":["甲","丙","戊"],"卯":["乙"],
          "辰":["戊","乙","癸"],"巳":["丙","戊","庚"],"午":["丁","己"],"未":["己","丁","乙"],
          "申":["庚","壬","戊"],"酉":["辛"],"戌":["戊","辛","丁"],"亥":["壬","甲"]}
SHISHEN_RU = {"比肩":"Плечо к плечу (Би Цзянь)","劫财":"Грабитель богатства (Цзе Цай)",
              "食神":"Бог еды (Ши Шэнь)","伤官":"Ранящий чиновник (Шан Гуань)",
              "偏财":"Косвенное богатство (Пянь Цай)","正财":"Прямое богатство (Чжэн Цай)",
              "七杀":"Семь убийств (Ци Ша)","正官":"Прямой чиновник (Чжэн Гуань)",
              "偏印":"Косвенная печать (Пянь Инь)","正印":"Прямая печать (Чжэн Инь)","日主":"Хозяин дня"}

GAN_ORDER = "甲乙丙丁戊己庚辛壬癸"
ZHI_ORDER = "子丑寅卯辰巳午未申酉戌亥"
XUN_KONG = {0:("戌","亥"),1:("申","酉"),2:("午","未"),3:("辰","巳"),4:("寅","卯"),5:("子","丑")}
TRINE = {"申":"水","子":"水","辰":"水","寅":"火","午":"火","戌":"火",
         "巳":"金","酉":"金","丑":"金","亥":"木","卯":"木","未":"木"}
TAOHUA = {"水":"酉","火":"卯","金":"午","木":"子"}
YIMA   = {"水":"寅","火":"申","金":"亥","木":"巳"}
TIANYI = {"甲":["丑","未"],"戊":["丑","未"],"庚":["丑","未"],"乙":["子","申"],"己":["子","申"],
          "丙":["亥","酉"],"丁":["亥","酉"],"壬":["巳","卯"],"癸":["巳","卯"],"辛":["寅","午"]}

def kong_wang(day_gz):
    """Пустые ветви (кун-ван) по декаде сюнь столпа дня."""
    g, z = GAN_ORDER.index(day_gz[0]), ZHI_ORDER.index(day_gz[1])
    jiazi = (z - g) % 12  # позиция начала сюнь
    xun = {0:0, 10:1, 8:2, 6:3, 4:4, 2:5}[jiazi]
    return XUN_KONG[xun]

def stars(day_gz, year_zhi, all_zhi):
    """Символические звёзды: где они и есть ли в карте."""
    dz = day_gz[1]
    out = {}
    for base_name, base in (("от ветви дня", dz), ("от ветви года", year_zhi)):
        th, ym = TAOHUA[TRINE[base]], YIMA[TRINE[base]]
        out.setdefault("персиковый_цвет_таохуа", {})[base_name] = {
            "ветвь": f"{ZHI_RU[th]}", "в_карте": th in all_zhi}
        out.setdefault("небесный_конь_има", {})[base_name] = {
            "ветвь": f"{ZHI_RU[ym]}", "в_карте": ym in all_zhi}
    nobles = TIANYI[day_gz[0]]
    out["дворянин_тяньи"] = {"ветви": [ZHI_RU[n] for n in nobles],
                             "в_карте": [ZHI_RU[n] for n in nobles if n in all_zhi]}
    return out

def pillar(gz, shishen_gan=None, shishen_zhi=None):
    gan, zhi = gz[0], gz[1]
    d = {
        "иероглифы": gz,
        "небесный_ствол": GAN_RU[gan],
        "земная_ветвь": ZHI_RU[zhi],
        "животное": ZHI_ANIMAL[zhi],
        "стихия_ствола": GAN_ELEM[gan],
        "инь_ян_ствола": GAN_YINYANG[gan],
        "стихия_ветви": ZHI_ELEM[zhi],
        "скрытые_стволы": [GAN_RU[h] for h in HIDDEN[zhi]],
    }
    if shishen_gan: d["десять_богов_ствол"] = SHISHEN_RU.get(shishen_gan, shishen_gan)
    if shishen_zhi: d["десять_богов_ветвь"] = [SHISHEN_RU.get(s, s) for s in shishen_zhi]
    return d

def count_elements(pillars_gz, include_hidden=True):
    cnt = {"Дерево":0,"Огонь":0,"Земля":0,"Металл":0,"Вода":0}
    for gz in pillars_gz:
        cnt[GAN_ELEM[gz[0]]] += 1
        cnt[ZHI_ELEM[gz[1]]] += 1
        if include_hidden:
            for i, h in enumerate(HIDDEN[gz[1]]):
                cnt[GAN_ELEM[h]] += 0.5 if i == 0 else 0.25
    return cnt

def main():
    p = argparse.ArgumentParser()
    p.add_argument("date")
    p.add_argument("time", nargs="?", default=None)
    p.add_argument("--gender", choices=["m","f"], default="f")
    p.add_argument("--lon", type=float, default=None, help="долгота места, восточная положительная")
    p.add_argument("--utc-offset", type=float, default=None, help="смещение часов от UTC на момент рождения")
    args = p.parse_args()

    try:
        y, m, d = map(int, args.date.split("-"))
        import datetime as _dt; _dt.date(y, m, d)
    except Exception:
        print(json.dumps({"ошибка": f"Некорректная дата: {args.date}. Формат ГГГГ-ММ-ДД."}, ensure_ascii=False)); sys.exit(1)
    has_time = args.time is not None
    solar_note = ""
    boundary_warning = ""
    if has_time:
        try:
            hh, mm = map(int, args.time.split(":"))
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            print(json.dumps({"ошибка": f"Некорректное время: {args.time}. Формат ЧЧ:ММ."}, ensure_ascii=False)); sys.exit(1)
        if (args.lon is None) != (args.utc_offset is None):
            print(json.dumps({"ошибка": "--lon и --utc-offset работают только вместе: передай оба или ни одного."}, ensure_ascii=False)); sys.exit(1)
        if args.lon is not None and args.utc_offset is not None:
            y, m, d, hh, mm, shift = to_solar_time(y, m, d, hh, mm, args.lon, args.utc_offset)
            solar_note = f"Время приведено к истинному солнечному: сдвиг {shift:+d} мин, солнечное {hh:02d}:{mm:02d}."
        # Граница двухчасового интервала (нечётный час): предупредить, если ±20 мин
        mins = hh * 60 + mm
        for b in range(60, 24*60, 120):  # границы 01,03,...,23
            if abs(mins - b) <= 20 or abs(mins - (b - 24*60)) <= 20:
                boundary_warning = ("Время в пределах ±20 минут от границы двухчасового интервала — "
                                    "рассчитай ОБА варианта столпа часа и скажи об этом клиенту.")
                break
        if abs(mins - 23*60) <= 20 or mins <= 20:
            boundary_warning = boundary_warning or "Время у границы 23:00/01:00 — проверь оба варианта, включая смену суток."
    else:
        hh, mm = 12, 0  # полдень как заглушка; столп часа не выводим

    solar = Solar.fromYmdHms(y, m, d, hh, mm, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    pillars = {
        "год": pillar(ec.getYear(), ec.getYearShiShenGan(), ec.getYearShiShenZhi()),
        "месяц": pillar(ec.getMonth(), ec.getMonthShiShenGan(), ec.getMonthShiShenZhi()),
        "день": pillar(ec.getDay(), "日主", ec.getDayShiShenZhi()),
    }
    gz_list = [ec.getYear(), ec.getMonth(), ec.getDay()]
    if has_time:
        pillars["час"] = pillar(ec.getTime(), ec.getTimeShiShenGan(), ec.getTimeShiShenZhi())
        gz_list.append(ec.getTime())

    day_gan = ec.getDayGan()

    # Такт удачи (да юнь) — 10-летние периоды
    try:
        yun = ec.getYun(1 if args.gender == "m" else 0)
        dayun = []
        for du in yun.getDaYun()[:9]:
            if not du.getGanZhi():
                continue
            gz = du.getGanZhi()
            item = {"возраст_начала": du.getStartAge(), "год_начала": du.getStartYear()}
            if gz:
                item["столп"] = gz
                item["ствол"] = GAN_RU.get(gz[0], gz[0])
                item["ветвь"] = ZHI_RU.get(gz[1], gz[1])
            dayun.append(item)
    except Exception:
        dayun = []

    kw = kong_wang(ec.getDay())
    all_zhi = [gz[1] for gz in gz_list]
    kw_in_chart = [ZHI_RU[k] for k in kw if k in all_zhi]

    out = {
        "конвенции": "год по Личунь; месяц по солнечным терминам цзе; день меняется в полночь (поздний час Цзы относится к текущему дню); "
                     + ("время приведено к истинному солнечному" if solar_note else "время НЕ приводилось к солнечному (координаты не переданы)"),
        "дата_григорианская": f"{y:04d}-{m:02d}-{d:02d}" + (f" {args.time}" if has_time else " (время неизвестно)"),
        "дата_лунная": f"{lunar.getYearInChinese()} год, {lunar.getMonthInChinese()} месяц, {lunar.getDayInChinese()} день",
        "животное_года": ZHI_ANIMAL[ec.getYear()[1]],
        "хозяин_дня": {
            "ствол": GAN_RU[day_gan],
            "стихия": GAN_ELEM[day_gan],
            "инь_ян": GAN_YINYANG[day_gan],
        },
        "четыре_столпа": pillars,
        "на_инь": {"год": nayin(ec.getYearNaYin()), "месяц": nayin(ec.getMonthNaYin()),
                   "день": nayin(ec.getDayNaYin()), **({"час": nayin(ec.getTimeNaYin())} if has_time else {})},
        "баланс_стихий": count_elements(gz_list),
        "такты_удачи_да_юнь": dayun,
        "неочевидное": {
            "пустоты_кун_ван": {
                "пустые_ветви": [ZHI_RU[k] for k in kw],
                "пустые_ветви_в_карте": kw_in_chart or "нет — пустоты не задеты",
            },
            "символические_звёзды": stars(ec.getDay(), ec.getYear()[1], all_zhi),
        },
        "примечание": " ".join(x for x in [
            solar_note, boundary_warning,
            "" if has_time else "Время рождения не указано — столп часа опущен, точность тактов удачи снижена."
        ] if x),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
