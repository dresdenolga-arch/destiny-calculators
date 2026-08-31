"""Runs engine/bazi/scripts/bazi_calc.py as a subprocess and parses its JSON output."""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.services import geocode_service

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "engine" / "bazi" / "scripts" / "bazi_calc.py"
_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


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
