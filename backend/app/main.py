from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.websites import router as websites_router
from app.database import get_db

app = FastAPI(title="AI Popup Generator API", version="0.1.0")
app.include_router(auth_router)
app.include_router(websites_router)


@app.get("/health", tags=["health"])
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}