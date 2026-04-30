"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";

export default function NewGamePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [storyText, setStoryText] = useState("");
  const [title, setTitle] = useState("");
  const [durationHint, setDurationHint] = useState("8小时");
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [gameMode, setGameMode] = useState<"waiting" | "instant">("waiting");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!storyText.trim()) {
      setError("请输入故事文本");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const game = await api.createGame({
        story_text: storyText,
        title: title || undefined,
        duration_hint: durationHint,
        max_players: maxPlayers,
        is_public: true,
        game_mode: gameMode,
      });
      router.push(`/games/${game.id}`);
    } catch (err: any) {
      setError(err.message || "创建失败");
    } finally {
      setLoading(false);
    }
  }

  if (authLoading || !user) {
    return (
      <div className="min-h-[calc(100dvh-4rem)] flex items-center justify-center">
        <div className="text-fantasy-muted">加载中...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-4 sm:py-8">
      <h1 className="text-2xl sm:text-3xl font-bold mb-4 sm:mb-8 bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
        创建新游戏
      </h1>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
        <div>
          <label className="block text-sm font-medium text-fantasy-muted mb-2">
            游戏标题（可选）
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-fantasy-card/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
            placeholder="留空将由 AI 自动生成"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-fantasy-muted mb-2">
            故事文本 <span className="text-fantasy-accent">*</span>
          </label>
          <textarea
            value={storyText}
            onChange={(e) => setStoryText(e.target.value)}
            className="w-full bg-fantasy-card/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors h-64 resize-y"
            placeholder="在这里粘贴你的故事、小说片段、原创剧情或世界观描述...&#10;&#10;AI 会自动解析其中的场景、角色和任务。"
            required
          />
          <p className="text-xs text-fantasy-muted/60 mt-1">
            {storyText.length} 字 | 建议 500-5000 字效果最佳
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              目标时长
            </label>
            <select
              value={durationHint}
              onChange={(e) => setDurationHint(e.target.value)}
              className="w-full bg-fantasy-card/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
            >
              <option value="2小时">2 小时（快速）</option>
              <option value="4小时">4 小时</option>
              <option value="8小时">8 小时（推荐）</option>
              <option value="1天">1 天</option>
              <option value="2天">2 天</option>
              <option value="3天">3 天</option>
              <option value="1周">1 周</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              最大玩家数
            </label>
            <select
              value={maxPlayers}
              onChange={(e) => setMaxPlayers(Number(e.target.value))}
              className="w-full bg-fantasy-card/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
            >
              <option value="2">2 人</option>
              <option value="3">3 人</option>
              <option value="4">4 人（推荐）</option>
              <option value="5">5 人</option>
              <option value="6">6 人</option>
              <option value="8">8 人</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-fantasy-muted mb-2">
            游戏模式
          </label>
          <div className="flex items-center h-[52px] space-x-4">
            <button
              type="button"
              onClick={() => setGameMode("waiting")}
              className={`flex-1 py-3 rounded-lg text-sm transition-colors ${
                gameMode === "waiting"
                  ? "bg-fantasy-accent text-white"
                  : "bg-fantasy-card text-fantasy-muted hover:text-fantasy-text"
              }`}
            >
              ⏳ 等待模式
            </button>
            <button
              type="button"
              onClick={() => setGameMode("instant")}
              className={`flex-1 py-3 rounded-lg text-sm transition-colors ${
                gameMode === "instant"
                  ? "bg-fantasy-accent text-white"
                  : "bg-fantasy-card text-fantasy-muted hover:text-fantasy-text"
              }`}
            >
              ⚡ 即玩模式
            </button>
          </div>
          <p className="text-xs text-fantasy-muted/60 mt-1">
            {gameMode === "waiting"
              ? "行动需要等待时间，AI 会根据行动复杂度自动评估"
              : "行动立即完成，无需等待，适合快速体验剧情"}
          </p>
        </div>

        <div className="bg-fantasy-card/30 rounded-xl p-4 sm:p-6 border border-fantasy-accent/10">
          <h3 className="text-base sm:text-lg font-semibold text-fantasy-text mb-2">  AI 将会...</h3>
          <ul className="space-y-2 text-fantasy-muted text-sm">
            <li className="flex items-start">
              <span className="text-fantasy-accent mr-2">•</span>
              解析你的故事文本，提取场景、角色和任务
            </li>
            <li className="flex items-start">
              <span className="text-fantasy-accent mr-2">•</span>
              根据目标时长规划章节节奏
            </li>
            <li className="flex items-start">
              <span className="text-fantasy-accent mr-2">•</span>
              生成引人入胜的开场叙事
            </li>
            <li className="flex items-start">
              <span className="text-fantasy-accent mr-2">•</span>
              担任游戏主持人，回应玩家的每一个行动
            </li>
          </ul>
        </div>

        <button
          type="submit"
          disabled={loading || !storyText.trim()}
          className="w-full bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white py-4 rounded-lg text-lg font-semibold transition-colors shadow-lg shadow-fantasy-accent/25"
        >
          {loading ? "AI 解析中，请稍候..." : "创建游戏"}
        </button>
      </form>
    </div>
  );
}
