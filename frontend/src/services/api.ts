export type AiConfig = {
  id: string;
  name: string;
  description: string;
};

export type MatchState = {
  id: string;
  status: string;
  current_player_id: string;
  turn: number;
  board_state: {
    bank_gems: Record<string, number>;
    tiers: Record<
      string,
      Array<{
        id: string;
        points: number;
        bonus: string;
        cost: Record<string, number>;
        tier: number;
      } | null>
    >;
    hidden: Record<string, number>;
    nobles: Array<{ id: string; points: number; requirement: Record<string, number> }>;
  };
  score: Record<string, number>;
  winner?: string | null;
  players: Array<{
    id: string;
    type: string;
    gems: Record<string, number>;
    score: number;
    card_count: number;
    reserved_cards: Array<{
      id: string;
      points: number;
      bonus: string;
      cost: Record<string, number>;
      tier: number;
    }>;
    reserved_count: number;
    nobles_count: number;
    bonuses: Record<string, number>;
  }>;
  return_tokens: boolean;
};

export type ActionItem = {
  id: string;
  type: string;
  payload: Record<string, unknown>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "请求失败");
  }

  return response.json() as Promise<T>;
}

export async function listAiConfigs(): Promise<AiConfig[]> {
  const data = await request<{ configs: AiConfig[] }>("/ai-configs");
  return data.configs;
}

export async function createMatch(humanName: string, aiConfigId: string) {
  return request<{ id: string; status: string }>("/matches", {
    method: "POST",
    body: JSON.stringify({ human_name: humanName, ai_config_id: aiConfigId }),
  });
}

export async function getMatch(matchId: string): Promise<MatchState> {
  return request<MatchState>(`/matches/${matchId}`);
}

export async function listActions(matchId: string): Promise<ActionItem[]> {
  const data = await request<{ actions: ActionItem[] }>(`/matches/${matchId}/actions`);
  return data.actions;
}

export async function submitAction(
  matchId: string,
  actionId: string,
  payload: Record<string, unknown> = {}
) {
  return request<{ success: boolean; reason?: string; state: MatchState }>(
    `/matches/${matchId}/actions`,
    {
      method: "POST",
      body: JSON.stringify({ action_id: actionId, payload }),
    }
  );
}
