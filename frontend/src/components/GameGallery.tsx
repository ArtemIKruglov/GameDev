import type { Game } from "../api/types";
import GameCard from "./GameCard";

interface GameGalleryProps {
  games: Game[];
  loading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export default function GameGallery({
  games,
  loading,
  hasMore,
  onLoadMore,
}: GameGalleryProps) {
  if (!loading && games.length === 0) {
    return (
      <div style={styles.empty}>
        <p style={styles.emptyText}>No games yet. Be the first to create one!</p>
      </div>
    );
  }

  return (
    <div>
      <div style={styles.grid}>
        {games.map((game) => (
          <GameCard key={game.id} game={game} />
        ))}
        {loading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={`skeleton-${i}`} style={styles.skeleton} />
          ))}
      </div>

      {hasMore && !loading && (
        <div style={styles.loadMoreWrapper}>
          <button onClick={onLoadMore} style={styles.loadMoreButton}>
            Load More
          </button>
        </div>
      )}
    </div>
  );
}

const styles = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: 20,
    padding: "0 1rem",
  } as React.CSSProperties,

  empty: {
    textAlign: "center" as const,
    padding: "4rem 2rem",
  } as React.CSSProperties,

  emptyText: {
    fontSize: "1.2rem",
    color: "var(--color-text-muted)",
  } as React.CSSProperties,

  skeleton: {
    background: "var(--color-bg-card)",
    borderRadius: "var(--radius)",
    height: 160,
    animation: "pulse 1.5s ease-in-out infinite",
  } as React.CSSProperties,

  loadMoreWrapper: {
    display: "flex",
    justifyContent: "center",
    marginTop: 32,
  } as React.CSSProperties,

  loadMoreButton: {
    padding: "12px 32px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "var(--color-text)",
    background: "var(--color-bg-card)",
    border: "2px solid var(--color-primary)",
    borderRadius: "var(--radius)",
    minHeight: 48,
    transition: "all 0.2s",
  } as React.CSSProperties,
};
