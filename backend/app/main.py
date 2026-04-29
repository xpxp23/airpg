from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_router, games_router, characters_router, actions_router
from app.routers.actions import cooperation_router

app = FastAPI(
    title="AI Async Narrative RPG",
    description="AI 叙事型多人异步跑团游戏 API",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(characters_router)
app.include_router(actions_router)
app.include_router(cooperation_router)


@app.get("/")
async def root():
    return {"message": "AI Async Narrative RPG API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
