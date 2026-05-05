import uuid
from datetime import datetime, timedelta, timezone
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
            game_mode=data.game_mode,
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

            # Delete ALL existing unclaimed characters for this game (retry-parse case)
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

            # Create Character rows with globally unique UUIDs
            # (AI-generated IDs like "char_1" are not globally unique)
            for pc in summary.get("preset_characters", []):
                char_id = str(uuid.uuid4())
                # Update the ID in ai_summary so frontend can match
                pc["db_id"] = char_id
                character = Character(
                    id=char_id,
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
        if game.status not in (GameStatus.LOBBY, GameStatus.ACTIVE):
            raise ValueError("Game is not joinable (must be lobby or active)")

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

        is_midgame = game.status == GameStatus.ACTIVE

        # Set mid-game defaults for new characters joining an active game
        if is_midgame and not existing:
            if not character.status_effects:
                character.status_effects = {"health": 100, "items": [], "injuries": []}
            else:
                character.status_effects.setdefault("health", 100)
                character.status_effects.setdefault("items", [])
                character.status_effects.setdefault("injuries", [])

            # Set location to current chapter's target scene if not already set
            if not character.location:
                ai = game.ai_summary or {}
                scenes = ai.get("scenes", [])
                if scenes:
                    chapter = game.current_chapter or 1
                    target_scene = None
                    for cp in ai.get("chapter_plan", []):
                        if cp.get("chapter") == chapter:
                            target_scene = cp.get("target_scene")
                            break
                    if target_scene:
                        for s in scenes:
                            if s.get("id") == target_scene:
                                character.location = target_scene
                                break
                    if not character.location:
                        character.location = scenes[0].get("id")

        # Only emit join event on first-time join, not character switches
        if not existing:
            if is_midgame:
                event = Event(
                    id=str(uuid.uuid4()),
                    game_id=game_id,
                    type=EventType.MIDGAME_JOIN,
                    data={
                        "user_id": user_id,
                        "character_id": character.id,
                        "character_name": character.name,
                        "chapter": game.current_chapter or 1,
                    },
                )
            else:
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
        game.started_at = datetime.now(timezone.utc)

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
        if game.status not in (GameStatus.LOBBY, GameStatus.ACTIVE):
            raise ValueError("Cannot leave a game that has ended")
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
        game.finished_at = datetime.now(timezone.utc)

        event = Event(
            id=str(uuid.uuid4()),
            game_id=game_id,
            type=EventType.GAME_END,
            data={"reason": reason},
        )
        self.db.add(event)
        await self.db.commit()

        # Generate story recap in background
        import asyncio
        asyncio.create_task(self._generate_story_recap(game_id))

        return game

    async def _generate_story_recap(self, game_id: str) -> None:
        """Generate an AI story recap after game ends."""
        try:
            from app.database import async_session
            async with async_session() as db:
                # Reload game in new session
                result = await db.execute(select(Game).where(Game.id == game_id))
                game = result.scalar_one_or_none()
                if not game:
                    return

                # Gather events for recap
                events_result = await db.execute(
                    select(Event)
                    .where(Event.game_id == game_id, Event.is_visible == True)
                    .order_by(Event.timestamp.asc())
                )
                events = list(events_result.scalars().all())

                # Build event summary
                event_lines = []
                for e in events:
                    d = e.data or {}
                    if e.type.value == "action_result":
                        event_lines.append(f"[{e.type.value}] {d.get('character_name', '')}: {d.get('narrative', '')[:200]}")
                    elif e.type.value == "game_start":
                        event_lines.append(f"[开场] {d.get('narrative', '')[:200]}")
                    elif e.type.value == "game_end":
                        event_lines.append(f"[结束] {d.get('reason', '')}")
                    elif e.type.value == "chapter_advance":
                        event_lines.append(f"[章节推进] 第{d.get('chapter', '?')}章: {d.get('description', '')}")
                    elif e.type.value == "player_join":
                        event_lines.append(f"[加入] {d.get('character_name', '')}")
                    else:
                        snippet = d.get("public_snippet") or d.get("narrative") or d.get("message") or str(d)[:100]
                        event_lines.append(f"[{e.type.value}] {snippet}")

                events_text = "\n".join(event_lines[-100:])  # Last 100 events

                # Get characters
                chars_result = await db.execute(
                    select(Character).where(Character.game_id == game_id)
                )
                characters = list(chars_result.scalars().all())
                chars_text = "\n".join(
                    f"- {c.name}: {'存活' if c.is_alive else '死亡'}, 位置={c.location or '未知'}"
                    for c in characters
                )

                # Use compressed memory if available, otherwise use events
                memory = game.compressed_memory or ""

                prompt = f"""你是一个跑团记录员。游戏已经结束，请根据以下信息生成一段精彩的故事回顾总结（300-600字）。

故事标题：{game.title or '未命名冒险'}
故事背景摘要：{memory[:500] if memory else '无'}

完整事件记录：
{events_text}

角色最终状态：
{chars_text}

结束原因：游戏已结束

请生成一段引人入胜的故事回顾，像小说的结尾章节一样。重点描述：
1. 冒险的开端和核心冲突
2. 过程中的关键时刻和转折
3. 最终的结局
4. 各角色的命运

以纯文本形式返回，不要使用 JSON。"""

                from app.services.ai_service import AIService
                ai = AIService()
                recap = await ai.call_text(
                    system_prompt="你是一个才华横溢的故事记录员，擅长将游戏过程编织成精彩的故事回顾。",
                    user_prompt=prompt,
                    temperature=0.7,
                    premium=True,
                )

                # Save recap
                result2 = await db.execute(select(Game).where(Game.id == game_id))
                game2 = result2.scalar_one_or_none()
                if game2:
                    game2.story_recap = recap
                    await db.commit()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to generate story recap for game %s", game_id)
