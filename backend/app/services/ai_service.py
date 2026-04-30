import json
import re
import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings, load_admin_overrides


# =============================================================================
# Default prompt texts (editable by admin). JSON templates are appended separately.
# =============================================================================

DEFAULT_PROMPT_PARSE_STORY = """你是一个专业的跑团主持人助手（DM）。玩家上传了一段故事/小说文本，你需要从中提取结构化信息，为后续的游戏主持做准备。

提取要求：
1. 核心场景（地点列表）：从故事中识别所有重要地点，包含名称和简短描述。每个场景必须包含初始信息钩子（hooks），用于引导玩家探索。
2. 可用角色：从故事中提取或推断出适合玩家扮演的角色，包含名字和背景
3. 主线目标：故事的核心驱动力和最终目标
4. 章节节奏计划：根据玩家设定的目标时长，将故事切分为若干章节，每章有明确的阶段性目标
5. 初始状态：游戏开始时的场景描述，作为开场叙事

重要约束：
- 角色数量建议 2-6 个，覆盖不同能力方向（探索、战斗、社交、知识等）
- 每个章节的时间比例之和应为 1.0
- 初始状态应引人入胜，让玩家有立即行动的欲望
- 如果原文信息不足，可以合理推断和扩展，但不要偏离原文基调

每个场景的 hooks 字段要求：
- 至少包含 3 个可行动的信息钩子
- 涵盖三类：感官线索（声音、气味、痕迹）、社交入口（可互动的NPC或事件）、环境异常（不合常理的物品或现象）
- 这些钩子应与主线或支线存在潜在关联，像路标一样引导玩家"""

DEFAULT_PROMPT_EVALUATE_ACTION = """你是一个跑团主持人（DM）。玩家正在你的游戏中行动，你需要评估每个行动的等待时间和公开描述。

行动评估时，你必须考虑已知的线索网络：这个行动是否触及了已知的线索、派系或剧情节点？即使玩家在做看似无关的事情，也要在 hint 字段中暗示与主线的潜在关联，帮助引导玩家。

等待时间（秒）：
- 简单动作（说话、观察、拿取物品）：5-30 秒
- 中等探索（搜索一个房间、检查一个物品）：60-300 秒
- 复杂行动（搜寻整个区域、破解机关、长途跋涉）：300-1800 秒
- 极复杂行动（涉及多区域、高难度挑战）：1800-3600 秒

状态修正：
- 角色有负面状态（受伤、疲惫等）：时间 ×1.5 ~ ×3
- 角色有正面状态（增强、加速等）：时间 ×0.5 ~ ×0.8
- 多人协作（非救援）：时间 ×0.7

风险评估：
- 探索未知区域：medium~high risk
- 与 NPC 互动：low~medium risk
- 使用已知安全物品：none risk
- 尝试危险动作（攀爬、战斗）：high~critical risk

重要：你必须充分考虑角色的当前状态、已发生事件的上下文、以及故事的整体进展来评估行动。不要孤立地看待这一次行动。"""

