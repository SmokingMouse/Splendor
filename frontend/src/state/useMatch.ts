"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ActionItem,
  MatchState,
  createMatch,
  getMatch,
  listActions,
  listAiConfigs,
  submitAction,
} from "../services/api";

export function useMatch() {
  const [match, setMatch] = useState<MatchState | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [configs, setConfigs] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listAiConfigs()
      .then((items) => setConfigs(items))
      .catch((err) => setError(err.message));
  }, []);

  const refresh = useCallback(async (matchId: string) => {
    const state = await getMatch(matchId);
    const available = await listActions(matchId);
    setMatch(state);
    setActions(available);
  }, []);

  useEffect(() => {
    if (!match?.id) {
      return;
    }
    const timer = setInterval(() => {
      refresh(match.id).catch((err) => setError(err.message));
    }, 2000);
    return () => clearInterval(timer);
  }, [match?.id, refresh]);

  const startMatch = useCallback(
    async (humanName: string, aiConfigId: string) => {
      setLoading(true);
      setError(null);
      try {
        const created = await createMatch(humanName, aiConfigId);
        await refresh(created.id);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [refresh]
  );

  const act = useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}) => {
      if (!match) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await submitAction(match.id, actionId, payload);
        if (!result.success) {
          setError(result.reason ?? "行动失败");
        }
        setMatch(result.state);
        setActions(await listActions(match.id));
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [match]
  );

  return {
    match,
    actions,
    configs,
    error,
    loading,
    startMatch,
    act,
  };
}
