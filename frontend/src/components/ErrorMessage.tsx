import { Link } from "react-router-dom";

interface ErrorMessageProps {
  type: string;
  message?: string;
  onRetry?: () => void;
  onChangeIdea?: () => void;
}

const MESSAGES: Record<string, { heading: string; body: string }> = {
  generation_failed: {
    heading: "Ой, в игре баг! 🐛",
    body: "Даже у лучших разработчиков бывают баги. Попробуем ещё раз?",
  },
  rate_limited: {
    heading: "Ого, ты создаёшь кучу игр! 🎮",
    body: "Передохни немножко и возвращайся — мы никуда не денемся!",
  },
  content_blocked: {
    heading: "Давай придумаем что-то другое! 🌈",
    body: "Попробуй другую идею — что-нибудь весёлое и доброе!",
  },
  content_filtered: {
    heading: "Давай придумаем что-то другое! 🌈",
    body: "Попробуй другую идею — что-нибудь весёлое и доброе!",
  },
};

const DEFAULT_MESSAGE = {
  heading: "Упс! Что-то пошло не так 🤖",
  body: "Не переживай, даже игровые приставки иногда зависают!",
};

export default function ErrorMessage({
  type,
  message,
  onRetry,
  onChangeIdea,
}: ErrorMessageProps) {
  const msg = MESSAGES[type] || DEFAULT_MESSAGE;

  return (
    <div style={styles.container} role="alert">
      <span style={styles.icon} aria-hidden="true">
        🤖🔧
      </span>
      <h2 style={styles.heading}>{msg.heading}</h2>
      <p style={styles.body}>{message || msg.body}</p>

      <div style={styles.actions}>
        {onRetry && (
          <button onClick={onRetry} style={styles.primaryButton}>
            Попробовать ещё 🔄
          </button>
        )}
        {onChangeIdea && (
          <button onClick={onChangeIdea} style={styles.secondaryButton}>
            Другая идея 💡
          </button>
        )}
        <Link to="/" style={styles.linkButton}>
          На главную
        </Link>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    textAlign: "center" as const,
    padding: "3rem 2rem",
    gap: 16,
    maxWidth: 480,
    margin: "0 auto",
  } as React.CSSProperties,

  icon: {
    fontSize: "3rem",
  } as React.CSSProperties,

  heading: {
    fontSize: "1.5rem",
    fontWeight: 700,
    color: "var(--color-text)",
    margin: 0,
  } as React.CSSProperties,

  body: {
    fontSize: "1.05rem",
    color: "var(--color-text-muted)",
    lineHeight: 1.6,
    margin: 0,
  } as React.CSSProperties,

  actions: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: 12,
    marginTop: 12,
    justifyContent: "center",
    alignItems: "center",
  } as React.CSSProperties,

  primaryButton: {
    padding: "12px 28px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#fff",
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    border: "none",
    borderRadius: "var(--radius)",
    minHeight: 48,
  } as React.CSSProperties,

  secondaryButton: {
    padding: "12px 28px",
    fontSize: "1rem",
    fontWeight: 600,
    color: "var(--color-text)",
    background: "var(--color-bg-card)",
    border: "2px solid var(--color-primary)",
    borderRadius: "var(--radius)",
    minHeight: 48,
  } as React.CSSProperties,

  linkButton: {
    padding: "12px 28px",
    fontSize: "1rem",
    color: "var(--color-text-muted)",
    textDecoration: "none",
    minHeight: 48,
    display: "flex",
    alignItems: "center",
  } as React.CSSProperties,
};
