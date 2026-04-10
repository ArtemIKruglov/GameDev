import { useState, useEffect, useRef } from "react";
import { api } from "../api/client";
import type { Game } from "../api/types";

const POLL_INTERVAL = 2000;

export function useGame(id: string | undefined) {
  const [game, setGame] = useState<Game | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError("No game ID provided");
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const gameData = await api.getGame(id!);
        if (cancelled) return;
        setGame(gameData);

        if (gameData.status === "ready") {
          // Game is ready — fetch HTML
          const htmlData = await api.getGameHTML(id!);
          if (!cancelled) {
            setHtml(htmlData);
            setLoading(false);
          }
        } else if (gameData.status === "pending") {
          // Game still generating — poll until ready
          pollRef.current = setInterval(async () => {
            if (cancelled) return;
            try {
              const updated = await api.getGame(id!);
              if (cancelled) return;
              setGame(updated);
              if (updated.status === "ready") {
                clearInterval(pollRef.current);
                const h = await api.getGameHTML(id!);
                if (!cancelled) {
                  setHtml(h);
                  setLoading(false);
                }
              } else if (updated.status === "failed") {
                clearInterval(pollRef.current);
                if (!cancelled) {
                  setError("Игра не получилась. Попробуй другую идею!");
                  setLoading(false);
                }
              }
            } catch {
              // network hiccup, keep polling
            }
          }, POLL_INTERVAL);
        } else {
          // failed or flagged
          setError("Игра не получилась. Попробуй другую идею!");
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError("Не удалось загрузить игру");
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  return { game, html, loading, error };
}