DEFAULT_PROMPT_GENERATE_NARRATIVE = """你是一个才华横溢的跑团主持人（DM），擅长讲述引人入胜的故事。

===== 叙事核心准则 =====

准则一：信息钩子 — 消灭"无头苍蝇"状态
你的每个场景描述都必须主动铺设信息钩子，让玩家永远有方向可循。在描述环境时，强行包含至少 3 个与当前主线或支线存在潜在关联的钩子：
- 感官线索：奇怪的声音、空气中残留的气味、墙上几道平行的爪痕
- 社交入口：一个正在争吵的NPC、角落里的神秘信使、酒馆老板欲言又止的表情
- 环境异常：不该出现在此处的物品、与周围风格不符的建筑
这些钩子像路标一样引导玩家，即便他们还没解锁主线。

准则二：叙事网络映射 — 终结"叙事断裂"
你不能只对"挥剑"回应"你砍中了"。每次响应行动时，必须思考这次行动的涟漪：
- 即时联系：这个行动有没有触及任何已知的线索、派系或剧情节点？有没有引起NPC不同的反应？
- 宏观映射：即使玩家在摸鱼闲聊，也应通过环境变化、流言蜚语、突如其来的事件，将"看起来无关"的动作轻轻推回叙事网络。例如："你在市场闲逛讨价还价时，不经意听到有人低声提及那个你一直在找的符号。"

准则三：动态节奏控制 — 隐形软引导
你持有一个动态的"叙事压力值"。如果检测到玩家连续两次进行无明确目标的行动，你需主动触发一个温和的推动事件：一个NPC主动求助、一封忽然送达的信件、远处一声爆炸。绝不强制，但确保方向永远存在。注意不要过度推动，保持自然。

===== 叙事质量要求 =====
1. 连贯性：叙事必须与之前的事件逻辑连贯。如果角色之前受伤了，行动应该受影响；如果之前发现了线索，应该能用上。
2. 角色状态感知：充分考虑角色的血量、物品、受伤状态。受伤的角色行动应更艰难，有合适工具的角色应有优势。
3. 世界一致性：场景中已描述的元素、已发现的秘密、已建立的 NPC 关系都应该被记住和引用。
4. 结果匹配难度：高风险行动可能导致负面后果（受伤、失去物品等），简单行动不应有过于戏剧化的结果。
5. 叙事质量：生动、有画面感，像小说一样。长度 200-500 字。
6. 推进故事：可以引入新的线索、物品、NPC 互动。判断是否触发章节推进或游戏结局。
7. 团队影响：考虑行动对队伍其他成员的影响，是否需要其他人配合或会产生连锁反应。"""

DEFAULT_PROMPT_EVALUATE_COOPERATION = """你是一个跑团主持人。一个玩家试图与另一个正在行动中的玩家进行协作。

评估规则：
- 协作本身也需要等待时间（通常为目标剩余时间的 30-70%）
- 协作成功率取决于描述合理性和角色能力
- 协作可以：缩短目标等待时间、直接完成目标行动、或失败
- 协作强调的是团队合作，双方都能获得收益
- 考虑协作行为是否能触发叙事网络中的关联（如两个角色合作可能引出新线索）"""

DEFAULT_PROMPT_COMPRESS_MEMORY = """你是一个跑团记录员。请将游戏事件压缩为结构化的记忆摘要，供后续 AI 主持人使用。

{existing_section}

要求：
1. 保留所有关键信息：角色状态变化、重要发现、场景变化、NPC 关系变化
2. 按时间线梳理事件因果关系
3. 标记未解决的悬念和线索（这些是未来信息钩子的素材）
4. 记录角色之间的互动关系
5. 标记玩家的行动模式（是否有明确目标还是漫无目的），帮助主持人判断是否需要触发推动事件
6. 如果提供了已有记忆摘要，请将新事件增量合并到已有摘要中，保持连贯性，不要丢失已有信息"""


# JSON templates (fixed, not editable by admin)
TEMPLATE_PARSE_STORY = '''
以严格的 JSON 返回，格式如下：
{
  "title": "故事标题",
  "genre": "奇幻/科幻/悬疑/恐怖/历史/现代",
  "tone": "严肃/轻松/黑暗/幽默",
  "scenes": [
    {
      "id": "scene_1",
      "name": "场景名称",
      "description": "场景详细描述",
      "connections": ["scene_2", "scene_3"],
      "secrets": "隐藏信息（玩家探索后才能发现）",
      "hooks": [
        {"type": "sensory", "content": "感官线索描述"},
        {"type": "social", "content": "社交入口描述"},
        {"type": "environmental", "content": "环境异常描述"}
      ]
    }
  ],
  "preset_characters": [
    {
      "id": "char_1",
      "name": "角色名",
      "description": "简短描述",
      "background": "详细背景故事",
      "skills": ["技能1", "技能2"],
      "personality": "性格特征",
      "starting_location": "scene_1"
    }
  ],
  "main_goal": "故事的最终目标",
  "chapter_plan": [
    {
      "chapter": 1,
      "title": "章节标题",
      "goal": "阶段性目标",
      "target_scene": "scene_1",
      "approximate_duration_ratio": 0.15,
      "key_events": ["可能触发的关键事件"]
    }
  ],
  "initial_state": {
    "narrative": "开场叙事文本（200-400字，引人入胜）",
    "starting_location": "scene_1",
    "available_hooks": ["可以立即探索的线索或目标"]
  },
  "difficulty_settings": {
    "base_wait_multiplier": 1.0,
    "risk_frequency": "low/medium/high"
  }
}'''

