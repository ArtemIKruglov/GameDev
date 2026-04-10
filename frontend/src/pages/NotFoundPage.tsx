import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div style={styles.container}>
      <span style={styles.emoji}>🕹️</span>
      <h1 style={styles.heading}>404 — Страница не найдена</h1>
      <p style={styles.body}>
        Кажется, ты забрёл не туда! Такой страницы не существует.
      </p>
      <Link to="/" style={styles.button}>
        На главную 🏠
      </Link>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center" as const,
    padding: "2rem",
    gap: 16,
  } as React.CSSProperties,
  emoji: { fontSize: "4rem" } as React.CSSProperties,
  heading: {
    fontSize: "1.8rem",
    fontWeight: 700,
    margin: 0,
  } as React.CSSProperties,
  body: {
    fontSize: "1.1rem",
    color: "var(--color-text-muted)",
    maxWidth: 400,
  } as React.CSSProperties,
  button: {
    marginTop: 12,
    padding: "14px 32px",
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#fff",
    background:
      "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    borderRadius: "var(--radius)",
    textDecoration: "none",
    minHeight: 48,
  } as React.CSSProperties,
};
