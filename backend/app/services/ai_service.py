import json
import re
import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings

settings = get_settings()


class AIService:
    """统一 AI 服务，支持多模型和多提供商"""

    def __init__(self):
        # 根据配置初始化客户端
        self.provider = settings.AI_PROVIDER
        self._init_client()

    def _init_client(self):
        """初始化 AI 客户端"""
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
        if model:
            return model
        if premium:
            return settings.AI_MODEL_PREMIUM or settings.OPENAI_MODEL_GPT4O
        return settings.AI_MODEL_DEFAULT or settings.OPENAI_MODEL_MINI

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        premium: bool = False,
    ) -> dict:
        """调用 LLM 并确保返回有效 JSON"""
        model = self._get_model(model, premium)
        content = await self._call_llm(system_prompt, user_prompt, model, temperature, max_tokens, json_mode=True)

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
        max_tokens: int = 2000,
        premium: bool = False,
    ) -> str:
        """调用 LLM 获取文本响应"""
        model = self._get_model(model, premium)
        return await self._call_llm(system_prompt, user_prompt, model, temperature, max_tokens, json_mode=False)

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        """底层 LLM 调用，支持 OpenAI 和 Anthropic"""
        if self.is_anthropic:
            return await self._call_anthropic(system_prompt, user_prompt, model, temperature, max_tokens, json_mode)
        else:
            return await self._call_openai_compatible(system_prompt, user_prompt, model, temperature, max_tokens, json_mode)

    async def _call_openai_compatible(
        self, system_prompt: str, user_prompt: str, model: str,
        temperature: float, max_tokens: int, json_mode: bool
    ) -> str:
        """OpenAI 兼容 API 调用"""
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

        return response.choices[0].message.content or ""

    async def _call_anthropic(
        self, system_prompt: str, user_prompt: str, model: str,
        temperature: float, max_tokens: int, json_mode: bool
    ) -> str:
        """Anthropic Claude API 调用"""
        # Claude 使用 system 参数而非 system message
        if json_mode:
            system_prompt += "\n\n请严格以 JSON 格式返回结果，不要包含任何其他文本。"

        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text if response.content else ""

    async def parse_story(self, story_text: str, duration_hint: str | None = None) -> dict:
        system_prompt = """你是一个专业的跑团主持人助手（DM）。玩家上传了一段故事/小说文本，你需要从中提取结构化信息，为后续的游戏主持做准备。

提取要求：
1. 核心场景（地点列表）：从故事中识别所有重要地点，包含名称和简短描述
2. 可用角色：从故事中提取或推断出适合玩家扮演的角色，包含名字和背景
3. 主线目标：故事的核心驱动力和最终目标
4. 章节节奏计划：根据玩家设定的目标时长，将故事切分为若干章节，每章有明确的阶段性目标
5. 初始状态：游戏开始时的场景描述，作为开场叙事

重要约束：
- 角色数量建议 2-6 个，覆盖不同能力方向（探索、战斗、社交、知识等）
- 每个章节的时间比例之和应为 1.0
- 初始状态应引人入胜，让玩家有立即行动的欲望
- 如果原文信息不足，可以合理推断和扩展，但不要偏离原文基调

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
      "secrets": "隐藏信息（玩家探索后才能发现）"
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
}"""

        user_prompt = f"""故事文本：
---
{story_text}
---

玩家设定的目标时长：{duration_hint or "未指定"}

请解析上述故事并以 JSON 格式返回结构化信息。"""

        # 故事解析需要高质量模型
        return await self.call_json(
            system_prompt, user_prompt, temperature=0.3, premium=True
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
    ) -> dict:
        system_prompt = f"""你是一个跑团主持人（DM）。玩家正在你的游戏中行动，你需要评估每个行动的等待时间和公开描述。

当前游戏状态：
- 场景：{scene}
- 当前章节：第{chapter}章（{chapter_title}），目标：{chapter_goal}
- 已过时间：{elapsed_time} / {target_duration}
- 队伍状态：
{characters_status}

行动评估规则：

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

返回严格的 JSON：
{{
  "public_snippet": "角色名正在做什么...（15-50字，其他玩家可见的描述）",
  "wait_seconds": 150,
  "difficulty": "trivial|easy|medium|hard|extreme",
  "risk": "none|low|medium|high|critical",
  "hint": "给玩家的隐含提示（不会展示给其他玩家）"
}}"""

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
    ) -> dict:
        system_prompt = f"""你是一个才华横溢的跑团主持人（DM），擅长讲述引人入胜的故事。

你现在需要根据玩家的行动和当前游戏状态，生成行动结果的叙事。

游戏记忆（最近事件摘要）：
{game_memory}

当前场景：{current_scene}
角色状态：
{character_status}

行动详情：
- 角色：{character_name}
- 行动：{action_text}
- 等待时长：{wait_seconds} 秒
- 难度：{difficulty}
- 风险：{risk}

叙事要求：
1. 结果应与行动的难度和风险匹配
2. 高风险行动可能导致负面后果（受伤、失去物品等）
3. 叙事应生动、有画面感，像小说一样
4. 可以引入新的线索、物品、NPC 互动
5. 长度 150-400 字
6. 判断是否触发章节推进或游戏结局

返回严格的 JSON：
{{
  "narrative": "叙事正文...",
  "outcome": "success|partial_success|failure|critical_failure",
  "effects": {{
    "health_change": 0,
    "new_items": ["物品名称"],
    "lost_items": [],
    "new_status_effects": [],
    "location_change": null,
    "new_clues": ["发现的线索"],
    "npc_interaction": null
  }},
  "scene_update": {{
    "discovered_secrets": ["scene_1_secret"],
    "new_connections": []
  }},
  "chapter_progress": {{
    "advance_chapter": false,
    "progress_description": "当前章节进展描述"
  }},
  "game_over": false,
  "game_over_narrative": null,
  "importance": "low|medium|high|critical",
  "public_broadcast": true
}}"""

        # 叙事生成需要高质量模型
        return await self.call_json(
            system_prompt, f"玩家行动：{action_text}", temperature=0.8, premium=True
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
        system_prompt = f"""你是一个跑团主持人。一个玩家试图与另一个正在行动中的玩家进行协作。

协作发起者：{helper_name}（状态：{helper_status}）
目标行动：
- 角色：{target_name}
- 行动：{target_action}
- 已等待：{elapsed_seconds} / {total_wait_seconds} 秒
- 剩余：{remaining_seconds} 秒

协作描述：{cooperation_text}

评估规则：
- 协作本身也需要等待时间（通常为目标剩余时间的 30-70%）
- 协作成功率取决于描述合理性和角色能力
- 协作可以：缩短目标等待时间、直接完成目标行动、或失败
- 协作强调的是团队合作，双方都能获得收益

返回严格的 JSON：
{{
  "cooperation_wait_seconds": 60,
  "success_chance": 0.8,
  "result": "success|partial|failure",
  "target_time_reduction_percent": 60,
  "cooperation_narrative": "协作过程的简短描述（50-100字）",
  "cooperation_effects": {{
    "helper_health_change": 0,
    "helper_new_status": [],
    "target_health_change": 0
  }},
  "risk_to_helper": "none|low|medium|high"
}}"""

        return await self.call_json(system_prompt, f"协作描述：{cooperation_text}", temperature=0.2)

    async def compress_memory(self, recent_events: str, characters_status: str) -> str:
        system_prompt = """请将以下游戏事件压缩为简洁的摘要，保留关键信息（角色状态变化、重要发现、场景变化）。

输出 100-200 字的摘要，用于后续 AI 调用的上下文。"""

        result = await self.call_json(
            system_prompt,
            f"最近事件：\n{recent_events}\n\n当前角色状态：\n{characters_status}",
            temperature=0.3,
        )
        return result.get("summary", "")
