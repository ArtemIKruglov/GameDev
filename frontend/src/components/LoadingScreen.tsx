import { useState, useEffect, useMemo } from "react";

const PHASES = [
  { text: "Reading your idea...", endSec: 5 },
  { text: "Designing your game world...", endSec: 15 },
  { text: "Adding the fun parts...", endSec: 25 },
  { text: "Polishing and testing...", endSec: Infinity },
];

const FUN_FACTS = [
  "The first video game was made in 1958!",
  "Pac-Man was inspired by a pizza with one slice missing.",
  "Mario was originally called Jumpman!",
  "The Game Boy sold over 118 million units!",
  "Minecraft was created in just 6 days!",
];

interface LoadingScreenProps {
  onCancel?: () => void;
}

export default function LoadingScreen({ onCancel }: LoadingScreenProps) {
  const [elapsed, setElapsed] = useState(0);
  const [factIndex, setFactIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setFactIndex((i) => (i + 1) % FUN_FACTS.length);
    }, 7000);
    return () => clearInterval(timer);
  }, []);

  const phase = useMemo(() => {
    for (const p of PHASES) {
      if (elapsed < p.endSec) return p;
    }
    return PHASES[PHASES.length - 1];
  }, [elapsed]);

  // Non-linear progress: fast start, slows down, never reaches 100%
  const progress = Math.min(95, 60 * (1 - Math.exp(-elapsed / 15)) + elapsed * 0.3);

  const showCancel = elapsed >= 10;

  return (
    <div style={styles.container}>
      <div style={styles.spinner} aria-hidden="true" />

      <p style={styles.phaseText}>{phase.text}</p>

      <div style={styles.progressTrack}>
        <div
          style={{
            ...styles.progressBar,
            width: `${progress}%`,
          }}
        />
      </div>

      <p style={styles.funFact}>{FUN_FACTS[factIndex]}</p>

      {showCancel && onCancel && (
        <button onClick={onCancel} style={styles.cancelButton}>
          Cancel
        </button>
      )}

    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    padding: "3rem 1.5rem",
    minHeight: 400,
    gap: 24,
    textAlign: "center" as const,
  } as React.CSSProperties,

  spinner: {
    width: 56,
    height: 56,
    border: "4px solid var(--color-bg-card)",
    borderTopColor: "var(--color-accent)",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  } as React.CSSProperties,

  phaseText: {
    fontSize: "1.3rem",
    fontWeight: 600,
    color: "var(--color-text)",
  } as React.CSSProperties,

  progressTrack: {
    width: "100%",
    maxWidth: 400,
    height: 8,
    borderRadius: 4,
    background: "var(--color-bg-card)",
    overflow: "hidden" as const,
  } as React.CSSProperties,

  progressBar: {
    height: "100%",
    borderRadius: 4,
    background: "linear-gradient(90deg, var(--color-primary), var(--color-accent))",
    transition: "width 1s ease-out",
  } as React.CSSProperties,

  funFact: {
    fontSize: "0.95rem",
    color: "var(--color-text-muted)",
    fontStyle: "italic" as const,
    animation: "pulse 7s ease-in-out infinite",
    maxWidth: 360,
  } as React.CSSProperties,

  cancelButton: {
    padding: "10px 28px",
    fontSize: "1rem",
    color: "var(--color-text-muted)",
    background: "transparent",
    border: "1px solid var(--color-text-muted)",
    borderRadius: "var(--radius)",
    transition: "all 0.2s",
    minHeight: 48,
  } as React.CSSProperties,
};
