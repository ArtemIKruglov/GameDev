import { useState, useCallback, useRef, useEffect } from "react";
import { api, ApiError } from "../api/client";
import type { Game } from "../api/types";

type Status = "idle" | "loading" | "success" | "error";

const POLL_INTERVAL = 2000; // 2 seconds
const POLL_TIMEOUT = 300000; // 5 minutes max

export function useCreateGame() {
  const [game, setGame] = useState<Game | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = undefined;
    }
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      stopPolling();
    };
  }, [stopPolling]);

  const createGame = useCallback(
    async (prompt: string) => {
      abortRef.current?.abort();
      stopPolling();
      const controller = new AbortController();
      abortRef.current = controller;

      setStatus("loading");
      setError(null);
      setGame(null);
      setLastPrompt(prompt);

      try {
        // POST returns immediately with status="pending"
        const pendingGame = await api.createGame({ prompt }, controller.signal);

        // Poll until ready/failed
        const startTime = Date.now();
        return await new Promise<Game | null>((resolve) => {
          pollRef.current = setInterval(async () => {
            if (controller.signal.aborted) {
              stopPolling();
              resolve(null);
              return;
            }
            try {
              const updated = await api.getGame(pendingGame.id);
              if (updated.status === "ready") {
                stopPolling();
                setGame(updated);
                setStatus("success");
                resolve(updated);
              } else if (updated.status === "failed") {
                stopPolling();
                setError("generation_failed");
                setStatus("error");
                resolve(null);
              } else if (Date.now() - startTime > POLL_TIMEOUT) {
                stopPolling();
                setError("generation_failed");
                setStatus("error");
                resolve(null);
              }
              // else: still pending, keep polling
            } catch {
              // Network hiccup, keep polling
            }
          }, POLL_INTERVAL);
        });
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return null;
        }
        const message = err instanceof ApiError ? err.errorCode : "unknown";
        setError(message);
        setStatus("error");
        return null;
      }
    },
    [stopPolling],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    stopPolling();
    setGame(null);
    setStatus("idle");
    setError(null);
  }, [stopPolling]);

  return {
    createGame,
    game,
    loading: status === "loading",
    error,
    lastPrompt,
    reset,
  };
}
