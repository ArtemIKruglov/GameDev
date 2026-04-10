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
    expect(screen.getByText("Hmm, that game had a bug!")).toBeInTheDocument();
    expect(
      screen.getByText("Even the best game makers need a second try."),
    ).toBeInTheDocument();
  });

  it("shows correct message for rate_limited", () => {
    renderWith(<ErrorMessage type="rate_limited" />);
    expect(screen.getByText("Wow, you've been busy!")).toBeInTheDocument();
    expect(
      screen.getByText(
        "You've been creating so many games! Take a break and come back in a bit.",
      ),
    ).toBeInTheDocument();
  });

  it("shows correct message for content_blocked", () => {
    renderWith(<ErrorMessage type="content_blocked" />);
    expect(
      screen.getByText("Let's keep it fun and friendly!"),
    ).toBeInTheDocument();
  });

  it("shows correct message for content_filtered (backend error code)", () => {
    renderWith(<ErrorMessage type="content_filtered" />);
    expect(
      screen.getByText("Let's keep it fun and friendly!"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Let's keep our games fun and friendly! Try a different idea.",
      ),
    ).toBeInTheDocument();
  });

  it("shows default message for unknown type", () => {
    renderWith(<ErrorMessage type="something_random" />);
    expect(
      screen.getByText("Oops! Something went wrong."),
    ).toBeInTheDocument();
  });

  it("calls onRetry when Try Again clicked", () => {
    const handleRetry = vi.fn();
    renderWith(<ErrorMessage type="generation_failed" onRetry={handleRetry} />);
    fireEvent.click(screen.getByText("Try Again"));
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it("calls onChangeIdea when Change My Idea clicked", () => {
    const handleChange = vi.fn();
    renderWith(
      <ErrorMessage type="generation_failed" onChangeIdea={handleChange} />,
    );
    fireEvent.click(screen.getByText("Change My Idea"));
    expect(handleChange).toHaveBeenCalledOnce();
  });
});
