"use client";

import { ActionItem } from "../services/api";

export function ActionPanel({
  actions,
  onAction,
  disabled,
}: {
  actions: ActionItem[];
  onAction: (id: string) => void;
  disabled: boolean;
}) {
  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">动作选择</h2>
        <span className="text-xs text-slate-500">{actions.length} 个</span>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-2">
        {actions.map((action) => (
          <button
            key={action.id}
            type="button"
            className="min-w-[160px] rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs shadow-sm transition hover:-translate-y-0.5 hover:border-slate-300"
            onClick={() => onAction(action.id)}
            disabled={disabled}
          >
            <div className="font-semibold text-slate-800">{action.type}</div>
            <div className="mt-1 text-[10px] text-slate-500">
              {JSON.stringify(action.payload)}
            </div>
          </button>
        ))}
        {actions.length === 0 && (
          <div className="text-xs text-slate-500">暂无可行动作</div>
        )}
      </div>
    </section>
  );
}
