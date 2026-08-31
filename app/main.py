from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import BasicAuthMiddleware
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
def api_matrix_html(date: str, name: str = "", child: bool = False):
    try:
        return matrix_service.render_html_page(date, name=name, child=child)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/bazi")
def api_bazi(req: BaziRequest):
    try:
        return bazi_service.compute(
            req.date, time=req.time, gender=req.gender,
            lon=req.lon, utc_offset=req.utc_offset,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/jyotish")
def api_jyotish(req: JyotishRequest):
    try:
        return jyotish_service.compute(
            req.date, utc_offset=req.utc_offset, time=req.time,
            lat=req.lat, lon=req.lon,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
