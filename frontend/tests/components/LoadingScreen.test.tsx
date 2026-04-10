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
    expect(screen.getByText("Reading your idea...")).toBeInTheDocument();
  });

  it("shows cancel button after delay", () => {
    const onCancel = vi.fn();
    render(<LoadingScreen onCancel={onCancel} />);

    // Not visible initially
    expect(screen.queryByText("Cancel")).not.toBeInTheDocument();

    // Advance 10 seconds
    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("advances to second phase after 5 seconds", () => {
    render(<LoadingScreen />);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(
      screen.getByText("Designing your game world..."),
    ).toBeInTheDocument();
  });

  it("shows a fun fact", () => {
    render(<LoadingScreen />);
    // The first fun fact is displayed on mount
    expect(
      screen.getByText("The first video game was made in 1958!"),
    ).toBeInTheDocument();
  });
});
