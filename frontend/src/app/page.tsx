"use client";

import React from "react";
import { MatchView } from "../components/MatchView";
import { ResultBanner } from "../components/ResultBanner";
import { useMatch } from "../state/useMatch";

export default function Home() {
  const { match, actions, configs, error, loading, startMatch, act } = useMatch();
  const [selectedGems, setSelectedGems] = React.useState<Record<string, number>>(
    {}
  );
  const [uiError, setUiError] = React.useState<string | null>(null);

  const normalize = (input: Record<string, number>) =>
    JSON.stringify(
      Object.keys(input)
        .sort()
        .reduce<Record<string, number>>((acc, key) => {
          const value = input[key];
          if (value > 0) {
            acc[key] = value;
          }
          return acc;
        }, {})
    );

  const findTakeGemsAction = (selection: Record<string, number>) => {
    const target = normalize(selection);
    return actions.find(
      (action) =>
        action.type === "take_gems" &&
        normalize(action.payload?.gems ?? {}) === target
    )?.id;
  };

  const findReturnGemsAction = (selection: Record<string, number>) => {
    const target = normalize(selection);
    return actions.find(
      (action) =>
        action.type === "return_gems" &&
        normalize(action.payload?.gems ?? {}) === target
    )?.id;
  };

  const onGemToggle = (gem: string) => {
    setUiError(null);
    setSelectedGems((prev) => {
      const total = Object.values(prev).reduce((sum, v) => sum + v, 0);
      const current = prev[gem] ?? 0;
      const bank = match?.board_state.bank_gems ?? {};
      const currentPlayer = match?.players?.find(
        (player) => player.id === match?.current_player_id
      );
      const playerGems = currentPlayer?.gems ?? {};
      const returnMode = match?.return_tokens ?? false;
      const requiredReturn = Math.max(
        0,
        Object.values(playerGems).reduce((sum, v) => sum + v, 0) - 10
      );

      if (returnMode) {
        if ((playerGems[gem] ?? 0) <= 0) {
          return prev;
        }
        const owned = playerGems[gem] ?? 0;
        const total = Object.values(prev).reduce((sum, v) => sum + v, 0);
        if (current < owned && total < requiredReturn) {
          return { ...prev, [gem]: current + 1 };
        }
        if (current > 0) {
          return { ...prev, [gem]: current - 1 };
        }
        return prev;
      }

      if ((bank[gem] ?? 0) <= 0) {
        return prev;
      }
      const hasDouble = Object.values(prev).some((value) => value >= 2);
      let nextValue = current;
      if (current === 0) {
        if (hasDouble || total >= 3) {
          return prev;
        }
        nextValue = 1;
      } else if (current === 1) {
        if (total > 1 || (bank[gem] ?? 0) < 4) {
          return prev;
        }
        nextValue = 2;
      } else {
        nextValue = 0;
      }
      return { ...prev, [gem]: nextValue };
    });
  };

  const onCardClick = (cardId: string) => {
    setUiError(null);
    const action = actions.find(
      (item) => item.type === "buy_card" && item.payload?.card_id === cardId
    );
    if (!action) {
      setUiError("当前卡牌不可购买");
      return;
    }
    act(action.id);
    setSelectedGems({});
  };

  const onReserveCard = (cardId: string) => {
    setUiError(null);
    const action = actions.find(
      (item) => item.type === "reserve_card" && item.payload?.card_id === cardId
    );
    if (!action) {
      setUiError("当前卡牌不可预留");
      return;
    }
    act(action.id);
  };

  const onReserveDeck = (tier: number) => {
    setUiError(null);
    const action = actions.find(
      (item) => item.type === "reserve_deck" && item.payload?.tier === tier
    );
    if (!action) {
      setUiError("当前牌堆不可预留");
      return;
    }
    act(action.id);
  };

  const takeActionId = findTakeGemsAction(selectedGems);
  const returnActionId = findReturnGemsAction(selectedGems);
  const currentPlayer = match?.players?.find(
    (player) => player.id === match?.current_player_id
  );
  const requiredReturn = currentPlayer
    ? Math.max(
        0,
        Object.values(currentPlayer.gems).reduce((sum, v) => sum + v, 0) - 10
      )
    : 0;
  const selectedSummary = Object.entries(selectedGems).filter(
    ([, count]) => count > 0
  );
  const isSelectionEmpty = selectedSummary.length == 0;

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 px-6 py-10 text-white">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-bold">Splendor 人机对战</h1>
        <p className="mt-2 text-sm text-slate-200">
          通过 Web 界面完成创建对局、行动与胜负查看。
        </p>

        {!match && (
          <section className="mt-6 rounded-3xl border border-white/10 bg-white/10 p-6 shadow-lg backdrop-blur">
            <h2 className="text-xl font-semibold">创建对局</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
              <input
                className="rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm text-white placeholder:text-slate-300"
                placeholder="玩家名称"
                defaultValue="玩家"
                id="human-name"
              />
              <select
                className="rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm text-white"
                id="ai-config"
              >
                {configs.map((config) => (
                  <option key={config.id} value={config.id}>
                    {config.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="rounded-lg bg-amber-400 px-5 py-2 text-sm font-semibold text-slate-900"
                disabled={loading}
                onClick={() => {
                  const nameInput = document.getElementById(
                    "human-name"
                  ) as HTMLInputElement | null;
                  const select = document.getElementById(
                    "ai-config"
                  ) as HTMLSelectElement | null;
                  startMatch(nameInput?.value ?? "玩家", select?.value ?? "default");
                }}
              >
                开始对局
              </button>
            </div>
          </section>
        )}

        {match && (
          <>
            <MatchView
              match={match}
              actions={actions}
              selectedGems={selectedGems}
              onGemToggle={onGemToggle}
              onCardClick={onCardClick}
              onReserveCard={onReserveCard}
              onReserveDeck={onReserveDeck}
            />
            <section className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-white/10 p-4">
              <div className="text-sm text-slate-200">
                {match?.return_tokens
                  ? `需要归还 ${requiredReturn} 枚`
                  : "已选宝石:"}
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                {selectedSummary.map(([gem, count]) => (
                  <span
                    key={gem}
                    className="rounded-full border border-white/20 bg-white/10 px-3 py-1"
                  >
                    {gem} x{count}
                  </span>
                ))}
                {isSelectionEmpty && (
                  <span className="text-slate-400">未选择</span>
                )}
              </div>
              <button
                type="button"
                className="ml-auto rounded-lg bg-amber-400 px-4 py-2 text-xs font-semibold text-slate-900 disabled:opacity-50"
                disabled={
                  loading ||
                  (match?.return_tokens
                    ? requiredReturn == 0 || selectedSummary.length == 0
                    : !takeActionId)
                }
                onClick={() => {
                  if (match?.return_tokens) {
                    const payload = { gems: selectedGems };
                    act(returnActionId ?? "return_gems", payload);
                    setSelectedGems({});
                    return;
                  }
                  if (takeActionId) {
                    act(takeActionId);
                    setSelectedGems({});
                  }
                }}
              >
                {match?.return_tokens ? "确认归还" : "确认拿宝石"}
              </button>
            </section>
            <ResultBanner match={match} />
          </>
        )}

        {(error || uiError) && (
          <div className="mt-4 text-sm text-red-300">{error ?? uiError}</div>
        )}
      </div>
    </main>
  );
}
