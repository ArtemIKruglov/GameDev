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

// Pick emoji + gradient based on prompt keywords
const THEME_MAP: [RegExp, string, string][] = [
  [/кот|cat|🐱/i, "🐱", "linear-gradient(135deg, #ff6b9d, #c44dff)"],
  [/космос|space|ракет|🚀/i, "🚀", "linear-gradient(135deg, #0a0e27, #1a1a5e)"],
  [/змей|snake/i, "🐍", "linear-gradient(135deg, #00c853, #1b5e20)"],
  [/гонк|racing|speed|пингвин/i, "🏎️", "linear-gradient(135deg, #ff6d00, #ff9100)"],
  [/волк|wolf|яйц/i, "🐺", "linear-gradient(135deg, #5d4037, #8d6e63)"],
  [/тетрис|tetris|блок/i, "🧱", "linear-gradient(135deg, #e91e63, #9c27b0)"],
  [/мемори|memory|пар[уы]/i, "🧠", "linear-gradient(135deg, #00bcd4, #009688)"],
  [/лабиринт|maze|3d/i, "🏰", "linear-gradient(135deg, #37474f, #546e7a)"],
  [/шутер|shoot|стрел|👾/i, "👾", "linear-gradient(135deg, #1a0033, #6c2dc7)"],
  [/платформ|прыг|jump/i, "🦘", "linear-gradient(135deg, #2196f3, #00e5ff)"],
  [/букв|letter|печат|typing/i, "⌨️", "linear-gradient(135deg, #00c9ff, #92fe9d)"],
  [/крот|mole|бей/i, "🔨", "linear-gradient(135deg, #ff5722, #ff9800)"],
  [/пазл|puzzle|головоломк/i, "🧩", "linear-gradient(135deg, #7c4dff, #448aff)"],
  [/мяч|ball|bounce/i, "⚽", "linear-gradient(135deg, #4caf50, #8bc34a)"],
  [/друг|friend|чат/i, "💬", "linear-gradient(135deg, #e040fb, #7c4dff)"],
  [/counter|strike|cs/i, "🎯", "linear-gradient(135deg, #263238, #455a64)"],
];

const DEFAULT_EMOJI = "🎮";
const DEFAULT_GRADIENT = "linear-gradient(135deg, #6c5ce7, #00cec9)";

function getTheme(prompt: string): [string, string] {
  // First check for emoji already in the prompt
  const emojiMatch = prompt.match(
    /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/u,
  );

  for (const [pattern, emoji, gradient] of THEME_MAP) {
    if (pattern.test(prompt)) {
      return [emojiMatch?.[0] || emoji, gradient];
    }
  }
  return [emojiMatch?.[0] || DEFAULT_EMOJI, DEFAULT_GRADIENT];
}

// Deterministic "random" from string hash — for star positions
function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

export default function GameCard({ game }: GameCardProps) {
  const [emoji, gradient] = getTheme(game.prompt);
  const hash = hashCode(game.id);

  // Generate decorative dots
  const dots = Array.from({ length: 5 }, (_, i) => ({
    left: ((hash * (i + 1) * 17) % 80) + 10,
    top: ((hash * (i + 1) * 31) % 60) + 10,
    size: ((hash * (i + 1)) % 3) + 2,
    opacity: 0.15 + ((hash * (i + 1)) % 20) / 100,
  }));

  return (
    <div style={styles.card}>
      {/* Preview banner */}
      <div style={{ ...styles.preview, background: gradient }}>
        <span style={styles.previewEmoji}>{emoji}</span>
        {dots.map((dot, i) => (
          <span
            key={i}
            style={{
              position: "absolute" as const,
              left: `${dot.left}%`,
              top: `${dot.top}%`,
              width: dot.size * 2,
              height: dot.size * 2,
              borderRadius: "50%",
              background: "rgba(255,255,255," + dot.opacity + ")",
            }}
          />
        ))}
      </div>

      <div style={styles.body}>
        <p style={styles.prompt}>{truncate(game.prompt, 70)}</p>
        <div style={styles.footer}>
          <span style={styles.time}>{timeAgo(game.created_at)}</span>
          <Link to={`/play/${game.id}`} style={styles.playButton}>
            Играть ▶
          </Link>
        </div>
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: "var(--color-bg-card)",
    borderRadius: "var(--radius-lg)",
    overflow: "hidden" as const,
    boxShadow: "var(--shadow)",
    transition: "transform 0.2s, box-shadow 0.2s",
    cursor: "default",
    display: "flex",
    flexDirection: "column" as const,
  } as React.CSSProperties,

  preview: {
    position: "relative" as const,
    height: 120,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden" as const,
  } as React.CSSProperties,

  previewEmoji: {
    fontSize: "3.5rem",
    filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.3))",
    zIndex: 1,
  } as React.CSSProperties,

  body: {
    padding: "14px 16px 16px",
    display: "flex",
    flexDirection: "column" as const,
    gap: 10,
    flex: 1,
  } as React.CSSProperties,

  prompt: {
    fontSize: "0.92rem",
    color: "var(--color-text)",
    lineHeight: 1.5,
    flex: 1,
    margin: 0,
  } as React.CSSProperties,

  footer: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  } as React.CSSProperties,

  time: {
    fontSize: "0.75rem",
    color: "var(--color-text-muted)",
  } as React.CSSProperties,

  playButton: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: "8px 20px",
    fontSize: "0.9rem",
    fontWeight: 700,
    color: "#fff",
    background:
      "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    borderRadius: 24,
    textDecoration: "none",
    minHeight: 36,
    boxShadow: "0 2px 8px rgba(108,92,231,0.3)",
  } as React.CSSProperties,
};
