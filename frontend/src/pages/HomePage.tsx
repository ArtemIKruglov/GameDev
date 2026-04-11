import { useState, useCallback, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import PromptInput from "../components/PromptInput";
import LoadingScreen from "../components/LoadingScreen";
import ErrorMessage from "../components/ErrorMessage";
import GameCard from "../components/GameCard";
import { useCreateGame } from "../hooks/useCreateGame";
import { useGames } from "../hooks/useGames";
import { api } from "../api/client";

const EXAMPLES = [
  "Котик прыгает по крышам и собирает звёздочки 🐱⭐",
  "Космический шутер с неоновыми цветами 🚀💜",
  "Бей кротов, но кроты — это смешные инопланетяне 👾🔨",
  "Робот бежит по платформам и собирает шестерёнки ⚙️🤖",
  "Печатай буквы быстрее, чем они падают! ⌨️💨",
  "Найди пару — мемори с животными 🐻🐼🦊",
];

type View = "input" | "loading" | "error";

export default function HomePage() {
  const navigate = useNavigate();
  const { createGame, error, loading, lastPrompt, reset } = useCreateGame();
  const [view, setView] = useState<View>("input");
  const [promptForInput, setPromptForInput] = useState("");
  const { games: recentGames } = useGames(6);

  useEffect(() => {
    api.trackEvent("page_view", undefined, "home");
  }, []);

  const handleSubmit = useCallback(
    async (prompt: string) => {
      setPromptForInput(prompt);
      setView("loading");
      const game = await createGame(prompt);
      if (game) {
        navigate(`/play/${game.id}`);
      } else {
        setView("error");
      }
    },
    [createGame, navigate],
  );

  const handleCancel = useCallback(() => {
    reset();
    setView("input");
  }, [reset]);

  if (view === "loading" && loading) {
    return (
      <div style={styles.page}>
        <LoadingScreen onCancel={handleCancel} />
      </div>
    );
  }

  if (view === "error" && error) {
    return (
      <div style={styles.page}>
        <ErrorMessage
          type={error}
          onRetry={() => {
            // BUG-3 fix: preserve the prompt on retry
            setView("input");
          }}
          onChangeIdea={() => {
            reset();
            setPromptForInput("");
            setView("input");
          }}
        />
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.logo}>Играйка</h1>
        <nav style={styles.nav}>
          <Link to="/gallery" style={styles.navLink}>Галерея</Link>
          <Link to="/privacy" style={styles.navLink}>Приватность</Link>
        </nav>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>Придумай игру — и вжух! 🎮</h2>
        <p style={styles.subheading}>
          Напиши, во что хочешь поиграть, а Играйка создаст игру для тебя
        </p>

        <PromptInput
          onSubmit={handleSubmit}
          disabled={loading}
          initialValue={promptForInput || lastPrompt}
        />

        <section style={styles.examples}>
          <h3 style={styles.examplesTitle}>Нет идей? Попробуй одну из этих! 👇</h3>
          <div style={styles.examplesGrid}>
            {EXAMPLES.map((example) => (
              <button
                key={example}
                style={styles.exampleCard}
                onClick={() => setPromptForInput(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </section>
      </main>

      {recentGames.length > 0 && (
        <section style={styles.recentSection}>
          <h3 style={styles.recentTitle}>
            Свежие игры от других ребят 🕹️
          </h3>
          <div style={styles.recentGrid}>
            {recentGames.map((game) => (
              <GameCard key={game.id} game={game} />
            ))}
          </div>
          <Link to="/gallery" style={styles.seeAllLink}>
            Все игры →
          </Link>
        </section>
      )}

      <footer style={styles.footer}>
        <p>Сделано для тех, кто мечтает по-крупному ✨</p>
        <Link to="/privacy">Приватность</Link>
      </footer>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column" as const,
  } as React.CSSProperties,

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1rem 2rem",
  } as React.CSSProperties,

  logo: {
    fontSize: "1.8rem",
    fontWeight: 800,
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    margin: 0,
  } as React.CSSProperties,

  nav: {
    display: "flex",
    gap: 20,
  } as React.CSSProperties,

  navLink: {
    color: "var(--color-text-muted)",
    fontSize: "0.95rem",
    textDecoration: "none",
  } as React.CSSProperties,

  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    padding: "3rem 1.5rem 2rem",
    gap: 16,
  } as React.CSSProperties,

  heading: {
    fontSize: "2.4rem",
    fontWeight: 800,
    textAlign: "center" as const,
    margin: 0,
  } as React.CSSProperties,

  subheading: {
    fontSize: "1.1rem",
    color: "var(--color-text-muted)",
    textAlign: "center" as const,
    marginBottom: 16,
  } as React.CSSProperties,

  examples: {
    marginTop: 48,
    width: "100%",
    maxWidth: 800,
  } as React.CSSProperties,

  examplesTitle: {
    fontSize: "1rem",
    color: "var(--color-text-muted)",
    textAlign: "center" as const,
    fontWeight: 500,
    marginBottom: 16,
  } as React.CSSProperties,

  examplesGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: 12,
  } as React.CSSProperties,

  exampleCard: {
    padding: "14px 16px",
    fontSize: "0.9rem",
    color: "var(--color-text)",
    background: "var(--color-bg-card)",
    border: "1px solid transparent",
    borderRadius: "var(--radius)",
    textAlign: "left" as const,
    lineHeight: 1.5,
    transition: "border-color 0.2s, transform 0.15s",
    cursor: "pointer",
    minHeight: 48,
  } as React.CSSProperties,

  recentSection: {
    width: "100%",
    maxWidth: 900,
    margin: "0 auto",
    padding: "2rem 1rem",
  } as React.CSSProperties,

  recentTitle: {
    fontSize: "1.3rem",
    fontWeight: 700,
    textAlign: "center" as const,
    marginBottom: 20,
  } as React.CSSProperties,

  recentGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
    gap: 16,
  } as React.CSSProperties,

  seeAllLink: {
    display: "block",
    textAlign: "center" as const,
    marginTop: 20,
    color: "var(--color-primary)",
    fontSize: "1rem",
    fontWeight: 600,
  } as React.CSSProperties,

  footer: {
    padding: "2rem",
    textAlign: "center" as const,
    fontSize: "0.85rem",
    color: "var(--color-text-muted)",
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: 8,
  } as React.CSSProperties,
};