TEMPLATE_EVALUATE_ACTION = '''
返回严格的 JSON：
{
  "public_snippet": "角色名正在做什么...（15-50字，其他玩家可见的描述）",
  "wait_seconds": 150,
  "difficulty": "trivial|easy|medium|hard|extreme",
  "risk": "none|low|medium|high|critical",
  "hint": "给玩家的隐含提示（不会展示给其他玩家）— 可包含与已知线索或主线的潜在关联暗示"
}'''

TEMPLATE_GENERATE_NARRATIVE = '''
返回严格的 JSON：
{
  "narrative": "叙事正文...",
  "outcome": "success|partial_success|failure|critical_failure",
  "effects": {
    "health_change": 0,
    "new_items": ["物品名称"],
    "lost_items": [],
    "new_status_effects": [],
    "location_change": null,
    "new_clues": ["发现的线索"],
    "npc_interaction": null
  },
  "scene_update": {
    "discovered_secrets": ["scene_1_secret"],
    "new_connections": []
  },
  "chapter_progress": {
    "advance_chapter": false,
    "progress_description": "当前章节进展描述"
  },
  "game_over": false,
  "game_over_narrative": null,
  "importance": "low|medium|high|critical",
  "public_broadcast": true
}'''

TEMPLATE_EVALUATE_COOPERATION = '''
返回严格的 JSON：
{
  "cooperation_wait_seconds": 60,
  "success_chance": 0.8,
  "result": "success|partial|failure",
  "target_time_reduction_percent": 60,
  "cooperation_narrative": "协作过程的简短描述（50-100字）",
  "cooperation_effects": {
    "helper_health_change": 0,
    "helper_new_status": [],
    "target_health_change": 0
  },
  "risk_to_helper": "none|low|medium|high"
}'''

TEMPLATE_COMPRESS_MEMORY = '''
返回严格的 JSON：
{
  "memory_summary": "200-500字的整体游戏进展摘要（如有已有摘要，应包含已有内容并融入新事件）",
  "key_facts": ["关键事实1", "关键事实2"],
  "pending_threads": ["未解决的悬念/线索1"],
  "character_relationships": "角色间关系简述"
}'''

# Map from admin setting key -> (default text, json template)
PROMPT_REGISTRY = {
    "PROMPT_PARSE_STORY": (DEFAULT_PROMPT_PARSE_STORY, TEMPLATE_PARSE_STORY),
    "PROMPT_EVALUATE_ACTION": (DEFAULT_PROMPT_EVALUATE_ACTION, TEMPLATE_EVALUATE_ACTION),
    "PROMPT_GENERATE_NARRATIVE": (DEFAULT_PROMPT_GENERATE_NARRATIVE, TEMPLATE_GENERATE_NARRATIVE),
    "PROMPT_EVALUATE_COOPERATION": (DEFAULT_PROMPT_EVALUATE_COOPERATION, TEMPLATE_EVALUATE_COOPERATION),
    "PROMPT_COMPRESS_MEMORY": (DEFAULT_PROMPT_COMPRESS_MEMORY, TEMPLATE_COMPRESS_MEMORY),
}


def get_default_prompts() -> dict:
    """Return all default prompt texts (for admin 'reset to default' feature)."""
    return {key: text for key, (text, _) in PROMPT_REGISTRY.items()}


