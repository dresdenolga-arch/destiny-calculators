"""City name -> coordinates + historical UTC offset at a given moment.

Geocoding via OpenStreetMap Nominatim (free, no key, but rate-limited to
~1 req/sec and requires an identifying User-Agent per their usage policy).
Timezone lookup is fully offline (timezonefinder), and the UTC offset is
computed from the IANA tz database for the actual birth date/time — this
correctly accounts for historical rules (DST, Soviet decree time, etc.)
instead of guessing.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from timezonefinder import TimezoneFinder

_tf = TimezoneFinder()
_USER_AGENT = "destiny-calculators/1.0 (birth-chart calculator; contact: dresdenolga@gmail.com)"


def geocode_city(city: str) -> dict:
    params = urllib.parse.urlencode({"q": city, "format": "json", "limit": 1, "accept-language": "ru"})
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError(f"не удалось связаться со службой геокодирования: {exc}")

    if not results:
        raise ValueError(
            f"город «{city}» не найден — проверьте написание или введите координаты вручную"
        )
    top = results[0]
    return {"lat": float(top["lat"]), "lon": float(top["lon"]), "display_name": top["display_name"]}


def resolve_location(city: str, birth_dt: datetime) -> dict:
    """birth_dt: naive datetime of birth (local, at the place in question)."""
    place = geocode_city(city)
    tz_name = _tf.timezone_at(lat=place["lat"], lng=place["lon"])
    if not tz_name:
        raise ValueError(f"не удалось определить часовой пояс для «{city}» — введите координаты вручную")

    aware = birth_dt.replace(tzinfo=ZoneInfo(tz_name))
    utc_offset = aware.utcoffset().total_seconds() / 3600

    return {
        "lat": place["lat"],
        "lon": place["lon"],
        "timezone": tz_name,
        "utc_offset": utc_offset,
        "display_name": place["display_name"],
    }
