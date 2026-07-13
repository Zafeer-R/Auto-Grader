from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import dev, grading, lti

app = FastAPI(title="Auto-Grader", version="0.1.0")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(lti.router)
app.include_router(grading.router)

if settings.debug:
    app.include_router(dev.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
