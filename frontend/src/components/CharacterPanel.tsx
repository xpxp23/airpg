"use client";

import { useState, useEffect } from "react";
import { Character, GameAction } from "@/types";

interface CharacterPanelProps {
  characters: Character[];
  actions: GameAction[];
  myCharacter: Character | null;
  onClose: () => void;
  onCooperation: (targetActionId: string, text: string) => Promise<any>;
}

export function CharacterPanel({
  characters,
  actions,
  myCharacter,
  onClose,
  onCooperation,
}: CharacterPanelProps) {
  const [cooperationTarget, setCooperationTarget] = useState<string | null>(null);
  const [cooperationText, setCooperationText] = useState("");
  const [loading, setLoading] = useState(false);

  // Lock body scroll when panel is open on mobile
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  const getCharacterPendingAction = (charId: string) => {
    return actions.find(
      (a) => a.character_id === charId && a.status === "pending"
    );
  };

  const handleCooperation = async () => {
    if (!cooperationTarget || !cooperationText.trim()) return;
    setLoading(true);
    try {
      await onCooperation(cooperationTarget, cooperationText);
      setCooperationTarget(null);
      setCooperationText("");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="md:hidden fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel: mobile full-width drawer, desktop sidebar */}
      <div className="fixed md:static inset-y-0 right-0 z-50 w-full md:w-80 bg-fantasy-card/80 backdrop-blur-sm border-l border-fantasy-accent/10 flex flex-col">
        <div className="p-3 sm:p-4 border-b border-fantasy-accent/10 flex items-center justify-between">
          <h2 className="font-semibold text-fantasy-text text-sm sm:text-base">队伍状态</h2>
          <button
            onClick={onClose}
            className="p-1 text-fantasy-muted hover:text-fantasy-text transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
          {characters
            .filter((c) => c.player_id)
            .sort((a, b) => {
              if (a.id === myCharacter?.id) return -1;
              if (b.id === myCharacter?.id) return 1;
              return 0;
            })
            .map((char) => {
              const pending = getCharacterPendingAction(char.id);
              const isMe = char.id === myCharacter?.id;
              const health = char.status_effects?.health ?? 100;
              const items = char.status_effects?.items || [];

              return (
                <div
                  key={char.id}
                  className={`rounded-xl p-3 sm:p-4 border ${
                    isMe
                      ? "border-fantasy-accent/30 bg-fantasy-accent/5"
                      : "border-fantasy-accent/10"
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-semibold text-fantasy-text text-sm sm:text-base">
                        {char.name}
                        {isMe && (
                          <span className="text-xs text-fantasy-accent ml-2">你</span>
                        )}
                      </div>
                      {char.description && (
                        <div className="text-xs text-fantasy-muted mt-1 line-clamp-2">
                          {char.description}
                        </div>
                      )}
                    </div>
                    <span
                      className={`text-xs px-2 py-1 rounded-full shrink-0 ${
                        char.is_alive
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {char.is_alive ? "存活" : "倒下"}
                    </span>
                  </div>

                  {/* Health bar */}
                  <div className="mb-2">
                    <div className="flex justify-between text-xs text-fantasy-muted mb-1">
                      <span>❤️ 生命值</span>
                      <span>{health}/100</span>
                    </div>
                    <div className="w-full bg-fantasy-bg/50 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          health > 60
                            ? "bg-green-500"
                            : health > 30
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        }`}
                        style={{ width: `${health}%` }}
                      />
                    </div>
                  </div>

                  {/* Location */}
                  {char.location && (
                    <div className="text-xs text-fantasy-muted mb-2">
                      ️ {char.location}
                    </div>
                  )}

                  {/* Items */}
                  {items.length > 0 && (
                    <div className="text-xs text-fantasy-muted mb-2">
                       {items.join("、")}
                    </div>
                  )}

                  {/* Pending action */}
                  {pending && (
                    <div className="bg-fantasy-bg/30 rounded-lg p-2 mt-2">
                      <div className="text-xs text-fantasy-accent mb-1">⏳ 行动中</div>
                      <div className="text-xs text-fantasy-text">{pending.public_snippet}</div>
                      {pending.remaining_seconds !== undefined && pending.remaining_seconds > 0 && (
                        <div className="mt-1">
                          <div className="w-full bg-fantasy-bg/50 rounded-full h-1.5 progress-shimmer" />
                          <div className="text-xs text-fantasy-muted mt-1">
                            剩余 {Math.ceil(pending.remaining_seconds)} 秒
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Cooperation button */}
                  {!isMe && pending && !myCharacter?.status_effects?.injuries?.length && (
                    <button
                      onClick={() => setCooperationTarget(pending.id)}
                      className="mt-2 w-full bg-fantasy-accent/10 hover:bg-fantasy-accent/20 text-fantasy-accent text-xs py-2 rounded-lg transition-colors"
                    >
                       协作
                    </button>
                  )}
                </div>
              );
            })}
        </div>

        {/* Cooperation modal */}
        {cooperationTarget && (
          <div className="p-3 sm:p-4 border-t border-fantasy-accent/10">
            <h3 className="text-sm font-semibold text-fantasy-text mb-2">发起协作</h3>
            <textarea
              value={cooperationText}
              onChange={(e) => setCooperationText(e.target.value)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-3 py-2 text-fantasy-text text-sm placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors h-20 resize-none"
              placeholder="描述你如何帮助队友..."
            />
            <div className="flex space-x-2 mt-2">
              <button
                onClick={handleCooperation}
                disabled={loading || !cooperationText.trim()}
                className="flex-1 bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white py-2 rounded-lg text-sm transition-colors"
              >
                {loading ? "提交中..." : "发起协作"}
              </button>
              <button
                onClick={() => {
                  setCooperationTarget(null);
                  setCooperationText("");
                }}
                className="flex-1 bg-fantasy-card hover:bg-fantasy-card/80 text-fantasy-text py-2 rounded-lg text-sm transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
