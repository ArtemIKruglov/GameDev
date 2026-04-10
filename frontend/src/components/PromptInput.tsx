import { useState, useEffect, useRef, useCallback } from "react";

const PLACEHOLDERS = [
  "Игра, где котик ловит падающую рыбку...",
  "Космический шутер, где уворачиваешься от астероидов...",
  "Лабиринт, где нужно сбежать от дракона...",
  "Головоломка — соединяй цвета по парам...",
  "Гонки на пингвинах по льду...",
];

const MAX_CHARS = 500;
const MIN_CHARS = 10;

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  disabled?: boolean;
  initialValue?: string;
}

export default function PromptInput({
  onSubmit,
  disabled,
  initialValue = "",
}: PromptInputProps) {
  const [value, setValue] = useState(initialValue);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);

  // Sync when initialValue changes (e.g. from example cards or retry)
  useEffect(() => {
    if (initialValue) setValue(initialValue);
  }, [initialValue]);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const hasSpeech =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  useEffect(() => {
    const timer = setInterval(() => {
      setPlaceholderIndex((i) => (i + 1) % PLACEHOLDERS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (value.trim().length >= MIN_CHARS && !disabled) {
        onSubmit(value.trim());
      }
    },
    [value, disabled, onSubmit],
  );

  const toggleSpeech = useCallback(() => {
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      setListening(false);
      return;
    }

    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionClass) return;

    const recognition = new SpeechRecognitionClass();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setValue((prev) => (prev ? prev + " " + transcript : transcript));
    };

    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [listening]);

  const canSubmit = value.trim().length >= MIN_CHARS && !disabled;

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.textareaWrapper}>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={PLACEHOLDERS[placeholderIndex]}
          maxLength={MAX_CHARS}
          disabled={disabled}
          rows={4}
          style={styles.textarea}
          aria-label="Опиши свою игру"
        />
        <span style={styles.charCount}>
          {value.length} / {MAX_CHARS}
        </span>
      </div>

      <div style={styles.actions}>
        {hasSpeech && (
          <button
            type="button"
            onClick={toggleSpeech}
            style={{
              ...styles.micButton,
              ...(listening ? styles.micActive : {}),
            }}
            aria-label={listening ? "Стоп" : "Скажи голосом"}
          >
            {listening ? "..." : "🎤"}
          </button>
        )}

        <button type="submit" disabled={!canSubmit} style={styles.submitButton(canSubmit)}>
          Создать игру! 🚀
        </button>
      </div>
    </form>
  );
}

const styles = {
  form: {
    width: "100%",
    maxWidth: 600,
    margin: "0 auto",
  } as React.CSSProperties,

  textareaWrapper: {
    position: "relative" as const,
  } as React.CSSProperties,

  textarea: {
    width: "100%",
    minHeight: 140,
    padding: "16px 16px 32px",
    background: "var(--color-bg-input)",
    color: "var(--color-text)",
    border: "2px solid var(--color-primary)",
    borderRadius: "var(--radius)",
    fontSize: "1.1rem",
    lineHeight: 1.6,
    resize: "vertical" as const,
    outline: "none",
    fontFamily: "inherit",
    transition: "border-color 0.2s",
  } as React.CSSProperties,

  charCount: {
    position: "absolute" as const,
    bottom: 10,
    right: 14,
    fontSize: "0.8rem",
    color: "var(--color-text-muted)",
    pointerEvents: "none" as const,
  } as React.CSSProperties,

  actions: {
    display: "flex",
    gap: 12,
    marginTop: 12,
    justifyContent: "center",
    alignItems: "center",
  } as React.CSSProperties,

  micButton: {
    width: 48,
    height: 48,
    borderRadius: "50%",
    background: "var(--color-bg-card)",
    border: "2px solid var(--color-primary)",
    fontSize: "1.3rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "var(--color-text)",
    transition: "all 0.2s",
  } as React.CSSProperties,

  micActive: {
    background: "var(--color-accent-warm)",
    borderColor: "var(--color-accent-warm)",
  } as React.CSSProperties,

  submitButton: (enabled: boolean): React.CSSProperties => ({
    padding: "14px 40px",
    fontSize: "1.2rem",
    fontWeight: 700,
    color: "#fff",
    background: enabled
      ? "linear-gradient(135deg, var(--color-primary), var(--color-accent))"
      : "var(--color-bg-card)",
    border: "none",
    borderRadius: "var(--radius)",
    opacity: enabled ? 1 : 0.5,
    cursor: enabled ? "pointer" : "not-allowed",
    transition: "all 0.2s",
    minHeight: 48,
  }),
};
