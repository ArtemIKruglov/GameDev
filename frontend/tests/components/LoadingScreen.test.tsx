import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import LoadingScreen from "../../src/components/LoadingScreen";

describe("LoadingScreen", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows initial loading phase text", () => {
    render(<LoadingScreen />);
    expect(screen.getByText(/читаем твою идею/i)).toBeInTheDocument();
  });

  it("shows cancel button after delay", () => {
    const onCancel = vi.fn();
    render(<LoadingScreen onCancel={onCancel} />);

    expect(screen.queryByText(/отменить/i)).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(screen.getByText(/отменить/i)).toBeInTheDocument();
  });

  it("advances to second phase after 5 seconds", () => {
    render(<LoadingScreen />);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText(/рисуем игровой мир/i)).toBeInTheDocument();
  });

  it("shows a fun fact", () => {
    render(<LoadingScreen />);
    expect(screen.getByText(/1958/)).toBeInTheDocument();
  });
});
