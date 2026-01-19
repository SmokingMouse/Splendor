"use client";

import { MatchState } from "../services/api";

export function ResultBanner({ match }: { match: MatchState }) {
  if (match.status != "finished") {
    return null;
  }
  return (
    <div className="mt-6 rounded-2xl border border-emerald-300 bg-emerald-50 px-6 py-4 text-emerald-700">
      对局结束，胜者: {match.winner ?? "未知"}
    </div>
  );
}
