"""Wraps the Matrix of Destiny engine (engine/matrix/scripts) for the API layer."""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "engine" / "matrix" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import calculate as _calc  # noqa: E402
import render_html as _render  # noqa: E402


def compute(date: str, child: bool = False, partner_date: str | None = None) -> dict:
    """Same shape as `calculate.py`'s CLI JSON output, computed in-process."""
    day, month, year = _calc.parse_date(date)
    person = _calc.calculate(day, month, year, child=child)

    if partner_date:
        p_day, p_month, p_year = _calc.parse_date(partner_date)
        partner = _calc.calculate(p_day, p_month, p_year, child=child)
        person["hidden_layers"] = _calc.hidden_layers(person, year)
        partner["hidden_layers"] = _calc.hidden_layers(partner, p_year)
        result = {
            "mode": "compatibility",
            "person_1": person,
            "person_2": partner,
            "comparison": _calc.compare(person, partner),
        }
        if child:
            result["child_note"] = _calc.CHILD_NOTE
        return result

    result = {"mode": "child" if child else "single", **person}
    result["hidden_layers"] = _calc.hidden_layers(person, year)
    if child:
        result["child_note"] = _calc.CHILD_NOTE
    return result


def render_html_page(date: str, name: str = "", child: bool = False) -> str:
    day, month, year = _calc.parse_date(date)
    matrix = _calc.calculate(day, month, year, child=child)
    return _render.build_page(matrix, name, child)


def render_compatibility_html_page(date: str, partner_date: str, name1: str = "",
                                    name2: str = "", child: bool = False) -> str:
    day, month, year = _calc.parse_date(date)
    p_day, p_month, p_year = _calc.parse_date(partner_date)
    person1 = _calc.calculate(day, month, year, child=child)
    person2 = _calc.calculate(p_day, p_month, p_year, child=child)
    comparison = _calc.compare(person1, person2)
    return _render.build_compat_page(person1, person2, name1, name2, comparison, child)
