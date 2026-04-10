import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import ErrorMessage from "../../src/components/ErrorMessage";

function renderWith(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("ErrorMessage", () => {
  it("shows correct message for generation_failed", () => {
    renderWith(<ErrorMessage type="generation_failed" />);
    expect(screen.getByText(/в игре баг/i)).toBeInTheDocument();
  });

  it("shows correct message for rate_limited", () => {
    renderWith(<ErrorMessage type="rate_limited" />);
    expect(screen.getByText(/создаёшь кучу игр/i)).toBeInTheDocument();
  });

  it("shows correct message for content_blocked", () => {
    renderWith(<ErrorMessage type="content_blocked" />);
    expect(screen.getByText(/что-то другое/i)).toBeInTheDocument();
  });

  it("shows correct message for content_filtered", () => {
    renderWith(<ErrorMessage type="content_filtered" />);
    expect(screen.getByText(/что-то другое/i)).toBeInTheDocument();
  });

  it("shows default message for unknown type", () => {
    renderWith(<ErrorMessage type="something_random" />);
    expect(screen.getByText(/что-то пошло не так/i)).toBeInTheDocument();
  });

  it("calls onRetry when button clicked", () => {
    const handleRetry = vi.fn();
    renderWith(<ErrorMessage type="generation_failed" onRetry={handleRetry} />);
    fireEvent.click(screen.getByText(/попробовать/i));
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it("calls onChangeIdea when button clicked", () => {
    const handleChange = vi.fn();
    renderWith(
      <ErrorMessage type="generation_failed" onChangeIdea={handleChange} />,
    );
    fireEvent.click(screen.getByText(/другая идея/i));
    expect(handleChange).toHaveBeenCalledOnce();
  });
});
