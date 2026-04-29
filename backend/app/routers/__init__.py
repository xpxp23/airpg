from app.routers.auth import router as auth_router
from app.routers.games import router as games_router
from app.routers.characters import router as characters_router
from app.routers.actions import router as actions_router

__all__ = ["auth_router", "games_router", "characters_router", "actions_router"]
