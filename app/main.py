from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Base, engine
from .routes import router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/manus-routes.json")
def route_manifest() -> dict:
    return {"routes": [{"path": "/", "title": "Adrobot Campaign Console"}]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")
