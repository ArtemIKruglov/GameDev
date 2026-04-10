import type { Game, GameCreateRequest, GameListResponse } from "./types";

const API_BASE = "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message: string,
    public retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({
      detail: { error: "unknown", message: "An unexpected error occurred" },
    }));
    // FastAPI wraps HTTPException bodies in "detail"
    const detail = body.detail || body;
    throw new ApiError(
      response.status,
      detail.error || "unknown",
      detail.message || "Something went wrong",
      detail.retry_after_seconds,
    );
  }

  return response.json();
}

export const api = {
  createGame(data: GameCreateRequest, signal?: AbortSignal): Promise<Game> {
    return request<Game>("/games", {
      method: "POST",
      body: JSON.stringify(data),
      signal,
    });
  },

  getGame(id: string): Promise<Game> {
    return request<Game>(`/games/${id}`);
  },

  getGameHTML(id: string): Promise<string> {
    return fetch(`${API_BASE}/games/${id}/html`, { credentials: "include" }).then(
      (r) => {
        if (!r.ok) throw new Error("Failed to load game");
        return r.text();
      },
    );
  },

  listGames(
    page = 1,
    perPage = 20,
    mine = false,
  ): Promise<GameListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      ...(mine ? { mine: "true" } : {}),
    });
    return request<GameListResponse>(`/games?${params}`);
  },

  flagGame(id: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/games/${id}/flag`, {
      method: "POST",
    });
  },

  refineGame(id: string, modification: string): Promise<Game> {
    return request<Game>(`/games/${id}/refine`, {
      method: "POST",
      body: JSON.stringify({ modification }),
    });
  },
};

export { ApiError };
