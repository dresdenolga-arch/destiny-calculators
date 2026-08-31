"""Runs engine/jyotish/scripts/jyotish_calc.py as a subprocess and parses its JSON output.

Requires the `pyswisseph` package, which needs a C compiler to build on Windows
(Microsoft C++ Build Tools) since no prebuilt wheel exists for this platform.
Until it's installed, compute() raises RuntimeError with that explanation.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.services import geocode_service

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "engine" / "jyotish" / "scripts" / "jyotish_calc.py"
_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def compute(date: str, utc_offset: float | None = None, time: str | None = None,
            lat: float | None = None, lon: float | None = None,
            city: str | None = None) -> dict:
    """date: YYYY-MM-DD, time: HH:MM or None.

    If city is given and lat/lon/utc_offset weren't provided manually,
    they're resolved from the city (geocoding + historical timezone lookup).
    """
    if city and (lat is None or lon is None or utc_offset is None):
        birth_dt = datetime.strptime(f"{date} {time or '12:00'}", "%Y-%m-%d %H:%M")
        try:
            loc = geocode_service.resolve_location(city, birth_dt)
        except ValueError as exc:
            raise RuntimeError(str(exc))
        if lat is None:
            lat = loc["lat"]
        if lon is None:
            lon = loc["lon"]
        if utc_offset is None:
            utc_offset = loc["utc_offset"]

    if utc_offset is None:
        raise RuntimeError("нужен город рождения либо смещение от UTC вручную")

    args = [sys.executable, str(_SCRIPT), date]
    if time:
        args.append(time)
    if lat is not None:
        args += ["--lat", str(lat)]
    if lon is not None:
        args += ["--lon", str(lon)]
    args += ["--utc-offset", str(utc_offset)]

    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=_ENV)
    if "ModuleNotFoundError" in proc.stderr and "swisseph" in proc.stderr:
        raise RuntimeError(
            "Джйотиш-движку нужен пакет pyswisseph, который не установлен: "
            "на Windows у него нет готового wheel, нужен компилятор "
            "(Microsoft C++ Build Tools) для сборки из исходников."
        )
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "Пустой ответ от jyotish_calc.py")
    data = json.loads(proc.stdout)
    if "ошибка" in data:
        raise RuntimeError(data["ошибка"])
    return data
