from pathlib import Path

from app.config import get_settings
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.popups import router as popups_router
from app.api.public import router as public_router
from app.api.websites import router as websites_router
from app.database import get_db

app = FastAPI(title="AI Popup Generator API", version="0.1.0")
app.include_router(auth_router)
app.include_router(popups_router)
app.include_router(public_router)
app.include_router(websites_router)
media_dir = get_settings().media_dir
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")
widget_script = Path(__file__).resolve().parents[2] / "widget" / "popup.js"
widget_test_page = Path(__file__).resolve().parents[2] / "frontend" / "public" / "widget-test.html"


@app.get("/widget.js", include_in_schema=False)
def serve_widget() -> FileResponse:
    return FileResponse(widget_script, media_type="application/javascript")


@app.get("/widget-test.html", include_in_schema=False)
def serve_widget_test_page() -> FileResponse:
    return FileResponse(widget_test_page, media_type="text/html")


@app.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}