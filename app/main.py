from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import BasicAuthMiddleware
from app.render import bazi_render, jyotish_render
from app.render.common import error_page
from app.services import bazi_service, jyotish_service, matrix_service

app = FastAPI(title="Даты рождения — три системы")
app.add_middleware(BasicAuthMiddleware)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class MatrixRequest(BaseModel):
    date: str  # ДД.ММ.ГГГГ
    child: bool = False
    partner_date: Optional[str] = None


class BaziRequest(BaseModel):
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    gender: str = "f"
    lon: Optional[float] = None
    utc_offset: Optional[float] = None


class JyotishRequest(BaseModel):
    date: str  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM
    lat: Optional[float] = None
    lon: Optional[float] = None
    utc_offset: float


@app.post("/api/matrix")
def api_matrix(req: MatrixRequest):
    try:
        return matrix_service.compute(req.date, child=req.child, partner_date=req.partner_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/matrix/html", response_class=HTMLResponse)
def api_matrix_html(date: str, name: str = "", child: bool = False,
                     partner_date: Optional[str] = None, partner_name: str = ""):
    try:
        if partner_date:
            return matrix_service.render_compatibility_html_page(
                date, partner_date, name1=name, name2=partner_name, child=child,
            )
        return matrix_service.render_html_page(date, name=name, child=child)
    except ValueError as exc:
        return HTMLResponse(error_page(str(exc)), status_code=400)


@app.post("/api/bazi")
def api_bazi(req: BaziRequest):
    try:
        return bazi_service.compute(
            req.date, time=req.time, gender=req.gender,
            lon=req.lon, utc_offset=req.utc_offset,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/bazi/html", response_class=HTMLResponse)
def api_bazi_html(date: str, name: str = "", time: Optional[str] = None,
                   gender: str = "f", lon: Optional[float] = None,
                   utc_offset: Optional[float] = None):
    try:
        data = bazi_service.compute(date, time=time, gender=gender, lon=lon, utc_offset=utc_offset)
        return bazi_render.build_page(data, person=name)
    except RuntimeError as exc:
        return HTMLResponse(error_page(str(exc)), status_code=400)


@app.post("/api/jyotish")
def api_jyotish(req: JyotishRequest):
    try:
        return jyotish_service.compute(
            req.date, utc_offset=req.utc_offset, time=req.time,
            lat=req.lat, lon=req.lon,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/jyotish/html", response_class=HTMLResponse)
def api_jyotish_html(date: str, utc_offset: float, name: str = "",
                      time: Optional[str] = None, lat: Optional[float] = None,
                      lon: Optional[float] = None):
    try:
        data = jyotish_service.compute(date, utc_offset=utc_offset, time=time, lat=lat, lon=lon)
        return jyotish_render.build_page(data, person=name)
    except RuntimeError as exc:
        return HTMLResponse(error_page(str(exc)), status_code=400)


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
