"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useGameState } from "@/hooks/useGameState";
import { api } from "@/lib/api";
import { GameAction, GameEvent } from "@/types";
import { CharacterPanel } from "@/components/CharacterPanel";
import { ActionInput } from "@/components/ActionInput";
import { CooperationPanel } from "@/components/CooperationPanel";

export default function GameRoomPage() {
  const params = useParams();
  const gameId = params.id as string;
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const {
    game,
    characters,
    actions,
    events,
    myCharacter,
    pendingAction,
    loading,
    error,
    refresh,
    submitAction,
    submitCooperation,
    cancelAction,
  } = useGameState(gameId, user?.id);

  const [showCharacters, setShowCharacters] = useState(false);
  const [joining, setJoining] = useState(false);
  const [starting, setStarting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [allEvents, setAllEvents] = useState<GameEvent[]>([]);
  const [loadingAllEvents, setLoadingAllEvents] = useState(false);
  const eventsEndRef = useRef<HTMLDivElement>(null);
  const eventsContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Track if user is near the bottom of the event stream
  const handleScroll = () => {
    const el = eventsContainerRef.current;
    if (!el) return;
    const threshold = 120;
    isNearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
  };

  // Auto-scroll only when user is already near the bottom
  useEffect(() => {
    if (isNearBottomRef.current) {
      eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events]);

  const handleJoin = async (characterId?: string) => {
    setJoining(true);
    try {
      await api.joinGame(gameId, characterId);
      refresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setJoining(false);
    }
  };

  const handleLeave = async () => {
    try {
      await api.leaveGame(gameId);
      refresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDisband = async () => {
    if (!confirm("确定要解散房间吗？此操作不可撤销。")) return;
    try {
      await api.disbandGame(gameId);
      router.push("/games");
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleStart = async () => {
    setStarting(true);
    try {
      await api.startGame(gameId);
      refresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setStarting(false);
    }
  };

  const handleRetryParse = async () => {
    setRetrying(true);
    try {
      await api.retryParse(gameId);
      refresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setRetrying(false);
    }
  };

  const handleEndGame = async () => {
    if (!confirm("确定要结束本局游戏吗？")) return;
    try {
      await api.endGame(gameId);
      refresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Load all events for summary view
  useEffect(() => {
    if ((game?.status === "finished" || game?.status === "abandoned") && allEvents.length === 0) {
      setLoadingAllEvents(true);
      api.getEvents(gameId, undefined, 9999)
        .then((res) => {
          setAllEvents(res.events || []);
        })
        .catch(() => {})
        .finally(() => setLoadingAllEvents(false));
    }
  }, [game?.status, gameId]);

  const getEventDisplay = (event: GameEvent) => {
    const { type, data } = event;
    switch (type) {
      case "game_start":
        return {
          content: data.narrative || "游戏开始了！",
          isSystem: false,
          icon: " ",
          characterName: "旁白",
          isNarrative: true,
        };
      case "game_end":
        return {
          content: `故事落幕。${data.reason || ""}`,
          isSystem: true,
          icon: " ",
        };
      case "player_join":
        return {
          content: `${data.character_name} 加入了冒险队伍`,
          isSystem: true,
          icon: " ",
        };
      case "midgame_join":
        return {
          content: `${data.character_name} 在冒险中途加入了队伍`,
          isSystem: true,
          icon: " ",
        };
      case "action_start":
        return {
          content: data.public_snippet || `${data.character_name} 开始行动`,
          actionText: data.input_text,
          isSystem: false,
          icon: "⏳",
          characterName: data.character_name,
          isAction: true,
        };
      case "action_result":
        return {
          content: data.narrative || `${data.character_name} 完成了行动`,
          isSystem: false,
          icon: " ",
          characterName: data.character_name,
          isNarrative: true,
        };
      case "cooperation_start":
        return {
          content: data.public_snippet || `${data.helper_name} 正在协助 ${data.target_name}`,
          isSystem: false,
          icon: " ",
          characterName: data.helper_name,
        };
      case "cooperation_result":
        return {
          content: data.narrative || `${data.helper_name} 完成了协助`,
          isSystem: false,
          icon: " ",
          characterName: data.helper_name,
        };
      case "chapter_advance":
        return {
          content: `故事进入第 ${data.chapter} 章${data.description ? `：${data.description}` : ""}`,
          isSystem: true,
          icon: " ",
        };
      case "system_message":
        return {
          content: data.message || "",
          isSystem: true,
          icon: " ",
        };
      default:
        return {
          content: JSON.stringify(data),
          isSystem: true,
          icon: " ",
        };
    }
  };

  const sortedEvents = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  if (authLoading || !user) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-fantasy-muted">加载中...</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-fantasy-muted">加载游戏中...</div>
      </div>
    );
  }

  if (error || !game) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-red-400">{error || "游戏不存在"}</div>
      </div>
    );
  }

  // Lobby state
  if (game.status === "lobby") {
    const presetChars = game.ai_summary?.preset_characters || [];
    const isCreator = game.creator_id === user.id;
    const hasCharacter = characters.some((c) => c.player_id === user.id);

    return (
      <div className="max-w-4xl mx-auto px-4 py-4 sm:py-8">
        <div className="bg-fantasy-card/60 backdrop-blur-sm rounded-2xl p-4 sm:p-8 border border-fantasy-accent/10">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-fantasy-text">
              {game.title || "准备中..."}
            </h1>
            <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${
              game.game_mode === "instant"
                ? "bg-yellow-500/20 text-yellow-400"
                : "bg-blue-500/20 text-blue-400"
            }`}>
              {game.game_mode === "instant" ? "⚡ 即玩" : "⏳ 等待"}
            </span>
          </div>

          {game.parse_status === "processing" && (
            <div className="bg-fantasy-accent/10 border border-fantasy-accent/20 rounded-lg px-4 py-3 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="animate-spin w-5 h-5 border-2 border-fantasy-accent border-t-transparent rounded-full" />
                  <span className="text-fantasy-accent text-sm">AI 正在解析故事文本，请稍候...</span>
                </div>
                <button
                  onClick={handleRetryParse}
                  disabled={retrying}
                  className="text-fantasy-muted hover:text-fantasy-accent text-xs transition-colors"
                >
                  重新解析
                </button>
              </div>
            </div>
          )}

          {game.parse_status === "failed" && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-red-400 text-lg">⚠️</span>
                  <div>
                    <p className="text-red-400 text-sm font-medium">AI 解析失败</p>
                    <p className="text-red-400/60 text-xs mt-1">
                      {game.parse_error || "故事文本解析过程中出现错误"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleRetryParse}
                  disabled={retrying}
                  className="bg-red-500/20 hover:bg-red-500/30 disabled:opacity-50 text-red-400 px-4 py-2 rounded-lg text-sm transition-colors"
                >
                  {retrying ? "重试中..." : "重新解析"}
                </button>
              </div>
            </div>
          )}

          {game.parse_status === "pending" && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-3 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-yellow-400 text-lg">⏳</span>
                  <div>
                    <p className="text-yellow-400 text-sm font-medium">等待解析</p>
                    <p className="text-yellow-400/60 text-xs mt-1">故事文本正在排队等待解析</p>
                  </div>
                </div>
                <button
                  onClick={handleRetryParse}
                  disabled={retrying}
                  className="bg-yellow-500/20 hover:bg-yellow-500/30 disabled:opacity-50 text-yellow-400 px-4 py-2 rounded-lg text-sm transition-colors"
                >
                  {retrying ? "解析中..." : "开始解析"}
                </button>
              </div>
            </div>
          )}
          {game.ai_summary && (
            <div className="bg-fantasy-bg/30 rounded-xl p-6 mb-6">
              <h2 className="text-lg font-semibold text-fantasy-text mb-3">  故事简介</h2>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-fantasy-muted mb-4">
                <span><span className="text-fantasy-muted/60">类型：</span>{game.ai_summary.genre}</span>
                <span><span className="text-fantasy-muted/60">基调：</span>{game.ai_summary.tone}</span>
                <span><span className="text-fantasy-muted/60">目标：</span>{game.ai_summary.main_goal}</span>
              </div>
              <p className="text-fantasy-text/80 text-[15px] leading-[1.8]">
                {game.ai_summary.initial_state?.narrative?.substring(0, 300)}...
              </p>
            </div>
          )}

          <div className="mb-4 sm:mb-6">
            <h2 className="text-base sm:text-lg font-semibold text-fantasy-text mb-3 sm:mb-4">
              选择角色 ({characters.filter((c) => c.player_id).length}/{game.max_players})
            </h2>
            {game.parse_status !== "completed" ? (
              <p className="text-fantasy-muted text-sm">等待 AI 解析完成后可选择角色...</p>
            ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
              {presetChars.map((pc) => {
                const charId = pc.db_id || pc.id;
                const dbChar = characters.find((c) => c.id === charId);
                const taken = dbChar && dbChar.player_id;
                const isMyChar = dbChar && dbChar.player_id === user.id;
                const canSwitch = !taken || isMyChar;
                return (
                  <button
                    key={charId}
                    onClick={() => canSwitch && !joining && handleJoin(charId)}
                    disabled={!canSwitch || joining}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      isMyChar
                        ? "border-green-500/50 bg-green-500/10 cursor-default"
                        : taken
                        ? "border-fantasy-muted/20 opacity-50 cursor-not-allowed"
                        : "border-fantasy-accent/20 hover:border-fantasy-accent/50 cursor-pointer"
                    }`}
                  >
                    <div className="font-semibold text-fantasy-text">
                      {pc.name}
                      {isMyChar && <span className="text-green-400 text-sm ml-2">当前角色</span>}
                      {taken && !isMyChar && <span className="text-fantasy-muted text-sm ml-2">已被选择</span>}
                    </div>
                    <div className="text-sm text-fantasy-muted mt-1">{pc.description}</div>
                    <div className="text-xs text-fantasy-muted/60 mt-2">
                      技能：{pc.skills?.join("、") || "无特殊技能"}
                    </div>
                  </button>
                );
              })}
            </div>
            )}
          </div>

          <div className="mb-6">
            <h3 className="text-md font-semibold text-fantasy-text mb-2">或自创角色</h3>
            <button
              onClick={() => handleJoin()}
              disabled={joining}
              className="bg-fantasy-card hover:bg-fantasy-card/80 disabled:opacity-50 border border-fantasy-accent/20 text-fantasy-text px-6 py-3 rounded-lg transition-colors"
            >
              {joining ? "加入中..." : hasCharacter ? "切换为自定义角色" : "创建自定义角色"}
            </button>
          </div>

          {hasCharacter && (
            <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg mb-6 flex items-center justify-between">
              <span>你已选择角色：{myCharacter?.name || "未知"}，点击其他角色可切换</span>
              {!isCreator && (
                <button
                  onClick={handleLeave}
                  className="text-sm text-red-400 hover:text-red-300 ml-4"
                >
                  退出房间
                </button>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-sm text-fantasy-muted mb-4">
            <span>当前 {characters.filter((c) => c.player_id).length} / {game.max_players} 名玩家</span>
          </div>

          {isCreator && (
            <div className="space-y-3">
              <button
                onClick={handleStart}
                disabled={game.parse_status !== "completed" || characters.filter((c) => c.player_id).length === 0 || starting}
                className="w-full bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 disabled:cursor-not-allowed text-white py-4 rounded-lg text-lg font-semibold transition-colors shadow-lg shadow-fantasy-accent/25"
              >
                {starting ? "启动中..." : game.parse_status === "pending" ? "等待解析开始..." : game.parse_status === "processing" ? "等待 AI 解析完成..." : game.parse_status === "failed" ? "解析失败，请重试" : characters.filter((c) => c.player_id).length === 0 ? "等待玩家加入..." : "开始游戏"}
              </button>
              <button
                onClick={handleDisband}
                className="w-full bg-transparent border border-red-500/30 hover:bg-red-500/10 text-red-400 py-2 rounded-lg text-sm transition-colors"
              >
                解散房间
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Finished / Abandoned game — summary view
  if (game.status === "finished" || game.status === "abandoned") {
    const sortedAllEvents = [...allEvents].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const gameDuration = game.started_at && game.finished_at
      ? Math.round((new Date(game.finished_at).getTime() - new Date(game.started_at).getTime()) / 60000)
      : null;

    return (
      <div className="max-w-4xl mx-auto px-4 py-4 sm:py-8">
        <div className="bg-fantasy-card/60 backdrop-blur-sm rounded-2xl p-4 sm:p-8 border border-fantasy-accent/10">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-fantasy-text">
                {game.title || "冒险结束"}
              </h1>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-fantasy-muted mt-2">
                {game.status === "finished" ? (
                  <span className="text-green-400">故事落幕</span>
                ) : (
                  <span className="text-yellow-400">已解散</span>
                )}
                {gameDuration !== null && <span>时长 {gameDuration} 分钟</span>}
                <span>第 {game.current_chapter} 章</span>
              </div>
            </div>
            <button
              onClick={() => router.push("/games")}
              className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-4 py-2 rounded-lg text-sm transition-colors"
            >
              返回游戏列表
            </button>
          </div>

          {/* Story Recap */}
          {game.story_recap && (
            <div className="bg-fantasy-bg/30 rounded-xl p-6 mb-6">
              <h2 className="text-lg font-semibold text-fantasy-text mb-3">  故事回顾</h2>
              <p className="text-fantasy-text/80 text-[15px] leading-[1.8] whitespace-pre-line">
                {game.story_recap}
              </p>
            </div>
          )}
          {game.status === "finished" && !game.story_recap && (
            <div className="bg-fantasy-bg/30 rounded-xl p-6 mb-6">
              <h2 className="text-lg font-semibold text-fantasy-text mb-3">  故事回顾</h2>
              <p className="text-fantasy-muted text-sm">AI 正在生成故事回顾，请稍后刷新页面...</p>
            </div>
          )}

          {/* Character Final Status */}
          {characters.length > 0 && (
            <div className="bg-fantasy-bg/30 rounded-xl p-6 mb-6">
              <h2 className="text-lg font-semibold text-fantasy-text mb-3">  角色最终状态</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {characters.map((c) => (
                  <div
                    key={c.id}
                    className={`p-4 rounded-lg border ${
                      c.is_alive
                        ? "border-green-500/20 bg-green-500/5"
                        : "border-red-500/20 bg-red-500/5"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-fantasy-text">{c.name}</span>
                      <span className={`text-xs ${c.is_alive ? "text-green-400" : "text-red-400"}`}>
                        {c.is_alive ? "存活" : "死亡"}
                      </span>
                    </div>
                    {c.location && (
                      <p className="text-xs text-fantasy-muted">位置：{c.location}</p>
                    )}
                    {c.status_effects?.health !== undefined && (
                      <p className="text-xs text-fantasy-muted">生命值：{c.status_effects.health}</p>
                    )}
                    {c.status_effects?.items && c.status_effects.items.length > 0 && (
                      <p className="text-xs text-fantasy-muted">物品：{c.status_effects.items.join("、")}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full Event Timeline */}
          <div className="bg-fantasy-bg/30 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-fantasy-text mb-3">  完整事件时间线</h2>
            {loadingAllEvents ? (
              <p className="text-fantasy-muted text-sm">加载事件记录中...</p>
            ) : sortedAllEvents.length === 0 ? (
              <p className="text-fantasy-muted text-sm">暂无事件记录</p>
            ) : (
              <div className="max-h-[60vh] overflow-y-auto space-y-2 pr-2">
                {sortedAllEvents.map((event) => {
                  const display = getEventDisplay(event);
                  const time = new Date(event.timestamp).toLocaleString("zh-CN", {
                    month: "2-digit",
                    day: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  });

                  if (display.isNarrative) {
                    return (
                      <div key={event.id} className="bg-fantasy-card/40 rounded-lg p-3 border border-fantasy-accent/10">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm">{display.icon}</span>
                          <span className="font-semibold text-fantasy-accent text-xs">{display.characterName}</span>
                          <span className="text-fantasy-muted/40 text-[10px] ml-auto tabular-nums">{time}</span>
                        </div>
                        <p className="text-fantasy-text/80 text-[13px] leading-[1.7] whitespace-pre-line">
                          {display.content}
                        </p>
                      </div>
                    );
                  }

                  if (display.isAction) {
                    return (
                      <div key={event.id} className="bg-fantasy-accent/5 rounded-lg p-3 border border-fantasy-accent/15">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm">{display.icon}</span>
                          <span className="font-semibold text-fantasy-accent/90 text-xs">{display.characterName}</span>
                          <span className="text-fantasy-muted/40 text-[10px] ml-auto tabular-nums">{time}</span>
                        </div>
                        {display.actionText && (
                          <p className="text-fantasy-text/80 text-xs mb-1">「{display.actionText}」</p>
                        )}
                        <p className="text-fantasy-muted/50 text-[11px]">{display.content}</p>
                      </div>
                    );
                  }

                  return (
                    <div key={event.id} className="flex items-start gap-2 text-fantasy-muted/70 text-xs py-1">
                      <span className="shrink-0 mt-0.5">{display.icon}</span>
                      <span>{display.content}</span>
                      <span className="shrink-0 ml-auto text-fantasy-muted/40 tabular-nums">{time}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Active game - mid-game join UI for users without a character
  if (game.status === "active" && !myCharacter) {
    const presetChars = game.ai_summary?.preset_characters || [];
    const unclaimedChars = presetChars.filter((pc) => {
      const charId = pc.db_id || pc.id;
      const dbChar = characters.find((c) => c.id === charId);
      return !dbChar || !dbChar.player_id;
    });

    return (
      <div className="max-w-3xl mx-auto px-4 py-4 sm:py-8">
        <div className="bg-fantasy-card/60 backdrop-blur-sm rounded-2xl p-4 sm:p-8 border border-fantasy-accent/10">
          <h1 className="text-2xl sm:text-3xl font-bold text-fantasy-text mb-2">
            {game.title || "冒险进行中"}
          </h1>
          <p className="text-fantasy-muted text-sm mb-6">
            这局游戏已经开始了！你可以中途加入，选择一个角色或创建自定义角色。
          </p>

          {/* Game state summary */}
          <div className="bg-fantasy-bg/30 rounded-xl p-4 mb-6">
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-fantasy-muted">
              <span>第 {game.current_chapter} 章</span>
              <span>{characters.filter((c) => c.player_id && c.is_alive).length} 名冒险者存活</span>
              <span>{characters.filter((c) => c.player_id).length}/{game.max_players} 已加入</span>
            </div>
            {game.ai_summary?.initial_state?.narrative && (
              <p className="text-fantasy-text/70 text-sm mt-3 leading-relaxed">
                {game.ai_summary.initial_state.narrative.substring(0, 200)}...
              </p>
            )}
          </div>

          {/* Available preset characters */}
          {unclaimedChars.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-fantasy-text mb-3">
                可选角色 ({unclaimedChars.length} 个空位)
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {unclaimedChars.map((pc) => {
                  const charId = pc.db_id || pc.id;
                  return (
                    <button
                      key={charId}
                      onClick={() => handleJoin(charId)}
                      disabled={joining}
                      className="p-4 rounded-xl border border-fantasy-accent/20 hover:border-fantasy-accent/50 text-left transition-all"
                    >
                      <div className="font-semibold text-fantasy-text">{pc.name}</div>
                      <div className="text-sm text-fantasy-muted mt-1">{pc.description}</div>
                      <div className="text-xs text-fantasy-muted/60 mt-2">
                        技能：{pc.skills?.join("、") || "无特殊技能"}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Custom character option */}
          <div className="mb-4">
            <h3 className="text-md font-semibold text-fantasy-text mb-2">或自创角色</h3>
            <button
              onClick={() => handleJoin()}
              disabled={joining}
              className="bg-fantasy-card hover:bg-fantasy-card/80 disabled:opacity-50 border border-fantasy-accent/20 text-fantasy-text px-6 py-3 rounded-lg transition-colors"
            >
              {joining ? "加入中..." : "创建自定义角色加入"}
            </button>
          </div>

          <p className="text-xs text-fantasy-muted/50 mt-4">
            中途加入的角色将以当前章节的场景为起点开始冒险
          </p>
        </div>
      </div>
    );
  }

  // Active game state
  return (
    <div className="flex h-[100dvh] md:h-[calc(100vh-4rem)]">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Game header */}
        <div className="bg-fantasy-card/60 backdrop-blur-sm border-b border-fantasy-accent/10 px-3 sm:px-4 py-2 sm:py-2.5 flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-semibold text-fantasy-text truncate">
                {game.title || "游戏进行中"}
              </h1>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                game.game_mode === "instant"
                  ? "bg-yellow-500/20 text-yellow-400"
                  : "bg-blue-500/20 text-blue-400"
              }`}>
                {game.game_mode === "instant" ? "⚡即玩" : "⏳等待"}
              </span>
            </div>
            <div className="text-[10px] sm:text-xs text-fantasy-muted/60">
              第 {game.current_chapter} 章 · {characters.filter((c) => c.player_id && c.is_alive).length} 名冒险者存活
            </div>
          </div>
          <div className="shrink-0 flex items-center gap-1.5 sm:gap-2 ml-2">
            {game.creator_id === user.id && (
              <button
                onClick={handleEndGame}
                className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs transition-colors"
              >
                结束
              </button>
            )}
            <button
              onClick={() => setShowCharacters(!showCharacters)}
              className="bg-fantasy-card hover:bg-fantasy-card/80 text-fantasy-text/80 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg text-[10px] sm:text-xs transition-colors"
            >
               角色
            </button>
          </div>
        </div>

        {/* Events stream */}
        <div
          ref={eventsContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 sm:py-6 space-y-2 sm:space-y-3"
        >
          {sortedEvents.map((event) => {
            const display = getEventDisplay(event);
            const time = new Date(event.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

            // System messages: left-aligned, subtle
            if (display.isSystem) {
              return (
                <div key={event.id} className="message-enter flex items-start gap-2 text-fantasy-muted/70 text-xs py-1">
                  <span className="shrink-0 mt-0.5">{display.icon}</span>
                  <span>{display.content}</span>
                  <span className="shrink-0 ml-auto text-fantasy-muted/40 tabular-nums">{time}</span>
                </div>
              );
            }

            // Narrative results: card with rich text
            if (display.isNarrative) {
              return (
                <div key={event.id} className="message-enter bg-fantasy-card/40 rounded-xl p-3 sm:p-5 border border-fantasy-accent/10">
                  <div className="flex items-center gap-2 mb-2 sm:mb-3">
                    <span className="text-sm">{display.icon}</span>
                    <span className="font-semibold text-fantasy-accent text-xs sm:text-sm">{display.characterName}</span>
                    <span className="text-fantasy-muted/40 text-[10px] sm:text-xs ml-auto tabular-nums">{time}</span>
                  </div>
                  <p className="text-fantasy-text/90 text-[13px] sm:text-[15px] leading-[1.7] sm:leading-[1.8] whitespace-pre-line">
                    {display.content}
                  </p>
                </div>
              );
            }

            // Action start: card showing player's action
            if (display.isAction) {
              return (
                <div key={event.id} className="message-enter bg-fantasy-accent/5 rounded-xl p-3 sm:p-4 border border-fantasy-accent/15">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm">{display.icon}</span>
                    <span className="font-semibold text-fantasy-accent/90 text-xs sm:text-sm">{display.characterName}</span>
                    <span className="text-fantasy-muted/40 text-[10px] sm:text-xs ml-auto tabular-nums">{time}</span>
                  </div>
                  {display.actionText && (
                    <p className="text-fantasy-text/80 text-[13px] sm:text-sm leading-relaxed mb-1.5">
                      「{display.actionText}」
                    </p>
                  )}
                  <p className="text-fantasy-muted/50 text-[11px] sm:text-xs">{display.content}</p>
                </div>
              );
            }

            // Cooperation start / other: compact inline
            return (
              <div key={event.id} className="message-enter flex items-start gap-2 text-sm py-1">
                <span className="shrink-0 mt-0.5">{display.icon}</span>
                <div className="min-w-0 flex-1">
                  <span className="font-medium text-fantasy-accent/80">{display.characterName}</span>{" "}
                  <span className="text-fantasy-muted/60">{display.content}</span>
                </div>
                <span className="shrink-0 text-fantasy-muted/40 text-xs tabular-nums mt-0.5">{time}</span>
              </div>
            );
          })}
          <div ref={eventsEndRef} />
        </div>

        {/* Action input */}
        <ActionInput
          pendingAction={pendingAction}
          onSubmit={submitAction}
          onCancel={cancelAction}
          gameMode={game.game_mode}
        />
      </div>

      {/* Character panel sidebar */}
      {showCharacters && (
        <CharacterPanel
          characters={characters}
          actions={actions}
          myCharacter={myCharacter}
          onClose={() => setShowCharacters(false)}
          onCooperation={(targetActionId, text) =>
            submitCooperation(targetActionId, text)
          }
          gameMode={game.game_mode}
        />
      )}
    </div>
  );
}
