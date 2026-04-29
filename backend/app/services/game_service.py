import uuid
import string
import random
from datetime import datetime, timedelta
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Game, GameStatus, ParseStatus, Character, User, Event, EventType
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
            parse_status=ParseStatus.PENDING,
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

        # Update status to processing
        game.parse_status = ParseStatus.PROCESSING
        game.parse_error = None
        await self.db.commit()

        try:
            summary = await self.ai_service.parse_story(game.uploaded_story, game.duration_hint)

            # Delete existing unclaimed preset characters (for retry-parse case)
            # Use bulk DELETE to ensure rows are removed before INSERT
            from sqlalchemy import delete as sql_delete
            await self.db.execute(
                sql_delete(Character).where(
                    Character.game_id == game_id,
                    Character.player_id.is_(None),
                )
            )
            await self.db.flush()

            game.ai_summary = summary
            game.parse_status = ParseStatus.COMPLETED
            if summary.get("title") and not game.title:
                game.title = summary["title"]

            # Create Character rows from AI-generated preset_characters
            for pc in summary.get("preset_characters", []):
                character = Character(
                    id=pc["id"],
                    game_id=game_id,
                    player_id=None,
                    name=pc.get("name", "Unknown"),
                    description=pc.get("description"),
                    background=pc.get("background"),
                    location=pc.get("starting_location"),
                )
                self.db.add(character)

            await self.db.commit()
            return summary
        except Exception as e:
            await self.db.rollback()
            game = await self.get_game(game_id)
            if game:
                game.parse_status = ParseStatus.FAILED
                game.parse_error = str(e)[:500]
                await self.db.commit()
            raise

    async def retry_parse_story(self, game_id: str) -> dict:
        """Retry story parsing for failed or pending games."""
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.parse_status == ParseStatus.COMPLETED:
            raise ValueError("Story already parsed successfully")
        return await self.parse_story(game_id)

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

    async def list_public_games(self, limit: int = 20, offset: int = 0) -> list[tuple[Game, int]]:
        """Return (game, player_count) tuples."""
        count_subq = (
            select(Character.game_id, func.count(Character.id).label("cnt"))
            .where(Character.player_id.isnot(None))
            .group_by(Character.game_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Game, func.coalesce(count_subq.c.cnt, 0).label("player_count"))
            .outerjoin(count_subq, Game.id == count_subq.c.game_id)
            .where(Game.is_public == True, Game.status.in_([GameStatus.LOBBY, GameStatus.ACTIVE]))
            .order_by(Game.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_user_games(self, user_id: str) -> list[tuple[Game, int]]:
        """Return (game, player_count) tuples for games the user is involved in."""
        count_subq = (
            select(Character.game_id, func.count(Character.id).label("cnt"))
            .where(Character.player_id.isnot(None))
            .group_by(Character.game_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Game, func.coalesce(count_subq.c.cnt, 0).label("player_count"))
            .outerjoin(count_subq, Game.id == count_subq.c.game_id)
            .join(Character, Character.game_id == Game.id, isouter=True)
            .where(
                (Game.creator_id == user_id) | (Character.player_id == user_id)
            )
            .distinct()
            .order_by(Game.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_player_count(self, game_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Character.id))
            .where(Character.game_id == game_id, Character.player_id.isnot(None))
        )
        return result.scalar() or 0

    async def join_game(self, game_id: str, user_id: str, character_id: str | None = None) -> Character:
        # Lock the game row to prevent TOCTOU race conditions
        result = await self.db.execute(
            select(Game).where(Game.id == game_id).with_for_update()
        )
        game = result.scalar_one_or_none()
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

        # Check if user already in game - allow character switching
        result = await self.db.execute(
            select(Character)
            .where(Character.game_id == game_id, Character.player_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if character_id:
            # Select existing character with lock
            result = await self.db.execute(
                select(Character)
                .where(Character.id == character_id, Character.game_id == game_id)
                .with_for_update()
            )
            character = result.scalar_one_or_none()
            if not character:
                raise ValueError("Character not found")
            # Allow switching if character is not taken by another player
            if character.player_id is not None and character.player_id != user_id:
                raise ValueError("Character already taken")
            # If switching characters, release the old one
            if existing and existing.id != character_id:
                existing.player_id = None
            character.player_id = user_id
        else:
            # If switching to custom character, release the old one
            if existing:
                existing.player_id = None
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
        if not game.ai_summary:
            raise ValueError("AI is still parsing the story, please wait")

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

    async def leave_game(self, game_id: str, user_id: str) -> None:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot leave a game that has started")
        if game.creator_id == user_id:
            raise ValueError("Creator cannot leave; use disband instead")

        result = await self.db.execute(
            select(Character)
            .where(Character.game_id == game_id, Character.player_id == user_id)
        )
        character = result.scalar_one_or_none()
        if not character:
            raise ValueError("You are not in this game")

        # Release the character (make it available again or remove custom ones)
        character.player_id = None

        # Add leave event
        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.PLAYER_LEAVE,
            data={
                "user_id": user_id,
                "character_name": character.name,
            },
        )
        self.db.add(event)
        await self.db.commit()

    async def disband_game(self, game_id: str, user_id: str) -> None:
        game = await self.get_game(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.creator_id != user_id:
            raise ValueError("Only the creator can disband the game")
        if game.status != GameStatus.LOBBY:
            raise ValueError("Cannot disband a game that has started")

        game.status = GameStatus.ABANDONED

        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_END,
            data={"reason": "房主解散了房间"},
        )
        self.db.add(event)
        await self.db.commit()

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
