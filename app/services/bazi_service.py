"""Runs engine/bazi/scripts/bazi_calc.py as a subprocess and parses its JSON output."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from app.services import geocode_service

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "engine" / "bazi" / "scripts" / "bazi_calc.py"
_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def _run(date: str, time: str | None, gender: str,
          lon: float | None, utc_offset: float | None) -> dict:
    args = [sys.executable, str(_SCRIPT), date]
    if time:
        args.append(time)
    args += ["--gender", gender]
    if lon is not None and utc_offset is not None:
        args += ["--lon", str(lon), "--utc-offset", str(utc_offset)]

    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=_ENV)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "Пустой ответ от bazi_calc.py")
    data = json.loads(proc.stdout)
    if "ошибка" in data:
        raise RuntimeError(data["ошибка"])
    return data


def _find_alt_hour_pillar(date: str, time: str, gender: str,
                           lon: float | None, utc_offset: float | None,
                           original_pillar: str | None) -> dict | None:
    """Столп часа пограничный (±20 мин от границы двухчасового интервала):
    сдвигаем время рождения на 45 минут в обе стороны и смотрим, получится
    ли другой столп часа — это и есть "второй вариант", о котором предупреждает
    сам скрипт. Возвращает столп часа второго варианта или None, если такого
    нет (значит время было пограничным не по этой причине)."""
    base = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    for delta in (45, -45):
        shifted = base + timedelta(minutes=delta)
        try:
            candidate = _run(shifted.strftime("%Y-%m-%d"), shifted.strftime("%H:%M"),
                              gender, lon, utc_offset)
        except RuntimeError:
            continue
        pillar = candidate.get("четыре_столпа", {}).get("час")
        if pillar and pillar.get("иероглифы") != original_pillar:
            return pillar
    return None


def compute(date: str, time: str | None = None, gender: str = "f",
            lon: float | None = None, utc_offset: float | None = None,
            city: str | None = None) -> dict:
    """date: YYYY-MM-DD, time: HH:MM or None.

    If city is given and lon/utc_offset weren't provided manually, they're
    resolved from the city (geocoding + historical timezone lookup).
    """
    if city and time and (lon is None or utc_offset is None):
        birth_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        try:
            loc = geocode_service.resolve_location(city, birth_dt)
        except ValueError as exc:
            raise RuntimeError(str(exc))
        if lon is None:
            lon = loc["lon"]
        if utc_offset is None:
            utc_offset = loc["utc_offset"]

    result = _run(date, time, gender, lon, utc_offset)

    if time and "границы" in result.get("примечание", ""):
        original_pillar = result.get("четыре_столпа", {}).get("час", {}).get("иероглифы")
        alt = _find_alt_hour_pillar(date, time, gender, lon, utc_offset, original_pillar)
        if alt:
            result["альтернативный_столп_часа"] = alt

    return result
