import { Link } from "react-router-dom";
import type { Game } from "../api/types";

interface GameCardProps {
  game: Game;
}

function timeAgo(dateString: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(dateString).getTime()) / 1000,
  );
  if (seconds < 60) return "только что";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.floor(hours / 24);
  return `${days} дн назад`;
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

export default function GameCard({ game }: GameCardProps) {
  return (
    <div style={styles.card}>
      <p style={styles.prompt}>{truncate(game.prompt, 80)}</p>
      <span style={styles.time}>{timeAgo(game.created_at)}</span>
      <Link to={`/play/${game.id}`} style={styles.playButton}>
        Играть 🎮
      </Link>
    </div>
  );
}

const styles = {
  card: {
    background: "var(--color-bg-card)",
    borderRadius: "var(--radius)",
    padding: "20px",
    display: "flex",
    flexDirection: "column" as const,
    gap: 12,
    boxShadow: "var(--shadow)",
    transition: "transform 0.2s, box-shadow 0.2s",
    cursor: "default",
  } as React.CSSProperties,

  prompt: {
    fontSize: "1rem",
    color: "var(--color-text)",
    lineHeight: 1.5,
    flex: 1,
    margin: 0,
  } as React.CSSProperties,

  time: {
    fontSize: "0.8rem",
    color: "var(--color-text-muted)",
  } as React.CSSProperties,

  playButton: {
    display: "inline-block",
    padding: "10px 24px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#fff",
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    borderRadius: "var(--radius)",
    textAlign: "center" as const,
    textDecoration: "none",
    minHeight: 48,
    lineHeight: "28px",
  } as React.CSSProperties,
};
