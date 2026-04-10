import { useState, useCallback, useRef, useEffect } from "react";
import { api, ApiError } from "../api/client";
import type { Game } from "../api/types";

type Status = "idle" | "loading" | "success" | "error";

export function useCreateGame() {
  const [game, setGame] = useState<Game | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const createGame = useCallback(async (prompt: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setError(null);
    setGame(null);
    try {
      const result = await api.createGame({ prompt }, controller.signal);
      setGame(result);
      setStatus("success");
      return result;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return null;
      }
      const message =
        err instanceof ApiError ? err.errorCode : "unknown";
      setError(message);
      setStatus("error");
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setGame(null);
    setStatus("idle");
    setError(null);
  }, []);

  return {
    createGame,
    game,
    loading: status === "loading",
    error,
    reset,
  };
}
