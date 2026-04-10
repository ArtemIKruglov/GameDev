import { useState, useEffect, useRef, useCallback, useMemo } from "react";

interface GamePlayerProps {
  html: string;
  onError?: () => void;
  onLoad?: () => void;
}

type PlayerState = "loading" | "playing" | "error";

const ERROR_SCRIPT = `<script>
window.onerror = function(msg) { parent.postMessage({ type: 'game-error', message: String(msg) }, '*'); };
setTimeout(() => parent.postMessage({ type: 'game-ok' }, '*'), 2000);
</script>`;

const HEALTH_TIMEOUT_MS = 5000;

export default function GamePlayer({ html, onError, onLoad }: GamePlayerProps) {
  const [state, setState] = useState<PlayerState>("loading");
  const [fullscreen, setFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const injectedHtml = useMemo(() => {
    const headClose = html.indexOf("</head>");
    if (headClose !== -1) {
      return html.slice(0, headClose) + ERROR_SCRIPT + html.slice(headClose);
    }
    return ERROR_SCRIPT + html;
  }, [html]);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      // Validate message structure: must be an object with a string `type` field
      const data = event.data;
      if (typeof data !== "object" || data === null || typeof data.type !== "string") {
        return;
      }

      if (data.type === "game-ok") {
        setState("playing");
        onLoad?.();
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
      } else if (data.type === "game-error") {
        setState("error");
        onError?.();
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
      }
    }

    window.addEventListener("message", handleMessage);

    timeoutRef.current = setTimeout(() => {
      setState((prev) => {
        if (prev === "loading") {
          onError?.();
          return "error";
        }
        return prev;
      });
    }, HEALTH_TIMEOUT_MS);

    return () => {
      window.removeEventListener("message", handleMessage);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [html, onError, onLoad]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement && containerRef.current) {
      containerRef.current.requestFullscreen().catch(() => {});
      setFullscreen(true);
    } else if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
      setFullscreen(false);
    }
  }, []);

  useEffect(() => {
    function onFsChange() {
      setFullscreen(!!document.fullscreenElement);
    }
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  return (
    <div ref={containerRef} style={styles.container}>
      {state === "loading" && (
        <div style={styles.overlay}>
          <div style={styles.spinner} />
          <p>Загружаем игру... 🎮</p>
        </div>
      )}

      {state === "error" && (
        <div style={styles.overlay}>
          <p style={styles.errorText}>
            Игра чуть-чуть сглючила! Попробуй обновить 🔄
          </p>
        </div>
      )}

      <iframe
        srcDoc={injectedHtml}
        sandbox="allow-scripts"
        title="Game"
        style={{
          ...styles.iframe,
          opacity: state === "playing" ? 1 : 0.15,
        }}
      />

      <button
        onClick={toggleFullscreen}
        style={styles.fullscreenButton}
        aria-label={fullscreen ? "Exit fullscreen" : "Enter fullscreen"}
      >
        {fullscreen ? "Выйти" : "На весь экран"}
      </button>

    </div>
  );
}

const styles = {
  container: {
    position: "relative" as const,
    width: "100%",
    maxWidth: 800,
    aspectRatio: "16 / 10",
    margin: "0 auto",
    background: "var(--color-bg-card)",
    borderRadius: "var(--radius-lg)",
    overflow: "hidden" as const,
    boxShadow: "var(--shadow)",
  } as React.CSSProperties,

  iframe: {
    width: "100%",
    height: "100%",
    border: "none",
    transition: "opacity 0.3s",
  } as React.CSSProperties,

  overlay: {
    position: "absolute" as const,
    inset: 0,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    zIndex: 2,
    color: "var(--color-text)",
    fontSize: "1.1rem",
  } as React.CSSProperties,

  spinner: {
    width: 40,
    height: 40,
    border: "3px solid var(--color-bg-input)",
    borderTopColor: "var(--color-accent)",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  } as React.CSSProperties,

  errorText: {
    color: "var(--color-error)",
    fontWeight: 600,
    padding: "0 2rem",
    textAlign: "center" as const,
  } as React.CSSProperties,

  fullscreenButton: {
    position: "absolute" as const,
    bottom: 12,
    right: 12,
    padding: "8px 16px",
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "var(--color-text)",
    background: "rgba(0,0,0,0.6)",
    border: "1px solid var(--color-text-muted)",
    borderRadius: "var(--radius)",
    zIndex: 3,
    minHeight: 36,
  } as React.CSSProperties,
};
