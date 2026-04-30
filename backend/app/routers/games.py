import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database import get_db, async_session
from app.schemas.game import GameCreate, GameJoin, GameResponse, GameDetailResponse, GameStart
from app.schemas.character import CharacterResponse
from app.schemas.event import EventResponse, EventListResponse
from app.services.game_service import GameService
from app.dependencies import get_current_user
from app.models.user import User
from app.models.game import GameStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/games", tags=["games"])


def _game_to_response(game, player_count: int = 0) -> GameResponse:
    return GameResponse(
        id=game.id,
        creator_id=game.creator_id,
        title=game.title,
        status=game.status.value if hasattr(game.status, "value") else game.status,
        current_chapter=game.current_chapter,
        max_players=game.max_players,
        is_public=game.is_public,
        game_mode=game.game_mode,
        invite_code=game.invite_code,
        started_at=game.started_at,
        finished_at=game.finished_at,
        created_at=game.created_at,
        player_count=player_count,
        parse_status=game.parse_status.value if hasattr(game.parse_status, "value") else game.parse_status,
    )


async def _parse_story_background(game_id: str):
    """Run story parsing in background, independent of the HTTP request."""
    async with async_session() as db:
        try:
            game_service = GameService(db)
            await game_service.parse_story(game_id)
        except Exception:
            logger.exception("Background story parsing failed for game %s", game_id)


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    data: GameCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.create_game(current_user.id, data)
    # Fire-and-forget: parse story in background, return immediately
    asyncio.create_task(_parse_story_background(game.id))
    return _game_to_response(game)


@router.get("", response_model=list[GameResponse])
async def list_games(
    scope: str = Query("public", regex="^(public|mine)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    if scope == "mine":
        games_with_counts = await game_service.list_user_games(current_user.id)
    else:
        games_with_counts = await game_service.list_public_games(limit, offset)
    return [_game_to_response(g, player_count=cnt) for g, cnt in games_with_counts]


@router.get("/{game_id}", response_model=GameDetailResponse)
async def get_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    player_count = await game_service.get_player_count(game_id)

    return GameDetailResponse(
        id=game.id,
        creator_id=game.creator_id,
        title=game.title,
        status=game.status.value if hasattr(game.status, "value") else game.status,
        current_chapter=game.current_chapter,
        max_players=game.max_players,
        is_public=game.is_public,
        game_mode=game.game_mode,
        invite_code=game.invite_code,
        started_at=game.started_at,
        finished_at=game.finished_at,
        created_at=game.created_at,
        uploaded_story=game.uploaded_story,
        ai_summary=game.ai_summary,
        parse_status=game.parse_status.value if hasattr(game.parse_status, "value") else game.parse_status,
        parse_error=game.parse_error,
        duration_hint=game.duration_hint,
        target_duration_minutes=game.target_duration_minutes,
        player_count=player_count,
    )


@router.post("/{game_id}/join", response_model=CharacterResponse)
async def join_game(
    game_id: str,
    data: GameJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    try:
        character = await game_service.join_game(game_id, current_user.id, data.character_id)
        return CharacterResponse(
            id=character.id,
            game_id=character.game_id,
            player_id=character.player_id,
            name=character.name,
            description=character.description,
            background=character.background,
            status_effects=character.status_effects or {},
            location=character.location,
            is_alive=character.is_alive,
            created_at=character.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/start", response_model=GameResponse)
async def start_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    try:
        game = await game_service.start_game(game_id, current_user.id)
        return _game_to_response(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    try:
        await game_service.leave_game(game_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/disband", status_code=status.HTTP_204_NO_CONTENT)
async def disband_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    try:
        await game_service.disband_game(game_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/end", response_model=GameResponse)
async def end_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can end the game")
    if game.status not in (GameStatus.ACTIVE, GameStatus.PAUSED):
        raise HTTPException(status_code=400, detail="Game is not active")
    try:
        game = await game_service.end_game(game_id, "房主结束了游戏")
        return _game_to_response(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{game_id}/events", response_model=EventListResponse)
async def get_events(
    game_id: str,
    since: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    events = await game_service.get_game_events(game_id, since, limit)
    return EventListResponse(
        events=[
            EventResponse(
                id=e.id,
                game_id=e.game_id,
                type=e.type.value if hasattr(e.type, "value") else e.type,
                timestamp=e.timestamp,
                data=e.data,
                is_visible=e.is_visible,
                created_at=e.created_at,
            )
            for e in events
        ],
        has_more=len(events) == limit,
    )


@router.get("/{game_id}/characters", response_model=list[CharacterResponse])
async def get_characters(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    characters = await game_service.get_game_characters(game_id)
    return [
        CharacterResponse(
            id=c.id,
            game_id=c.game_id,
            player_id=c.player_id,
            name=c.name,
            description=c.description,
            background=c.background,
            status_effects=c.status_effects or {},
            location=c.location,
            is_alive=c.is_alive,
            created_at=c.created_at,
        )
        for c in characters
    ]


@router.post("/{game_id}/retry-parse", response_model=GameResponse)
async def retry_parse_story(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can retry parsing")

    asyncio.create_task(_parse_story_background(game.id))
    return _game_to_response(game)
