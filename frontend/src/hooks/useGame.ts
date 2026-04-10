import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Game } from "../api/types";

export function useGame(id: string | undefined) {
  const [game, setGame] = useState<Game | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        const [gameData, htmlData] = await Promise.all([
          api.getGame(id!),
          api.getGameHTML(id!),
        ]);
        if (!cancelled) {
          setGame(gameData);
          setHtml(htmlData);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load game");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [id]);

  return { game, html, loading, error };
}