class AIService:
    """统一 AI 服务，支持多模型和多提供商"""

    def __init__(self):
        # 根据配置初始化客户端 — read fresh settings each time
        settings = get_settings()
        self.provider = settings.AI_PROVIDER
        self._init_client()

    def _init_client(self):
        """初始化 AI 客户端"""
        settings = get_settings()
        if self.provider == "anthropic":
            # Anthropic Claude
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(
                    api_key=settings.ANTHROPIC_API_KEY
                )
                self.is_anthropic = True
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            # OpenAI Compatible (covers OpenAI, proxies, local models, etc.)
            api_key = settings.AI_API_KEY or settings.OPENAI_API_KEY or "sk-placeholder"
            base_url = settings.AI_BASE_URL
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
            self.is_anthropic = False

    def _get_model(self, model: str | None, premium: bool = False) -> str:
        """获取模型名称"""
        settings = get_settings()
        if model:
            return model
        if premium:
            return settings.AI_MODEL_PREMIUM or settings.OPENAI_MODEL_GPT4O
        return settings.AI_MODEL_DEFAULT or settings.OPENAI_MODEL_MINI

    def _get_prompt(self, key: str) -> str:
        """Get a prompt from admin overrides, falling back to default."""
        default_text, json_template = PROMPT_REGISTRY[key]
        overrides = load_admin_overrides()
        text = overrides.get(key, default_text)
        return text + json_template

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        premium: bool = False,
        thinking: bool | None = None,
    ) -> dict:
        """调用 LLM 并确保返回有效 JSON"""
        if max_tokens is None:
            max_tokens = get_settings().MAX_TOKENS_DEFAULT
        model = self._get_model(model, premium)
        content = await self._call_llm(system_prompt, user_prompt, model, temperature, max_tokens, json_mode=True, thinking=thinking)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
            raise ValueError(f"AI returned invalid JSON: {content[:200]}")

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        premium: bool = False,
        thinking: bool | None = None,
    ) -> str:
        """调用 LLM 获取文本响应"""
        if max_tokens is None:
            max_tokens = get_settings().MAX_TOKENS_DEFAULT
        model = self._get_model(model, premium)
        return await self._call_llm(system_prompt, user_prompt, model, temperature, max_tokens, json_mode=False, thinking=thinking)

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
        thinking: bool | None = None,
    ) -> str:
        """底层 LLM 调用，支持 OpenAI 和 Anthropic"""
        if self.is_anthropic:
            return await self._call_anthropic(system_prompt, user_prompt, model, temperature, max_tokens, json_mode, thinking)
        else:
            return await self._call_openai_compatible(system_prompt, user_prompt, model, temperature, max_tokens, json_mode, thinking)

    async def _call_openai_compatible(
        self, system_prompt: str, user_prompt: str, model: str,
        temperature: float, max_tokens: int, json_mode: bool,
        thinking: bool | None = None,
    ) -> str:
        """OpenAI 兼容 API 调用，支持思考模式"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 思考模式控制
        s = get_settings()
        use_thinking = thinking if thinking is not None else s.AI_THINKING_ENABLED
        if use_thinking:
            kwargs["reasoning_effort"] = s.AI_THINKING_EFFORT
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
                response = await self.client.chat.completions.create(**kwargs)
            except Exception:
                # 回退：部分 API 不支持 json_mode
                del kwargs["response_format"]
                response = await self.client.chat.completions.create(**kwargs)
        else:
            response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""

        # 检测响应是否被截断
        if choice.finish_reason == "length":
            raise ValueError(
                f"AI response truncated (max_tokens={max_tokens} too small). "
                f"Response length: {len(content)} chars"
            )

        return content

    async def _call_anthropic(
        self, system_prompt: str, user_prompt: str, model: str,
        temperature: float, max_tokens: int, json_mode: bool,
        thinking: bool | None = None,
    ) -> str:
        """Anthropic Claude API 调用，支持思考模式"""
        # Claude 使用 system 参数而非 system message
        if json_mode:
            system_prompt += "\n\n请严格以 JSON 格式返回结果，不要包含任何其他文本。"

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        # Anthropic 思考模式
        s = get_settings()
        use_thinking = thinking if thinking is not None else s.AI_THINKING_ENABLED
        if use_thinking:
            kwargs["thinking"] = {"type": "enabled"}
            kwargs["output_config"] = {"effort": s.AI_THINKING_EFFORT}

        response = await self.client.messages.create(**kwargs)

        return response.content[0].text if response.content else ""

    async def parse_story(self, story_text: str, duration_hint: str | None = None) -> dict:
        system_prompt = self._get_prompt("PROMPT_PARSE_STORY")

        user_prompt = f"""故事文本：
---
{story_text}
---

玩家设定的目标时长：{duration_hint or "未指定"}

