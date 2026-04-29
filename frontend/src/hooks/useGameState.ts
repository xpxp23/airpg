"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { Game, Character, GameAction, GameEvent } from "@/types";

interface GameState {
  game: Game | null;
  characters: Character[];
  actions: GameAction[];
  events: GameEvent[];
  myCharacter: Character | null;
  pendingAction: GameAction | null;
}

export function useGameState(gameId: string, userId?: string) {
  const [state, setState] = useState<GameState>({
    game: null,
    characters: [],
    actions: [],
    events: [],
    myCharacter: null,
    pendingAction: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastEventTime = useRef<string | null>(null);
  const pollInterval = useRef<NodeJS.Timeout | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [game, characters, actionsResult, eventsResult] = await Promise.all([
        api.getGame(gameId),
        api.getCharacters(gameId),
        api.getActions(gameId),
        api.getEvents(gameId, lastEventTime.current || undefined),
      ]);

      const actions = actionsResult.actions;
      const events = eventsResult.events;

      // Update last event time for incremental polling
      if (events.length > 0) {
        const newest = events.reduce((a, b) =>
          new Date(a.timestamp) > new Date(b.timestamp) ? a : b
        );
        lastEventTime.current = newest.timestamp;
      }

      // Find current user's character
      const myChar = userId ? characters.find((c) => c.player_id === userId) || null : null;
      const pending = actions.find(
        (a) => a.status === "pending" && a.character_id === myChar?.id
      ) || null;

      setState((prev) => ({
        game,
        characters,
        actions: [
          ...prev.actions.filter(
            (a) => !actions.find((newA) => newA.id === a.id)
          ),
          ...actions,
        ],
        events: [
          ...prev.events,
          ...events.filter(
            (e) => !prev.events.find((oldE) => oldE.id === e.id)
          ),
        ],
        myCharacter: myChar,
        pendingAction: pending,
      }));

      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [gameId, userId]);

  // Initial load
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Polling - adaptive interval based on game state
  useEffect(() => {
    const getInterval = () => {
      if (state.game?.status === "lobby") return 5000;  // 5s in lobby for real-time feel
      return 10000; // 10s in active game
    };

    pollInterval.current = setInterval(refresh, getInterval());
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [refresh, state.game?.status]);

  const submitAction = useCallback(
    async (actionText: string) => {
      if (!state.myCharacter) throw new Error("No character");
      const action = await api.submitAction(gameId, state.myCharacter.id, actionText);
      setState((prev) => ({
        ...prev,
        actions: [...prev.actions, action],
        pendingAction: action,
      }));
      return action;
    },
    [gameId, state.myCharacter]
  );

  const submitCooperation = useCallback(
    async (targetActionId: string, cooperationText: string) => {
      if (!state.myCharacter) throw new Error("No character");
      const action = await api.submitCooperation(
        gameId,
        state.myCharacter.id,
        targetActionId,
        cooperationText
      );
      setState((prev) => ({
        ...prev,
        actions: [...prev.actions, action],
      }));
      return action;
    },
    [gameId, state.myCharacter]
  );

  const cancelAction = useCallback(
    async (actionId: string) => {
      await api.cancelAction(gameId, actionId);
      setState((prev) => ({
        ...prev,
        actions: prev.actions.map((a) =>
          a.id === actionId ? { ...a, status: "cancelled" as const } : a
        ),
        pendingAction: prev.pendingAction?.id === actionId ? null : prev.pendingAction,
      }));
    },
    [gameId]
  );

  return {
    ...state,
    loading,
    error,
    refresh,
    submitAction,
    submitCooperation,
    cancelAction,
  };
}
