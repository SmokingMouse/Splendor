"use client";

import { ActionItem, MatchState } from "../services/api";

const gemStyles: Record<string, string> = {
  diamond: "bg-white text-gray-900 border border-gray-200",
  sapphire: "bg-blue-500 text-white",
  emerald: "bg-emerald-500 text-white",
  ruby: "bg-red-500 text-white",
  onyx: "bg-slate-800 text-white",
  gold: "bg-amber-400 text-slate-900",
};
const cardTone: Record<string, string> = {
  diamond: "from-slate-100/80 via-white/40 to-slate-200/60",
  sapphire: "from-blue-600/40 via-blue-500/20 to-blue-700/40",
  emerald: "from-emerald-600/40 via-emerald-500/20 to-emerald-700/40",
  ruby: "from-red-600/40 via-red-500/20 to-red-700/40",
  onyx: "from-slate-900/60 via-slate-800/30 to-slate-950/60",
  gold: "from-amber-400/40 via-amber-300/20 to-amber-500/40",
};

export function MatchView({
  match,
  actions,
  selectedGems,
  onGemToggle,
  onCardClick,
  onReserveCard,
  onReserveDeck,
}: {
  match: MatchState;
  actions: ActionItem[];
  selectedGems: Record<string, number>;
  onGemToggle: (gem: string) => void;
  onCardClick: (cardId: string) => void;
  onReserveCard: (cardId: string) => void;
  onReserveDeck: (tier: number) => void;
}) {
  const buyableCards = new Set(
    actions
      .filter((action) => action.type === "buy_card" && action.payload?.card_id)
      .map((action) => String(action.payload.card_id))
  );
  const reservableCards = new Set(
    actions
      .filter((action) => action.type === "reserve_card" && action.payload?.card_id)
      .map((action) => String(action.payload.card_id))
  );
  const reservableDecks = new Set(
    actions
      .filter((action) => action.type === "reserve_deck" && action.payload?.tier)
      .map((action) => Number(action.payload.tier))
  );
  const players = match.players ?? [];

  return (
    <section className="mt-6 rounded-3xl border border-slate-800/30 bg-gradient-to-br from-slate-800 via-slate-700 to-slate-600 p-6 text-white shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold tracking-wide">对局桌面</h2>
          <div className="text-xs text-slate-200">
            回合 {match.turn} · 当前行动 {match.current_player_id}
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-200">
          {Object.entries(match.score).map(([player, score]) => (
            <span
              key={player}
              className="rounded-full border border-white/20 bg-white/10 px-3 py-1"
            >
              {player}: {score}
            </span>
          ))}
        </div>
      </div>

      {match.return_tokens && (
        <div className="mt-4 rounded-2xl border border-amber-300/50 bg-amber-300/10 px-4 py-3 text-xs text-amber-100">
          宝石超过 10，请选择要归还的宝石后点击“确认归还”
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_auto]">
        <div className="space-y-5">
          <div className="grid grid-cols-3 gap-3 md:grid-cols-5">
            {match.board_state.nobles.map((noble) => (
              <div
                key={noble.id}
                className="rounded-2xl border border-white/20 bg-white/10 p-3 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">贵族</span>
                  <span className="rounded-full bg-white/20 px-2 py-1 text-[10px]">
                    {noble.points} 分
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(noble.requirement).map(([gem, count]) => (
                    <span
                      key={gem}
                      className={`inline-flex h-5 items-center justify-center rounded-full px-2 text-[10px] ${gemStyles[gem]}`}
                    >
                      {count}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {["3", "2", "1"].map((tier) => (
            <div key={tier} className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-200">
                <span className="font-semibold">等级 {tier}</span>
                <button
                  type="button"
                  className={`rounded-full border px-2 py-1 text-[10px] transition ${
                    reservableDecks.has(Number(tier))
                      ? "border-amber-300/70 bg-amber-300/10 hover:bg-amber-300/20"
                      : "border-white/10 bg-white/10"
                  }`}
                  onClick={() => onReserveDeck(Number(tier))}
                >
                  牌堆剩余 {match.board_state.hidden[tier] ?? 0}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {(match.board_state.tiers[tier] ?? []).map((card, index) => {
                  if (!card) {
                    return (
                      <div
                        key={`empty-${tier}-${index}`}
                        className="rounded-2xl border border-dashed border-white/20 bg-white/5 p-3 text-xs text-slate-300"
                      >
                        空位
                      </div>
                    );
                  }
                  return (
                    <div
                      key={card.id}
                      className={`relative cursor-pointer overflow-hidden rounded-2xl border bg-gradient-to-br p-3 text-xs transition hover:-translate-y-0.5 ${
                        cardTone[card.bonus]
                      } ${
                        buyableCards.has(card.id)
                          ? "border-amber-300/70 shadow-[0_0_12px_rgba(251,191,36,0.35)]"
                          : "border-white/20"
                      }`}
                      onClick={() => onCardClick(card.id)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">开发卡</span>
                        <span className="rounded-full bg-white/20 px-2 py-1 text-[10px]">
                          {card.points} 分
                        </span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <span
                          className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-[10px] ${gemStyles[card.bonus]}`}
                        >
                          {card.bonus.slice(0, 1).toUpperCase()}
                        </span>
                        <div className="text-[10px] text-slate-200">{card.id}</div>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1">
                        {Object.entries(card.cost).map(([gem, count]) => (
                          <span
                            key={gem}
                            className={`inline-flex h-5 items-center justify-center rounded-full px-2 text-[10px] ${gemStyles[gem]}`}
                          >
                            {count}
                          </span>
                        ))}
                      </div>
                      {reservableCards.has(card.id) && (
                        <button
                          type="button"
                          className="mt-3 w-full rounded-lg border border-white/20 bg-white/10 px-2 py-1 text-[10px] text-slate-100 hover:bg-white/20"
                          onClick={(event) => {
                            event.stopPropagation();
                            onReserveCard(card.id);
                          }}
                        >
                          预留
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-4 self-start">
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4 text-xs">
            <div className="font-semibold">玩家状态</div>
            <div className="mt-3 grid gap-3">
              {players.map((player) => (
                <div
                  key={player.id}
                  className={`rounded-xl border px-3 py-2 ${
                    player.id === match.current_player_id
                      ? "border-amber-300/70 bg-amber-300/10"
                      : "border-white/10 bg-white/5"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{player.id}</span>
                    <span className="text-[10px] text-slate-200">
                      {player.type === "ai" ? "AI" : "人类"}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1 text-[10px] text-slate-200">
                    <span>分数 {player.score}</span>
                    <span>卡牌 {player.card_count}</span>
                    <span>预留 {player.reserved_count}</span>
                    <span>贵族 {player.nobles_count}</span>
                  </div>
                  {player.reserved_cards.length > 0 && (
                    <div className="mt-2 grid gap-2">
                      <div className="text-[10px] text-slate-300">已预留</div>
                      <div className="grid gap-2">
                        {player.reserved_cards.map((card) => (
                          <button
                            key={card.id}
                            type="button"
                            className={`flex flex-col items-start gap-1 rounded-lg border px-2 py-2 text-[10px] ${
                              buyableCards.has(card.id)
                                ? "border-amber-300/70 bg-amber-300/10"
                                : "border-white/10 bg-white/5"
                            }`}
                            onClick={() => onCardClick(card.id)}
                          >
                            <div className="flex w-full items-center justify-between">
                              <span>#{card.id}</span>
                              <span>{card.points} 分</span>
                            </div>
                            <div className="flex w-full items-center gap-2">
                              <span
                                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] ${gemStyles[card.bonus]}`}
                              >
                                {card.bonus.slice(0, 1).toUpperCase()}
                              </span>
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(card.cost).map(([gem, count]) => (
                                  <span
                                    key={gem}
                                    className={`inline-flex h-5 items-center justify-center rounded-full px-2 text-[10px] ${gemStyles[gem]}`}
                                  >
                                    {count}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Object.entries(player.gems).map(([gem, count]) => (
                      <button
                        key={gem}
                        type="button"
                        className={`inline-flex h-5 items-center justify-center rounded-full px-2 text-[10px] ${
                          gemStyles[gem]
                        } ${
                          match.return_tokens && player.id === match.current_player_id
                            ? "ring-1 ring-amber-300/70"
                            : ""
                        }`}
                        onClick={() => {
                          if (match.return_tokens && player.id === match.current_player_id) {
                            onGemToggle(gem);
                          }
                        }}
                      >
                        {count}
                      </button>
                    ))}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Object.entries(player.bonuses).map(([gem, count]) => (
                      <span
                        key={gem}
                        className={`inline-flex h-5 items-center justify-center rounded-full px-2 text-[10px] ${gemStyles[gem]}`}
                      >
                        +{count}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4 text-xs">
            <div className="font-semibold">宝石库存</div>
            <div className="mt-3 grid gap-2">
              {Object.entries(match.board_state.bank_gems).map(([gem, count]) => (
                <button
                  key={gem}
                  type="button"
                  className={`flex items-center justify-between rounded-lg px-2 py-1 text-left transition ${
                    selectedGems[gem] ? "bg-white/20" : "hover:bg-white/10"
                  }`}
                  onClick={() => onGemToggle(gem)}
                >
                  <span className={`h-5 w-5 rounded-full ${gemStyles[gem]}`} />
                  <span className="text-slate-200">{gem}</span>
                  <span className="font-semibold">
                    {count}
                    {selectedGems[gem] ? ` · 选${selectedGems[gem]}` : ""}
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-4 text-xs">
            <div className="font-semibold">提示</div>
            <div className="mt-3 space-y-2 text-slate-200">
              <div>点击卡牌购买</div>
              <div>点击宝石选择后确认拿取</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
