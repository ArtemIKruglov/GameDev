import { useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import GamePlayer from "../components/GamePlayer";
import LoadingScreen from "../components/LoadingScreen";
import ErrorMessage from "../components/ErrorMessage";
import { useGame } from "../hooks/useGame";
import { api, ApiError } from "../api/client";

export default function PlayPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { game, html, loading, error } = useGame(id);
  const [copied, setCopied] = useState(false);
  const [showRefine, setShowRefine] = useState(false);
  const [modification, setModification] = useState("");
  const [refining, setRefining] = useState(false);
  const [refineError, setRefineError] = useState<string | null>(null);

  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
    }
  }, []);

  const handleRefine = useCallback(async () => {
    if (!id || !modification.trim()) return;
    setRefining(true);
    setRefineError(null);
    try {
      const newGame = await api.refineGame(id, modification.trim());
      navigate(`/play/${newGame.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setRefineError(err.message);
      } else {
        setRefineError("Refinement failed. Please try again!");
      }
    } finally {
      setRefining(false);
    }
  }, [id, modification, navigate]);

  if (loading) {
    return (
      <div style={styles.page}>
        <LoadingScreen />
      </div>
    );
  }

  if (error || !game || !html) {
    return (
      <div style={styles.page}>
        <ErrorMessage
          type="generation_failed"
          message={error || "Game not found"}
          onRetry={() => navigate(0)}
          onChangeIdea={() => navigate("/")}
        />
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <Link to="/" style={styles.logo}>
          GameSpark
        </Link>
      </header>

      <main style={styles.main}>
        {game.parent_game_id && (
          <Link to={`/play/${game.parent_game_id}`} style={styles.backLink}>
            Back to original
          </Link>
        )}

        {game.prompt && (
          <p style={styles.prompt}>{game.prompt}</p>
        )}

        <GamePlayer html={html} />

        <div style={styles.actions}>
          <button onClick={handleShare} style={styles.actionButton}>
            {copied ? "Copied!" : "Share"}
          </button>
          <button
            onClick={() => setShowRefine((v) => !v)}
            style={styles.actionButton}
          >
            Change Something
          </button>
          <button onClick={() => navigate("/")} style={styles.actionButton}>
            New Game
          </button>
        </div>

        {showRefine && (
          <div style={styles.refineSection}>
            <input
              type="text"
              value={modification}
              onChange={(e) => setModification(e.target.value)}
              placeholder="e.g. make the character move faster"
              style={styles.refineInput}
              maxLength={500}
              disabled={refining}
            />
            <button
              onClick={handleRefine}
              disabled={refining || modification.trim().length < 3}
              style={{
                ...styles.refineButton,
                opacity: refining || modification.trim().length < 3 ? 0.5 : 1,
              }}
            >
              {refining ? "Updating..." : "Update My Game"}
            </button>
            {refineError && (
              <p style={styles.refineError}>{refineError}</p>
            )}
          </div>
        )}
      </main>
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
    padding: "1rem 2rem",
  } as React.CSSProperties,

  logo: {
    fontSize: "1.4rem",
    fontWeight: 800,
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    textDecoration: "none",
  } as React.CSSProperties,

  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    padding: "1rem 1.5rem 2rem",
    gap: 20,
  } as React.CSSProperties,

  prompt: {
    fontSize: "1rem",
    color: "var(--color-text-muted)",
    textAlign: "center" as const,
    maxWidth: 600,
    margin: 0,
  } as React.CSSProperties,

  actions: {
    display: "flex",
    gap: 12,
    flexWrap: "wrap" as const,
    justifyContent: "center",
  } as React.CSSProperties,

  actionButton: {
    padding: "12px 28px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "var(--color-text)",
    background: "var(--color-bg-card)",
    border: "2px solid var(--color-primary)",
    borderRadius: "var(--radius)",
    minHeight: 48,
    transition: "all 0.2s",
  } as React.CSSProperties,

  backLink: {
    fontSize: "0.9rem",
    color: "var(--color-primary)",
    textDecoration: "none",
  } as React.CSSProperties,

  refineSection: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    gap: 12,
    width: "100%",
    maxWidth: 500,
  } as React.CSSProperties,

  refineInput: {
    width: "100%",
    padding: "12px 16px",
    fontSize: "1rem",
    border: "2px solid var(--color-primary)",
    borderRadius: "var(--radius)",
    background: "var(--color-bg-card)",
    color: "var(--color-text)",
    outline: "none",
  } as React.CSSProperties,

  refineButton: {
    padding: "12px 28px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#fff",
    background: "var(--color-primary)",
    border: "none",
    borderRadius: "var(--radius)",
    cursor: "pointer",
    minHeight: 48,
    transition: "all 0.2s",
  } as React.CSSProperties,

  refineError: {
    color: "#e74c3c",
    fontSize: "0.9rem",
    margin: 0,
  } as React.CSSProperties,
};
