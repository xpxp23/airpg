import uuid
import string
import random
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Game, GameStatus, Character, User, Event, EventType
from app.schemas.game import GameCreate, GameResponse, GameDetailResponse
from app.services.ai_service import AIService


class GameService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    def _generate_invite_code(self) -> str:
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=6))

    async def create_game(self, creator_id: str, data: GameCreate) -> Game:
        # Parse duration hint to minutes
        target_minutes = self._parse_duration(data.duration_hint)

        game = Game(
            id=str(uuid.uuid4()),
            creator_id=creator_id,
            title=data.title,
            uploaded_story=data.story_text,
            duration_hint=data.duration_hint,
            target_duration_minutes=target_minutes,
            max_players=data.max_players,
            is_public=data.is_public,
            invite_code=self._generate_invite_code(),
        )
        self.db.add(game)
        await self.db.commit()
        await self.db.refresh(game)
        return game

    def _parse_duration(self, hint: str | None) -> int | None:
        if not hint:
            return None
        hint = hint.lower()
        if "小时" in hint or "hour" in hint:
            try:
                num = int("".join(filter(str.isdigit, hint)))
                return num * 60
            except ValueError:
                return 480  # default 8 hours
        if "天" in hint or "day" in hint:
            try:
                num = int("".join(filter(str.isdigit, hint)))
                return num * 1440
            except ValueError:
                return 1440
        return 480

    async def parse_story(self, game_id: str) -> dict:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")

        summary = await self.ai_service.parse_story(game.uploaded_story, game.duration_hint)

        game.ai_summary = summary
        if summary.get("title") and not game.title:
            game.title = summary["title"]
        await self.db.commit()
        return summary

    async def get_game(self, game_id: str) -> Game | None:
        result = await self.db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one_or_none()

    async def get_game_with_details(self, game_id: str) -> Game | None:
        result = await self.db.execute(
            select(Game)
            .options(selectinload(Game.characters), selectinload(Game.events))
            .where(Game.id == game_id)
        )
        return result.scalar_one_or_none()

    async def list_public_games(self, limit: int = 20, offset: int = 0) -> list[Game]:
        result = await self.db.execute(
            select(Game)
            .where(Game.is_public == True, Game.status.in_(["lobby", "active"]))
            .order_by(Game.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_user_games(self, user_id: str) -> list[Game]:
        # Games where user is creator or has a character
        result = await self.db.execute(
            select(Game)
            .join(Character, Character.game_id == Game.id, isouter=True)
            .where(
                (Game.creator_id == user_id) | (Character.player_id == user_id)
            )
            .distinct()
            .order_by(Game.created_at.desc())
        )
        return list(result.scalars().all())

    async def join_game(self, game_id: str, user_id: str, character_id: str | None = None) -> Character:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.status != GameStatus.LOBBY:
            raise ValueError("Game is not in lobby state")

        # Check player count
        result = await self.db.execute(
            select(func.count(Character.id))
            .where(Character.game_id == game_id, Character.player_id.isnot(None))
        )
        current_count = result.scalar() or 0
        if current_count >= game.max_players:
            raise ValueError("Game is full")

        # Check if user already in game
        result = await self.db.execute(
            select(Character)
            .where(Character.game_id == game_id, Character.player_id == user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Already in this game")

        if character_id:
            # Select existing character
            result = await self.db.execute(
                select(Character)
                .where(Character.id == character_id, Character.game_id == game_id)
            )
            character = result.scalar_one_or_none()
            if not character:
                raise ValueError("Character not found")
            if character.player_id is not None:
                raise ValueError("Character already taken")
            character.player_id = user_id
        else:
            # Create custom character
            user = await self.db.execute(select(User).where(User.id == user_id))
            user = user.scalar_one()
            character = Character(
                id=str(uuid.uuid4()),
                game_id=game_id,
                player_id=user_id,
                name=f"{user.username}的角色",
                description="一位新加入的冒险者",
            )
            self.db.add(character)

        # Add join event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.PLAYER_JOIN,
            data={
                "user_id": user_id,
                "character_id": character.id,
                "character_name": character.name,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(character)
        return character

    async def start_game(self, game_id: str, user_id: str) -> Game:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.creator_id != user_id:
            raise ValueError("Only creator can start the game")
        if game.status != GameStatus.LOBBY:
            raise ValueError("Game is not in lobby state")

        # Parse story if not done
        if not game.ai_summary:
            await self.parse_story(game_id)

        game.status = GameStatus.ACTIVE
        game.started_at = datetime.utcnow()

        # Add game start event with opening narrative
        opening = ""
        if game.ai_summary and "initial_state" in game.ai_summary:
            opening = game.ai_summary["initial_state"].get("narrative", "")

        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_START,
            data={"narrative": opening or "游戏开始了！"},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(game)
        return game

    async def get_player_character(self, game_id: str, user_id: str) -> Character | None:
        result = await self.db.execute(
            select(Character)
            .where(Character.game_id == game_id, Character.player_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_game_events(self, game_id: str, since: datetime | None = None, limit: int = 50) -> list[Event]:
        query = select(Event).where(Event.game_id == game_id, Event.is_visible == True)
        if since:
            query = query.where(Event.timestamp > since)
        query = query.order_by(Event.timestamp.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_game_characters(self, game_id: str) -> list[Character]:
        result = await self.db.execute(
            select(Character).where(Character.game_id == game_id).order_by(Character.created_at)
        )
        return list(result.scalars().all())

    async def get_character(self, character_id: str) -> Character | None:
        result = await self.db.execute(select(Character).where(Character.id == character_id))
        return result.scalar_one_or_none()

    async def end_game(self, game_id: str, reason: str) -> Game:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")

        game.status = GameStatus.FINISHED
        game.finished_at = datetime.utcnow()

        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_END,
            data={"reason": reason},
        )
        self.db.add(event)
        await self.db.commit()
        return game
