import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import PromptInput from "../components/PromptInput";
import LoadingScreen from "../components/LoadingScreen";
import ErrorMessage from "../components/ErrorMessage";
import { useCreateGame } from "../hooks/useCreateGame";

const EXAMPLES = [
  "A game where a cat jumps between rooftops collecting stars",
  "A space invaders clone with neon colors",
  "A whack-a-mole game with funny aliens",
  "A platformer where a robot collects gears",
  "A typing speed game with falling letters",
  "A memory card matching game with animals",
];

type View = "input" | "loading" | "error";

export default function HomePage() {
  const navigate = useNavigate();
  const { createGame, error, loading, reset } = useCreateGame();
  const [view, setView] = useState<View>("input");

  const handleSubmit = useCallback(
    async (prompt: string) => {
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
          onRetry={() => setView("input")}
          onChangeIdea={() => {
            reset();
            setView("input");
          }}
        />
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.logo}>GameSpark</h1>
        <nav style={styles.nav}>
          <Link to="/gallery" style={styles.navLink}>Gallery</Link>
          <Link to="/privacy" style={styles.navLink}>Privacy</Link>
        </nav>
      </header>

      <main style={styles.main}>
        <h2 style={styles.heading}>What game do you want to make?</h2>
        <p style={styles.subheading}>
          Describe your dream game and AI will build it in seconds
        </p>

        <PromptInput onSubmit={handleSubmit} disabled={loading} />

        <section style={styles.examples}>
          <h3 style={styles.examplesTitle}>Need ideas? Try one of these:</h3>
          <div style={styles.examplesGrid}>
            {EXAMPLES.map((example) => (
              <button
                key={example}
                style={styles.exampleCard}
                onClick={() => {
                  if (example.trim().length >= 10) handleSubmit(example);
                }}
              >
                {example}
              </button>
            ))}
          </div>
        </section>
      </main>

      <footer style={styles.footer}>
        <p>Made for kids who dream big</p>
        <Link to="/privacy">Privacy</Link>
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
