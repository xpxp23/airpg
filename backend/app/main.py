from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_router, games_router, characters_router, actions_router
from app.routers.actions import cooperation_router
from app.routers.admin import router as admin_router
from app.database import engine, Base
from app.config import apply_admin_overrides, refresh_settings_if_changed
from app.models import *  # noqa: F401 - ensure all models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (safety net for fresh deployments)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Load admin settings overrides from JSON file
    apply_admin_overrides()
    yield


class AdminSettingsMiddleware(BaseHTTPMiddleware):
    """Refresh admin settings from disk if changed, ensuring all workers stay in sync."""
    async def dispatch(self, request: Request, call_next):
        refresh_settings_if_changed()
        return await call_next(request)


app = FastAPI(
    title="AI Async Narrative RPG",
    description="AI 叙事型多人异步跑团游戏 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(AdminSettingsMiddleware)

# CORS - allow all origins for API (uses Bearer token auth, not cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(characters_router)
app.include_router(actions_router)
app.include_router(cooperation_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "AI Async Narrative RPG API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