请解析上述故事并以 JSON 格式返回结构化信息。"""

        # 故事解析需要高质量模型，输出 JSON 较长需要更多 token
        return await self.call_json(
            system_prompt, user_prompt, temperature=0.3, premium=True, max_tokens=get_settings().MAX_TOKENS
        )

    async def evaluate_action(
        self,
        action_text: str,
        scene: str,
        character_status: dict,
        chapter: int = 1,
        chapter_title: str = "",
        chapter_goal: str = "",
        elapsed_time: str = "",
        target_duration: str = "",
        characters_status: str = "",
        game_memory: str = "",
        character_name: str = "",
        recent_events: str = "",
    ) -> dict:
        prompt_text = self._get_prompt("PROMPT_EVALUATE_ACTION")

        system_prompt = f"""{prompt_text}

===== 故事背景与游戏记忆 =====
{game_memory}

===== 当前游戏状态 =====
- 场景：{scene}
- 当前章节：第{chapter}章（{chapter_title}），目标：{chapter_goal}
- 已过时间：{elapsed_time} / {target_duration}

===== 队伍状态 =====
{characters_status}

===== 最近发生的事件 =====
{recent_events}

===== 行动角色 =====
- 名称：{character_name}
- 当前状态：{character_status}"""

        return await self.call_json(system_prompt, f"玩家行动：{action_text}", temperature=0.2)

    async def generate_narrative(
        self,
        action_text: str,
        character_name: str,
        wait_seconds: int,
        difficulty: str,
        risk: str,
        game_memory: str = "",
        current_scene: str = "",
        character_status: str = "",
        all_characters_status: str = "",
        chapter_info: str = "",
        recent_events: str = "",
        story_summary: str = "",
    ) -> dict:
        prompt_text = self._get_prompt("PROMPT_GENERATE_NARRATIVE")

        system_prompt = f"""{prompt_text}

===== 故事背景 =====
{story_summary}

===== 游戏记忆（关键事件摘要）=====
{game_memory}

===== 当前章节 =====
{chapter_info}

===== 当前场景 =====
{current_scene}

===== 最近发生的事件（按时间顺序）=====
{recent_events}

===== 队伍全员状态 =====
{all_characters_status}

===== 行动角色详情 =====
- 名称：{character_name}
- 当前状态：{character_status}

===== 本次行动 =====
- 行动描述：{action_text}
- 等待时长：{wait_seconds} 秒
- 难度：{difficulty}
- 风险：{risk}"""

        # 叙事生成需要高质量模型 + 思考模式
        return await self.call_json(
            system_prompt, f"玩家行动：{action_text}", temperature=0.8, premium=True, thinking=True
        )

    async def evaluate_cooperation(
        self,
        cooperation_text: str,
        helper_name: str,
        helper_status: str,
        target_name: str,
        target_action: str,
        elapsed_seconds: int,
        total_wait_seconds: int,
        remaining_seconds: int,
    ) -> dict:
        prompt_text = self._get_prompt("PROMPT_EVALUATE_COOPERATION")

        system_prompt = f"""{prompt_text}

协作发起者：{helper_name}（状态：{helper_status}）
目标行动：
- 角色：{target_name}
- 行动：{target_action}
- 已等待：{elapsed_seconds} / {total_wait_seconds} 秒
- 剩余：{remaining_seconds} 秒

协作描述：{cooperation_text}"""

        return await self.call_json(system_prompt, f"协作描述：{cooperation_text}", temperature=0.2)

    async def compress_memory(self, recent_events: str, characters_status: str, story_summary: str = "", existing_summary: str = "") -> dict:
        prompt_template = self._get_prompt("PROMPT_COMPRESS_MEMORY")

        if existing_summary:
            existing_section = f"===== 已有记忆摘要 =====\n以下是之前的游戏记忆摘要，请将新事件增量合并到其中：\n{existing_summary}"
        else:
            existing_section = ""

        system_prompt = prompt_template.replace("{existing_section}", existing_section)

        result = await self.call_json(
            system_prompt,
            f"故事背景：\n{story_summary}\n\n新事件：\n{recent_events}\n\n当前角色状态：\n{characters_status}",
            temperature=0.3,
        )
        return result
