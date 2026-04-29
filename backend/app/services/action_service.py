import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Action, ActionStatus, ActionType, Character, Game, GameStatus, Event, EventType
from app.schemas.action import ActionCreate, CooperationCreate, ActionResponse, CooperationResponse
from app.services.ai_service import AIService
from app.services.game_service import GameService


class ActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.game_service = GameService(db)

    async def submit_action(self, game_id: str, user_id: str, data: ActionCreate) -> Action:
        # Validate game state
        game = await self.game_service.get_game(game_id)
        if not game or game.status != GameStatus.ACTIVE:
            raise ValueError("Game is not active")

        # Validate character
        character = await self.game_service.get_character(data.character_id)
        if not character or character.game_id != game_id:
            raise ValueError("Character not found in this game")
        if character.player_id != user_id:
            raise ValueError("This is not your character")
        if not character.is_alive:
            raise ValueError("Character is dead and cannot act")

        # Check if character already has pending action
        result = await self.db.execute(
            select(Action).where(
                Action.character_id == data.character_id,
                Action.status == ActionStatus.PENDING,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("Character already has a pending action")

        # Get current scene for AI evaluation
        current_scene = "未知场景"
        if game.ai_summary and "scenes" in game.ai_summary:
            scenes = game.ai_summary["scenes"]
            if scenes:
                current_scene = scenes[0].get("description", "未知场景")

        # Get chapter info
        chapter = game.current_chapter or 1
        chapter_title = ""
        chapter_goal = ""
        if game.ai_summary and "chapter_plan" in game.ai_summary:
            for cp in game.ai_summary["chapter_plan"]:
                if cp.get("chapter") == chapter:
                    chapter_title = cp.get("title", "")
                    chapter_goal = cp.get("goal", "")
                    break

        # AI evaluation - with fallback on failure
        try:
            eval_result = await self.ai_service.evaluate_action(
                action_text=data.action_text,
                scene=current_scene,
                character_status=character.status_effects or {},
                chapter=chapter,
                chapter_title=chapter_title,
                chapter_goal=chapter_goal,
            )
        except Exception:
            # Fallback if AI fails
            eval_result = {
                "public_snippet": f"{character.name}正在行动...",
                "wait_seconds": 60,
                "difficulty": "medium",
                "risk": "low",
            }

        wait_seconds = eval_result.get("wait_seconds", 60)
        now = datetime.utcnow()
        finish_at = now + timedelta(seconds=wait_seconds)

        action = Action(
            id=str(uuid.uuid4()),
            game_id=game_id,
            character_id=data.character_id,
            player_id=user_id,
            action_type=ActionType.NORMAL,
            input_text=data.action_text,
            public_snippet=eval_result.get("public_snippet", f"{character.name}正在行动..."),
            wait_seconds=wait_seconds,
            started_at=now,
            finish_at=finish_at,
            difficulty=eval_result.get("difficulty", "medium"),
            risk=eval_result.get("risk", "low"),
            status=ActionStatus.PENDING,
        )
        self.db.add(action)

        # Add event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.ACTION_START,
            data={
                "action_id": action.id,
                "character_id": character.id,
                "character_name": character.name,
                "public_snippet": action.public_snippet,
                "wait_seconds": wait_seconds,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def complete_action(self, action_id: str) -> Action:
        action = await self.get_action(action_id)
        if not action or action.status != ActionStatus.PENDING:
            raise ValueError("Action not found or not pending")

        game = await self.game_service.get_game(action.game_id)
        character = await self.game_service.get_character(action.character_id)

        # Generate narrative - with fallback on failure
        try:
            narrative_result = await self.ai_service.generate_narrative(
                action_text=action.input_text,
                character_name=character.name,
                wait_seconds=action.wait_seconds,
                difficulty=action.difficulty or "medium",
                risk=action.risk or "low",
            )
        except Exception:
            # Fallback if AI fails
            narrative_result = {
                "narrative": f"{character.name}完成了行动。",
                "outcome": "success",
                "effects": {},
                "chapter_progress": {"advance_chapter": False},
                "game_over": False,
                "importance": "medium",
            }

        # Update action
        action.status = ActionStatus.COMPLETED
        action.completed_at = datetime.utcnow()
        action.result_narrative = narrative_result.get("narrative", "")
        action.result_effects = narrative_result.get("effects", {})

        # Apply effects to character
        effects = narrative_result.get("effects", {})
        if effects:
            await self._apply_effects(character, effects)

        # Add result event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=action.game_id,
            type=EventType.ACTION_RESULT,
            data={
                "action_id": action.id,
                "character_id": character.id,
                "character_name": character.name,
                "narrative": action.result_narrative,
                "outcome": narrative_result.get("outcome", "success"),
                "importance": narrative_result.get("importance", "medium"),
            },
        )
        self.db.add(event)

        # Check chapter progress
        chapter_progress = narrative_result.get("chapter_progress", {})
        if chapter_progress.get("advance_chapter"):
            game.current_chapter = (game.current_chapter or 1) + 1
            chapter_event = Event(
                id=str(uuid.uuid4()),
                game_id=action.game_id,
                type=EventType.CHAPTER_ADVANCE,
                data={"chapter": game.current_chapter, "description": chapter_progress.get("progress_description", "")},
            )
            self.db.add(chapter_event)

        # Check game over
        if narrative_result.get("game_over"):
            await self.game_service.end_game(action.game_id, "story_completed")

        await self.db.commit()
        return action

    async def _apply_effects(self, character: Character, effects: dict):
        status = character.status_effects or {}

        # Health change
        health_change = effects.get("health_change", 0)
        if health_change:
            current_health = status.get("health", 100)
            status["health"] = max(0, min(100, current_health + health_change))
            if status["health"] <= 0:
                character.is_alive = False

        # Items
        new_items = effects.get("new_items", [])
        if new_items:
            items = status.get("items", [])
            items.extend(new_items)
            status["items"] = items

        lost_items = effects.get("lost_items", [])
        if lost_items:
            items = status.get("items", [])
            status["items"] = [i for i in items if i not in lost_items]

        # Status effects
        new_effects = effects.get("new_status_effects", [])
        if new_effects:
            injuries = status.get("injuries", [])
            injuries.extend(new_effects)
            status["injuries"] = injuries

        # Location change
        location_change = effects.get("location_change")
        if location_change:
            character.location = location_change

        character.status_effects = status

    async def submit_cooperation(self, game_id: str, user_id: str, data: CooperationCreate) -> Action:
        # Validate game state
        game = await self.game_service.get_game(game_id)
        if not game or game.status != GameStatus.ACTIVE:
            raise ValueError("Game is not active")

        # Validate helper character
        helper = await self.game_service.get_character(data.helper_character_id)
        if not helper or helper.game_id != game_id:
            raise ValueError("Helper character not found")
        if helper.player_id != user_id:
            raise ValueError("This is not your character")
        if not helper.is_alive:
            raise ValueError("Character is dead")

        # Check helper doesn't have pending action
        result = await self.db.execute(
            select(Action).where(
                Action.character_id == data.helper_character_id,
                Action.status == ActionStatus.PENDING,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("Character already has a pending action")

        # Validate target action
        target_action = await self.get_action(data.target_action_id)
        if not target_action or target_action.status != ActionStatus.PENDING:
            raise ValueError("Target action not found or not pending")
        if target_action.game_id != game_id:
            raise ValueError("Target action is not in this game")

        # Get target character
        target_char = await self.game_service.get_character(target_action.character_id)

        # Calculate elapsed time
        now = datetime.utcnow()
        elapsed = (now - target_action.started_at).total_seconds()
        remaining = (target_action.finish_at - now).total_seconds()

        if remaining <= 0:
            raise ValueError("Target action already completed")

        # AI evaluation for cooperation
        eval_result = await self.ai_service.evaluate_cooperation(
            cooperation_text=data.cooperation_text,
            helper_name=helper.name,
            helper_status=str(helper.status_effects),
            target_name=target_char.name,
            target_action=target_action.input_text,
            elapsed_seconds=int(elapsed),
            total_wait_seconds=target_action.wait_seconds,
            remaining_seconds=int(remaining),
        )

        coop_wait = eval_result.get("cooperation_wait_seconds", 60)
        reduction_percent = eval_result.get("target_time_reduction_percent", 50)
        coop_finish = now + timedelta(seconds=coop_wait)

        # Create cooperation action
        cooperation = Action(
            id=str(uuid.uuid4()),
            game_id=game_id,
            character_id=data.helper_character_id,
            player_id=user_id,
            action_type=ActionType.COOPERATION,
            input_text=data.cooperation_text,
            public_snippet=eval_result.get("cooperation_narrative", f"{helper.name}正在协助{target_char.name}..."),
            wait_seconds=coop_wait,
            started_at=now,
            finish_at=coop_finish,
            difficulty="medium",
            risk=eval_result.get("risk_to_helper", "low"),
            is_cooperation=True,
            cooperation_target_id=data.target_action_id,
            status=ActionStatus.PENDING,
        )
        self.db.add(cooperation)

        # Add cooperation start event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.COOPERATION_START,
            data={
                "cooperation_id": cooperation.id,
                "helper_id": helper.id,
                "helper_name": helper.name,
                "target_id": target_char.id,
                "target_name": target_char.name,
                "public_snippet": cooperation.public_snippet,
                "wait_seconds": coop_wait,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(cooperation)
        return cooperation

    async def complete_cooperation(self, cooperation_id: str) -> tuple[Action, Action]:
        cooperation = await self.get_action(cooperation_id)
        if not cooperation or cooperation.status != ActionStatus.PENDING:
            raise ValueError("Cooperation not found or not pending")

        # Get target action
        target_action = await self.get_action(cooperation.cooperation_target_id)
        if not target_action:
            raise ValueError("Target action not found")

        helper = await self.game_service.get_character(cooperation.character_id)
        target_char = await self.game_service.get_character(target_action.character_id)

        # Calculate time reduction
        now = datetime.utcnow()
        remaining = (target_action.finish_at - now).total_seconds()

        if remaining > 0:
            # Get reduction from modifiers
            reduction_percent = 50  # default
            for mod in cooperation.modifiers:
                if mod.get("type") == "cooperation":
                    reduction_percent = mod.get("reduction_percent", 50)
                    break

            new_remaining = remaining * (1 - reduction_percent / 100)
            target_action.finish_at = now + timedelta(seconds=max(new_remaining, 5))

            # Add modifier to target action
            target_action.modifiers = target_action.modifiers + [{
                "type": "cooperation",
                "by_character": cooperation.character_id,
                "by_character_name": helper.name,
                "reduction_percent": reduction_percent,
                "at": now.isoformat(),
            }]

        # Complete cooperation action
        cooperation.status = ActionStatus.COMPLETED
        cooperation.completed_at = now
        cooperation.result_narrative = f"{helper.name}成功协助了{target_char.name}，行动进度加快了！"

        # Add event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=cooperation.game_id,
            type=EventType.COOPERATION_RESULT,
            data={
                "cooperation_id": cooperation.id,
                "helper_id": helper.id,
                "helper_name": helper.name,
                "target_id": target_char.id,
                "target_name": target_char.name,
                "narrative": cooperation.result_narrative,
                "target_new_finish_at": target_action.finish_at.isoformat(),
            },
        )
        self.db.add(event)
        await self.db.commit()
        return cooperation, target_action

    async def get_action(self, action_id: str) -> Action | None:
        result = await self.db.execute(select(Action).where(Action.id == action_id))
        return result.scalar_one_or_none()

    async def get_pending_actions(self, game_id: str) -> list[Action]:
        result = await self.db.execute(
            select(Action)
            .where(Action.game_id == game_id, Action.status == ActionStatus.PENDING)
            .order_by(Action.finish_at)
        )
        return list(result.scalars().all())

    async def get_game_actions(self, game_id: str, status: str | None = None, limit: int = 50) -> list[Action]:
        query = select(Action).where(Action.game_id == game_id)
        if status:
            query = query.where(Action.status == status)
        query = query.order_by(Action.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def cancel_action(self, action_id: str, user_id: str) -> Action:
        action = await self.get_action(action_id)
        if not action:
            raise ValueError("Action not found")
        if action.player_id != user_id:
            raise ValueError("Not your action")
        if action.status != ActionStatus.PENDING:
            raise ValueError("Action is not pending")

        action.status = ActionStatus.CANCELLED
        await self.db.commit()
        return action

    def action_to_response(self, action: Action) -> ActionResponse:
        now = datetime.utcnow()
        remaining = None
        if action.status == ActionStatus.PENDING and action.finish_at:
            remaining = max(0, (action.finish_at - now).total_seconds())

        return ActionResponse(
            id=action.id,
            game_id=action.game_id,
            character_id=action.character_id,
            player_id=action.player_id,
            action_type=action.action_type.value if action.action_type else "normal",
            input_text=action.input_text,
            public_snippet=action.public_snippet,
            wait_seconds=action.wait_seconds,
            started_at=action.started_at,
            finish_at=action.finish_at,
            completed_at=action.completed_at,
            result_narrative=action.result_narrative,
            result_effects=action.result_effects,
            difficulty=action.difficulty,
            risk=action.risk,
            is_cooperation=action.is_cooperation,
            cooperation_target_id=action.cooperation_target_id,
            modifiers=action.modifiers or [],
            status=action.status.value if action.status else "pending",
            created_at=action.created_at,
            remaining_seconds=remaining,
        )
