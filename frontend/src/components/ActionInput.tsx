"use client";

import { useState, useEffect } from "react";
import { GameAction } from "@/types";

interface ActionInputProps {
  pendingAction: GameAction | null;
  onSubmit: (text: string) => Promise<any>;
  onCancel: (actionId: string) => Promise<void>;
}

export function ActionInput({ pendingAction, onSubmit, onCancel }: ActionInputProps) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    if (!pendingAction || pendingAction.remaining_seconds === undefined) return;

    setRemaining(Math.ceil(pendingAction.remaining_seconds));

    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 0) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [pendingAction]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      await onSubmit(text);
      setText("");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (pendingAction) {
    return (
      <div className="bg-fantasy-card/60 backdrop-blur-sm border-t border-fantasy-accent/10 p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-sm text-fantasy-accent">⏳ 行动进行中</div>
            <div className="text-fantasy-text text-sm mt-1">
              {pendingAction.public_snippet}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-fantasy-accent">
              {Math.floor(remaining / 60)}:{(remaining % 60).toString().padStart(2, "0")}
            </div>
            <div className="text-xs text-fantasy-muted">剩余时间</div>
          </div>
        </div>
        <div className="w-full bg-fantasy-bg/50 rounded-full h-2 mb-3">
          <div
            className="h-2 rounded-full progress-shimmer transition-all"
            style={{
              width: `${Math.max(
                0,
                Math.min(
                  100,
                  ((pendingAction.wait_seconds - remaining) / pendingAction.wait_seconds) * 100
                )
              )}%`,
            }}
          />
        </div>
        <button
          onClick={() => onCancel(pendingAction.id)}
          className="text-fantasy-muted hover:text-fantasy-accent text-sm transition-colors"
        >
          取消行动
        </button>
      </div>
    );
  }

  return (
    <div className="bg-fantasy-card/60 backdrop-blur-sm border-t border-fantasy-accent/10 p-4">
      <form onSubmit={handleSubmit} className="flex space-x-3">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1 bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
          placeholder="描述你的行动...（如：我搜索书桌的抽屉）"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !text.trim()}
          className="bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
        >
          {loading ? "提交中..." : "行动"}
        </button>
      </form>
      <div className="text-xs text-fantasy-muted/60 mt-2">
        提示：描述越具体，AI 生成的故事越精彩
      </div>
    </div>
  );
}
