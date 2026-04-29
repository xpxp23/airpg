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
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
      case "action_start":
        return {
          content: data.public_snippet || `${data.character_name} 开始行动`,
          isSystem: false,
          icon: "⏳",
          characterName: data.character_name,
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
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-fantasy-card/60 backdrop-blur-sm rounded-2xl p-8 border border-fantasy-accent/10">
          <h1 className="text-3xl font-bold mb-2 text-fantasy-text">
            {game.title || "准备中..."}
          </h1>

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
          <p className="text-fantasy-muted mb-6">
            邀请码：<span className="text-fantasy-accent font-mono">{game.invite_code}</span>
          </p>

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

          <div className="mb-6">
            <h2 className="text-lg font-semibold text-fantasy-text mb-4">
              选择角色 ({characters.filter((c) => c.player_id).length}/{game.max_players})
            </h2>
            {game.parse_status !== "completed" ? (
              <p className="text-fantasy-muted text-sm">等待 AI 解析完成后可选择角色...</p>
            ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

  // Active game state
  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Game header */}
        <div className="bg-fantasy-card/60 backdrop-blur-sm border-b border-fantasy-accent/10 px-4 py-2.5 flex items-center justify-between">
          <div className="min-w-0">
            <h1 className="text-base font-semibold text-fantasy-text truncate">
              {game.title || "游戏进行中"}
            </h1>
            <div className="text-xs text-fantasy-muted/60">
              第 {game.current_chapter} 章 · {characters.filter((c) => c.is_alive).length} 名冒险者存活
            </div>
          </div>
          <div className="shrink-0 flex items-center gap-2">
            {game.creator_id === user.id && (
              <button
                onClick={handleEndGame}
                className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-xs transition-colors"
              >
                结束本局
              </button>
            )}
            <button
              onClick={() => setShowCharacters(!showCharacters)}
              className="bg-fantasy-card hover:bg-fantasy-card/80 text-fantasy-text/80 px-3 py-1.5 rounded-lg text-xs transition-colors"
            >
               角色
            </button>
          </div>
        </div>

        {/* Events stream */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-3">
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
                <div key={event.id} className="message-enter bg-fantasy-card/40 rounded-xl p-5 border border-fantasy-accent/10">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm">{display.icon}</span>
                    <span className="font-semibold text-fantasy-accent text-sm">{display.characterName}</span>
                    <span className="text-fantasy-muted/40 text-xs ml-auto tabular-nums">{time}</span>
                  </div>
                  <p className="text-fantasy-text/90 text-[15px] leading-[1.8] whitespace-pre-line">
                    {display.content}
                  </p>
                </div>
              );
            }

            // Action start / cooperation start: compact inline
            return (
              <div key={event.id} className="message-enter flex items-center gap-2 text-sm py-1">
                <span className="shrink-0">{display.icon}</span>
                <span className="font-medium text-fantasy-accent/80">{display.characterName}</span>
                <span className="text-fantasy-muted/60 truncate">{display.content}</span>
                <span className="shrink-0 text-fantasy-muted/40 text-xs ml-auto tabular-nums">{time}</span>
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
        />
      )}
    </div>
  );
}
