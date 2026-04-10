import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Game } from "../api/types";

export function useGames(perPage = 20) {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const hasMore = games.length < total;

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listGames(1, perPage);
        if (!cancelled) {
          setGames(data.games);
          setTotal(data.total);
          setPage(1);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load games");
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
  }, [perPage]);

  const loadMore = useCallback(async () => {
    const nextPage = page + 1;
    setLoading(true);
    try {
      const data = await api.listGames(nextPage, perPage);
      setGames((prev) => [...prev, ...data.games]);
      setTotal(data.total);
      setPage(nextPage);
    } catch {
      setError("Failed to load more games");
    } finally {
      setLoading(false);
    }
  }, [page, perPage]);

  return { games, loading, error, hasMore, loadMore };
}
