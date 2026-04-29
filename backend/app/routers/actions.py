from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.action import ActionCreate, CooperationCreate, ActionResponse, ActionListResponse, CooperationResponse
from app.services.action_service import ActionService
from app.services.game_service import GameService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/games/{game_id}/actions", tags=["actions"])


@router.post("", response_model=ActionResponse, status_code=201)
async def submit_action(
    game_id: str,
    data: ActionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action_service = ActionService(db)
    try:
        action = await action_service.submit_action(game_id, current_user.id, data)
        return action_service.action_to_response(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ActionListResponse)
async def list_actions(
    game_id: str,
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action_service = ActionService(db)
    game_service = GameService(db)

    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    actions = await action_service.get_game_actions(game_id, status, limit)
    return ActionListResponse(
        actions=[action_service.action_to_response(a) for a in actions]
    )


@router.get("/{action_id}", response_model=ActionResponse)
async def get_action(
    game_id: str,
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action_service = ActionService(db)
    action = await action_service.get_action(action_id)
    if not action or action.game_id != game_id:
        raise HTTPException(status_code=404, detail="Action not found")
    return action_service.action_to_response(action)


@router.delete("/{action_id}", status_code=204)
async def cancel_action(
    game_id: str,
    action_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action_service = ActionService(db)
    try:
        await action_service.cancel_action(action_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Cooperation endpoint (separate from actions)
cooperation_router = APIRouter(prefix="/api/v1/games/{game_id}/cooperation", tags=["cooperation"])


@cooperation_router.post("", response_model=ActionResponse, status_code=201)
async def submit_cooperation(
    game_id: str,
    data: CooperationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action_service = ActionService(db)
    try:
        action = await action_service.submit_cooperation(game_id, current_user.id, data)
        return action_service.action_to_response(action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
