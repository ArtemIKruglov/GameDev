import { Link } from "react-router-dom";
import GameGallery from "../components/GameGallery";
import { useGames } from "../hooks/useGames";

export default function GalleryPage() {
  const { games, loading, hasMore, loadMore } = useGames();

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <Link to="/" style={styles.logo}>
          GameSpark
        </Link>
        <h1 style={styles.title}>Game Gallery</h1>
        <Link to="/" style={styles.createLink}>
          Create a Game
        </Link>
      </header>

      <main style={styles.main}>
        <GameGallery
          games={games}
          loading={loading}
          hasMore={hasMore}
          onLoadMore={loadMore}
        />
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
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "1rem 2rem",
    flexWrap: "wrap" as const,
    gap: 12,
  } as React.CSSProperties,

  logo: {
    fontSize: "1.4rem",
    fontWeight: 800,
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    textDecoration: "none",
  } as React.CSSProperties,

  title: {
    fontSize: "1.4rem",
    fontWeight: 700,
    margin: 0,
  } as React.CSSProperties,

  createLink: {
    padding: "10px 24px",
    fontSize: "0.95rem",
    fontWeight: 600,
    color: "#fff",
    background: "linear-gradient(135deg, var(--color-primary), var(--color-accent))",
    borderRadius: "var(--radius)",
    textDecoration: "none",
    minHeight: 48,
    display: "flex",
    alignItems: "center",
  } as React.CSSProperties,

  main: {
    flex: 1,
    padding: "1.5rem 1rem 3rem",
  } as React.CSSProperties,
};
