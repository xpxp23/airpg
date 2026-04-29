from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.character import CharacterCreate, CharacterResponse
from app.services.game_service import GameService
from app.dependencies import get_current_user
from app.models.user import User
import uuid

router = APIRouter(prefix="/api/v1/games/{game_id}/characters", tags=["characters"])


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(
    game_id: str,
    data: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status.value != "lobby":
        raise HTTPException(status_code=400, detail="Game is not in lobby state")

    # Check if user already has character in this game
    existing = await game_service.get_player_character(game_id, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Already have a character in this game")

    from app.models import Character
    character = Character(
        id=str(uuid.uuid4()),
        game_id=game_id,
        player_id=current_user.id,
        name=data.name,
        description=data.description,
        background=data.background,
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)

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


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    game_id: str,
    character_id: str,
    data: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game_service = GameService(db)
    character = await game_service.get_character(character_id)
    if not character or character.game_id != game_id:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.player_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your character")

    character.name = data.name
    if data.description:
        character.description = data.description
    if data.background:
        character.background = data.background

    await db.commit()
    await db.refresh(character)

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
