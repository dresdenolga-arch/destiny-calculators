"""Runs engine/bazi/scripts/bazi_calc.py as a subprocess and parses its JSON output."""
import json
import os
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "engine" / "bazi" / "scripts" / "bazi_calc.py"
_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def compute(date: str, time: str | None = None, gender: str = "f",
            lon: float | None = None, utc_offset: float | None = None) -> dict:
    """date: YYYY-MM-DD, time: HH:MM or None."""
    args = [sys.executable, str(_SCRIPT), date]
    if time:
        args.append(time)
    args += ["--gender", gender]
    if lon is not None and utc_offset is not None:
        args += ["--lon", str(lon), "--utc-offset", str(utc_offset)]

    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=_ENV)
    if not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "Пустой ответ от bazi_calc.py")
    return json.loads(proc.stdout)
