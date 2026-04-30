"use client";

import { GameAction } from "@/types";

interface CooperationPanelProps {
  actions: GameAction[];
  myCharacterId: string | null;
  gameMode?: "waiting" | "instant";
}

export function CooperationPanel({ actions, myCharacterId, gameMode }: CooperationPanelProps) {
  const cooperationActions = actions.filter(
    (a) => a.action_type === "cooperation" && a.status === "pending"
  );

  if (cooperationActions.length === 0) {
    return null;
  }

  return (
    <div className="bg-fantasy-card/40 rounded-xl p-4 border border-fantasy-accent/10">
      <h3 className="text-sm font-semibold text-fantasy-text mb-3">  协作进行中</h3>
      <div className="space-y-3">
        {cooperationActions.map((action) => {
          const isMine = action.player_id === myCharacterId;
          return (
            <div
              key={action.id}
              className={`p-3 rounded-lg border ${
                isMine
                  ? "border-fantasy-accent/30 bg-fantasy-accent/5"
                  : "border-fantasy-accent/10"
              }`}
            >
              <div className="text-xs text-fantasy-accent mb-1">
                {isMine ? "你的协作" : "队友协作"}
              </div>
              <div className="text-sm text-fantasy-text">
                {action.public_snippet}
              </div>
              {gameMode !== "instant" && action.remaining_seconds !== undefined && action.remaining_seconds > 0 && (
                <div className="text-xs text-fantasy-muted mt-1">
                  ⏳ 剩余 {Math.ceil(action.remaining_seconds)} 秒
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
