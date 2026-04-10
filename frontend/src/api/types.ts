export interface Game {
  id: string;
  prompt: string;
  status: "pending" | "ready" | "failed" | "flagged";
  play_url: string;
  created_at: string;
  generation_time_ms: number | null;
  parent_game_id: string | null;
}

export interface GameListResponse {
  games: Game[];
  total: number;
  page: number;
  per_page: number;
}

export interface GameCreateRequest {
  prompt: string;
}

export interface GameRefineRequest {
  modification: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  retry_after_seconds?: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  database: string;
  version: string;
}
