import uuid
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Action, ActionStatus, ActionType, Character, Game, GameStatus, Event, EventType
from app.schemas.action import ActionCreate, CooperationCreate, ActionResponse, CooperationResponse
from app.config import get_settings
from app.services.ai_service import AIService
from app.services.game_service import GameService

logger = logging.getLogger(__name__)


class ActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.game_service = GameService(db)

    async def _build_game_context(self, game: Game, current_character: Character | None = None) -> dict:
        """构建完整的游戏上下文，供 AI 调用使用。"""
        ai = game.ai_summary or {}

        # 故事背景摘要
        story_summary_parts = []
        if ai.get("title"):
            story_summary_parts.append(f"故事标题：{ai['title']}")
        if ai.get("genre"):
            story_summary_parts.append(f"类型：{ai['genre']}")
        if ai.get("tone"):
            story_summary_parts.append(f"基调：{ai['tone']}")
        if ai.get("main_goal"):
            story_summary_parts.append(f"主线目标：{ai['main_goal']}")
        if ai.get("initial_state", {}).get("narrative"):
            story_summary_parts.append(f"开场：{ai['initial_state']['narrative'][:500]}")
        story_summary = "\n".join(story_summary_parts)

        # 场景信息 — 根据角色当前位置匹配
        current_scene = "未知场景"
        scenes = ai.get("scenes", [])
        if current_character and current_character.location:
            for s in scenes:
                if s.get("id") == current_character.location or s.get("name") == current_character.location:
                    current_scene = f"{s.get('name', '')}：{s.get('description', '')}"
                    if s.get("secrets"):
                        current_scene += f"\n隐藏信息：{s['secrets']}"
                    break
        if current_scene == "未知场景" and scenes:
            current_scene = f"{scenes[0].get('name', '')}：{scenes[0].get('description', '')}"

        # 章节信息
        chapter = game.current_chapter or 1
        chapter_info_parts = [f"当前章节：第{chapter}章"]
        chapter_title = ""
        chapter_goal = ""
        for cp in ai.get("chapter_plan", []):
            if cp.get("chapter") == chapter:
                chapter_title = cp.get("title", "")
                chapter_goal = cp.get("goal", "")
                chapter_info_parts.append(f"章节标题：{chapter_title}")
                chapter_info_parts.append(f"阶段目标：{chapter_goal}")
                if cp.get("key_events"):
                    chapter_info_parts.append(f"关键事件：{', '.join(cp['key_events'])}")
                break
        chapter_info = "\n".join(chapter_info_parts)

        # 全队角色状态
        all_chars = await self.game_service.get_game_characters(game.id)
        all_chars_lines = []
        for c in all_chars:
            if not c.player_id:
                continue  # 跳过未选择的角色
            status = c.status_effects or {}
            health = status.get("health", 100)
            items = status.get("items", [])
            injuries = status.get("injuries", [])
            line = f"- {c.name}（{'存活' if c.is_alive else '倒下'}）"
            if c.location:
                line += f" 位置：{c.location}"
            line += f" 生命：{health}/100"
            if items:
                line += f" 物品：{', '.join(items)}"
            if injuries:
                line += f" 状态：{', '.join(str(i) for i in injuries)}"
            if c.id == current_character.id if current_character else False:
                line += " [当前行动角色]"
            all_chars_lines.append(line)
        all_characters_status = "\n".join(all_chars_lines) if all_chars_lines else "暂无队伍信息"

        # 当前角色详细状态
        character_status_str = "{}"
        if current_character:
            character_status_str = str(current_character.status_effects or {})

        # 最近事件（取最近 N 条可见事件，N 由 admin 配置）
        keep_recent = get_settings().MEMORY_COMPRESS_KEEP_RECENT
        recent_events_list = await self.game_service.get_game_events(game.id, limit=keep_recent)
        recent_events_lines = []
        for ev in reversed(recent_events_list):  # 按时间正序
            data = ev.data or {}
            ts = ev.timestamp.strftime("%H:%M") if ev.timestamp else "??:??"
            if ev.type == EventType.ACTION_RESULT:
                recent_events_lines.append(f"[{ts}] {data.get('character_name', '?')} 的行动结果：{data.get('narrative', '')[:200]}")
            elif ev.type == EventType.ACTION_START:
                recent_events_lines.append(f"[{ts}] {data.get('character_name', '?')} 开始行动：{data.get('public_snippet', '')}")
            elif ev.type == EventType.GAME_START:
                recent_events_lines.append(f"[{ts}] 游戏开始：{data.get('narrative', '')[:200]}")
            elif ev.type == EventType.CHAPTER_ADVANCE:
                recent_events_lines.append(f"[{ts}] 进入第{data.get('chapter', '?')}章：{data.get('description', '')}")
            elif ev.type == EventType.COOPERATION_RESULT:
                recent_events_lines.append(f"[{ts}] {data.get('helper_name', '?')} 协助了 {data.get('target_name', '?')}：{data.get('narrative', '')}")
            elif ev.type == EventType.PLAYER_JOIN:
                recent_events_lines.append(f"[{ts}] {data.get('character_name', '?')} 加入了队伍")
            elif ev.type == EventType.MIDGAME_JOIN:
                recent_events_lines.append(f"[{ts}] {data.get('character_name', '?')} 在冒险中途加入了队伍（第{data.get('chapter', '?')}章）")
        recent_events = "\n".join(recent_events_lines) if recent_events_lines else "暂无事件记录"

        # 游戏已进行时间
        elapsed_time = ""
        if game.started_at:
            started = game.started_at.replace(tzinfo=timezone.utc) if game.started_at.tzinfo is None else game.started_at
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            elapsed_time = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
        target_duration = f"{game.target_duration_minutes}分钟" if game.target_duration_minutes else "未设定"

        # game_memory = story background + compressed history
        game_memory = story_summary
        if game.compressed_memory:
            game_memory += f"\n\n===== 游戏记忆（历史摘要）=====\n{game.compressed_memory}"

        return {
            "story_summary": story_summary,
            "compressed_memory": game.compressed_memory or "",
            "game_memory": game_memory,
            "current_scene": current_scene,
            "chapter_info": chapter_info,
            "chapter": chapter,
            "chapter_title": chapter_title,
            "chapter_goal": chapter_goal,
            "all_characters_status": all_characters_status,
            "character_status": character_status_str,
            "recent_events": recent_events,
            "elapsed_time": elapsed_time,
            "target_duration": target_duration,
        }

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

        # Build full game context for AI
        ctx = await self._build_game_context(game, character)

        # AI evaluation - with fallback on failure
        try:
            eval_result = await self.ai_service.evaluate_action(
                action_text=data.action_text,
                scene=ctx["current_scene"],
                character_status=character.status_effects or {},
                chapter=ctx["chapter"],
                chapter_title=ctx["chapter_title"],
                chapter_goal=ctx["chapter_goal"],
                characters_status=ctx["all_characters_status"],
                elapsed_time=ctx["elapsed_time"],
                target_duration=ctx["target_duration"],
                game_memory=ctx["game_memory"],
                character_name=character.name,
                recent_events=ctx["recent_events"],
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
        now = datetime.now(timezone.utc)

        # Instant mode: skip timer, complete immediately
        is_instant = game.game_mode == "instant"
        if is_instant:
            wait_seconds = 0
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
                "input_text": data.action_text,
                "wait_seconds": wait_seconds,
            },
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(action)

        if is_instant:
            # Instant mode: complete action immediately, no timer
            await self.complete_action(action.id)
        else:
            # Waiting mode: kick off narrative pre-generation in background during countdown
            asyncio.create_task(
                self._pregenerate_narrative(action.id, game_id, data.character_id)
            )

        return action

    async def _pregenerate_narrative(self, action_id: str, game_id: str, character_id: str):
        """Background task: generate narrative during countdown period."""
        from app.database import async_session

        try:
            async with async_session() as db:
                action_svc = ActionService(db)

                action = await action_svc.get_action(action_id)
                if not action or action.status != ActionStatus.PENDING:
                    return

                game = await action_svc.game_service.get_game(game_id)
                character = await action_svc.game_service.get_character(character_id)
                if not game or not character:
                    return

                ctx = await action_svc._build_game_context(game, character)

                try:
                    narrative_result = await action_svc.ai_service.generate_narrative(
                        action_text=action.input_text,
                        character_name=character.name,
                        wait_seconds=action.wait_seconds,
                        difficulty=action.difficulty or "medium",
                        risk=action.risk or "low",
                        game_memory=ctx["game_memory"],
                        current_scene=ctx["current_scene"],
                        character_status=ctx["character_status"],
                        all_characters_status=ctx["all_characters_status"],
                        chapter_info=ctx["chapter_info"],
                        recent_events=ctx["recent_events"],
                        story_summary=ctx["story_summary"],
                    )
                except Exception as e:
                    logger.warning(f"Pre-generation failed for action {action_id}: {e}")
                    return

                # Re-check status before storing (may have been cancelled)
                await db.refresh(action)
                if action.status != ActionStatus.PENDING:
                    return

                action.narrative_result_cache = narrative_result
                await db.commit()
                logger.info(f"Pre-generated narrative for action {action_id}")
        except Exception as e:
            logger.error(f"Pre-generation error for action {action_id}: {e}")

    async def complete_action(self, action_id: str) -> Action:
        action = await self.get_action(action_id)
        if not action or action.status != ActionStatus.PENDING:
            raise ValueError("Action not found or not pending")

        game = await self.game_service.get_game(action.game_id)
        character = await self.game_service.get_character(action.character_id)

        # Check if narrative was pre-generated during countdown
        if action.narrative_result_cache:
            narrative_result = action.narrative_result_cache
        else:
            # Fallback: generate narrative now (pre-generation may have failed)
            ctx = await self._build_game_context(game, character)
            try:
                narrative_result = await self.ai_service.generate_narrative(
                    action_text=action.input_text,
                    character_name=character.name,
                    wait_seconds=action.wait_seconds,
                    difficulty=action.difficulty or "medium",
                    risk=action.risk or "low",
                    game_memory=ctx["game_memory"],
                    current_scene=ctx["current_scene"],
                    character_status=ctx["character_status"],
                    all_characters_status=ctx["all_characters_status"],
                    chapter_info=ctx["chapter_info"],
                    recent_events=ctx["recent_events"],
                    story_summary=ctx["story_summary"],
                )
            except Exception:
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
        action.completed_at = datetime.now(timezone.utc)
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

        # Check if memory compression is needed (async, non-blocking)
        asyncio.create_task(self._maybe_compress_memory(action.game_id))

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

    async def _maybe_compress_memory(self, game_id: str):
        """Check if memory compression is needed and trigger it if so.

        Called after action completion. Runs the actual AI compression in a
        background task so it doesn't block the response.
        """
        settings = get_settings()
        event_threshold = settings.MEMORY_COMPRESS_EVENT_THRESHOLD
        char_threshold = settings.MEMORY_COMPRESS_CHAR_THRESHOLD

        # Skip if both thresholds are 0 (disabled)
        if event_threshold <= 0 and char_threshold <= 0:
            return

        game = await self.game_service.get_game(game_id)
        if not game or game.status != GameStatus.ACTIVE:
            return

        # Count events after last compression
        base_count = game.memory_event_count or 0
        result = await self.db.execute(
            select(func.count(Event.id)).where(
                Event.game_id == game_id,
                Event.is_visible == True,
            )
        )
        total_events = result.scalar() or 0
        new_event_count = total_events - base_count

        if new_event_count <= 0:
            return

        # Check event count threshold
        triggered = event_threshold > 0 and new_event_count >= event_threshold

        # Check char count threshold
        if not triggered and char_threshold > 0:
            result = await self.db.execute(
                select(Event).where(
                    Event.game_id == game_id,
                    Event.is_visible == True,
                ).order_by(Event.timestamp.desc()).offset(base_count)
            )
            new_events = list(result.scalars().all())
            total_chars = sum(len(str(e.data or "")) for e in new_events)
            triggered = total_chars >= char_threshold

        if not triggered:
            return

        # Trigger compression in background
        asyncio.create_task(self._run_memory_compression(game_id, base_count, total_events))

    async def _run_memory_compression(self, game_id: str, base_count: int, total_events: int):
        """Background task: compress old events into memory summary."""
        try:
            # Use a fresh session for the background task
            from app.database import async_session

            async with async_session() as db:
                game_svc = GameService(db)
                game = await game_svc.get_game(game_id)
                if not game:
                    return

                settings = get_settings()
                keep_recent = settings.MEMORY_COMPRESS_KEEP_RECENT

                # Get all visible events ordered by time
                result = await db.execute(
                    select(Event).where(
                        Event.game_id == game_id,
                        Event.is_visible == True,
                    ).order_by(Event.timestamp.asc())
                )
                all_events = list(result.scalars().all())

                # Events to compress: everything except the last `keep_recent`
                if len(all_events) <= keep_recent:
                    return

                events_to_compress = all_events[:-keep_recent]

                # Format events for compression
                event_lines = []
                for ev in events_to_compress:
                    data = ev.data or {}
                    ts = ev.timestamp.strftime("%H:%M") if ev.timestamp else "??:??"
                    if ev.type == EventType.ACTION_RESULT:
                        event_lines.append(f"[{ts}] {data.get('character_name', '?')} 的行动结果：{data.get('narrative', '')[:300]}")
                    elif ev.type == EventType.ACTION_START:
                        event_lines.append(f"[{ts}] {data.get('character_name', '?')} 开始行动：{data.get('public_snippet', '')}")
                    elif ev.type == EventType.GAME_START:
                        event_lines.append(f"[{ts}] 游戏开始：{data.get('narrative', '')[:300]}")
                    elif ev.type == EventType.CHAPTER_ADVANCE:
                        event_lines.append(f"[{ts}] 进入第{data.get('chapter', '?')}章：{data.get('description', '')}")
                    elif ev.type == EventType.COOPERATION_RESULT:
                        event_lines.append(f"[{ts}] {data.get('helper_name', '?')} 协助了 {data.get('target_name', '?')}：{data.get('narrative', '')}")
                    elif ev.type == EventType.PLAYER_JOIN:
                        event_lines.append(f"[{ts}] {data.get('character_name', '?')} 加入了队伍")
                    elif ev.type == EventType.MIDGAME_JOIN:
                        event_lines.append(f"[{ts}] {data.get('character_name', '?')} 在中途加入了队伍")
                    elif ev.type == EventType.PLAYER_LEAVE:
                        event_lines.append(f"[{ts}] {data.get('character_name', '?')} 离开了队伍")

                recent_events_text = "\n".join(event_lines)
                if not recent_events_text:
                    return

                # Get character status
                chars = await game_svc.get_game_characters(game_id)
                char_lines = []
                for c in chars:
                    if not c.player_id:
                        continue
                    status = c.status_effects or {}
                    health = status.get("health", 100)
                    line = f"- {c.name}（{'存活' if c.is_alive else '倒下'}）生命：{health}/100"
                    if c.location:
                        line += f" 位置：{c.location}"
                    char_lines.append(line)
                characters_status = "\n".join(char_lines) or "暂无"

                # Story summary
                ai = game.ai_summary or {}
                story_parts = []
                if ai.get("title"):
                    story_parts.append(f"故事标题：{ai['title']}")
                if ai.get("main_goal"):
                    story_parts.append(f"主线目标：{ai['main_goal']}")
                story_summary = "\n".join(story_parts)

                # Call AI compression
                ai_svc = AIService()
                existing_summary = game.compressed_memory or ""
                result = await ai_svc.compress_memory(
                    recent_events=recent_events_text,
                    characters_status=characters_status,
                    story_summary=story_summary,
                    existing_summary=existing_summary,
                )

                # Build the compressed memory text
                memory_parts = []
                if result.get("memory_summary"):
                    memory_parts.append(result["memory_summary"])
                if result.get("key_facts"):
                    memory_parts.append("关键事实：" + "；".join(result["key_facts"]))
                if result.get("pending_threads"):
                    memory_parts.append("未解悬念：" + "；".join(result["pending_threads"]))
                if result.get("character_relationships"):
                    memory_parts.append("角色关系：" + result["character_relationships"])

                compressed_text = "\n".join(memory_parts)

                # Update game
                game.compressed_memory = compressed_text
                game.memory_event_count = total_events
                game.last_memory_compress_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info(f"Memory compressed for game {game_id}: {len(events_to_compress)} events -> {len(compressed_text)} chars")

        except Exception as e:
            logger.error(f"Memory compression failed for game {game_id}: {e}")

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
        now = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
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

        # Check if memory compression is needed (async, non-blocking)
        asyncio.create_task(self._maybe_compress_memory(cooperation.game_id))

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
        now = datetime.now(timezone.utc)
        remaining = None
        if action.status == ActionStatus.PENDING and action.finish_at:
            finish_at = action.finish_at.replace(tzinfo=timezone.utc) if action.finish_at.tzinfo is None else action.finish_at
            remaining = max(0, (finish_at - now).total_seconds())

        # Hide pre-generated narrative from pending actions
        is_pending = action.status == ActionStatus.PENDING

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
            result_narrative=None if is_pending else action.result_narrative,
            result_effects=None if is_pending else action.result_effects,
            difficulty=action.difficulty,
            risk=action.risk,
            is_cooperation=action.is_cooperation,
            cooperation_target_id=action.cooperation_target_id,
            modifiers=action.modifiers or [],
            status=action.status.value if action.status else "pending",
            created_at=action.created_at,
            remaining_seconds=remaining,
        )
