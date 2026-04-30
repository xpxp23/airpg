"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Game } from "@/types";

export default function GamesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [scope, setScope] = useState<"public" | "mine">("public");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadGames();
      const interval = setInterval(loadGames, 10000); // Refresh every 10s
      return () => clearInterval(interval);
    }
  }, [user, scope]);

  async function loadGames() {
    setLoading(true);
    try {
      const data = await api.listGames(scope);
      setGames(data);
    } catch (err) {
      console.error("Failed to load games:", err);
    } finally {
      setLoading(false);
    }
  }

  const statusLabels: Record<string, { label: string; color: string }> = {
    lobby: { label: "等待中", color: "bg-green-500/20 text-green-400" },
    active: { label: "进行中", color: "bg-blue-500/20 text-blue-400" },
    finished: { label: "已结束", color: "bg-gray-500/20 text-gray-400" },
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-fantasy-muted">加载中...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-4 sm:py-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-fantasy-text">游戏大厅</h1>
        <Link
          href="/games/new"
          className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-4 sm:px-6 py-2 rounded-lg transition-colors text-sm sm:text-base"
        >
          创建新游戏
        </Link>
      </div>

      <div className="flex space-x-2 sm:space-x-4 mb-4 sm:mb-6 overflow-x-auto">
        <button
          onClick={() => setScope("public")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            scope === "public"
              ? "bg-fantasy-accent text-white"
              : "bg-fantasy-card text-fantasy-muted hover:text-fantasy-text"
          }`}
        >
          公开房间
        </button>
        <button
          onClick={() => setScope("mine")}
          className={`px-4 py-2 rounded-lg text-sm transition-colors ${
            scope === "mine"
              ? "bg-fantasy-accent text-white"
              : "bg-fantasy-card text-fantasy-muted hover:text-fantasy-text"
          }`}
        >
          我的游戏
        </button>
      </div>

      {loading ? (
        <div className="text-center text-fantasy-muted py-12">加载中...</div>
      ) : games.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-4"> </div>
          <p className="text-fantasy-muted mb-4">还没有游戏</p>
          <Link
            href="/games/new"
            className="text-fantasy-accent hover:text-fantasy-accent/80"
          >
            创建第一个游戏
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {games.map((game) => (
            <Link
              key={game.id}
              href={`/games/${game.id}`}
              className="bg-fantasy-card/60 backdrop-blur-sm rounded-xl p-6 border border-fantasy-accent/10 hover:border-fantasy-accent/30 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <h2 className="text-lg font-semibold text-fantasy-text group-hover:text-fantasy-accent transition-colors line-clamp-1">
                  {game.title || "未命名游戏"}
                </h2>
                <span className={`text-xs px-2 py-1 rounded-full ${statusLabels[game.status]?.color || ""}`}>
                  {statusLabels[game.status]?.label || game.status}
                </span>
              </div>
              <div className="flex items-center space-x-4 text-sm text-fantasy-muted">
                <span>  {game.player_count}/{game.max_players}</span>
                <span>  第 {game.current_chapter} 章</span>
              </div>
              <div className="mt-3 text-xs text-fantasy-muted/60">
                {new Date(game.created_at).toLocaleDateString("zh-CN")}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
