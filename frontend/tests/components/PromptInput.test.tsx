import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PromptInput from "../../src/components/PromptInput";

// PromptInput doesn't use react-router, so no wrapper needed

describe("PromptInput", () => {
  it("renders with placeholder text", () => {
    render(<PromptInput onSubmit={() => {}} />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveAttribute("placeholder");
  });

  it("submit button disabled when input too short", () => {
    render(<PromptInput onSubmit={() => {}} />);
    const button = screen.getByRole("button", { name: /создать игру/i });
    expect(button).toBeDisabled();
  });

  it("submit button enabled when input >= 10 chars", () => {
    render(<PromptInput onSubmit={() => {}} />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "A cat game with stars" } });
    const button = screen.getByRole("button", { name: /создать игру/i });
    expect(button).toBeEnabled();
  });

  it("calls onSubmit with prompt text", () => {
    const handleSubmit = vi.fn();
    render(<PromptInput onSubmit={handleSubmit} />);
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, {
      target: { value: "A cool platformer game" },
    });
    const button = screen.getByRole("button", { name: /создать игру/i });
    fireEvent.click(button);
    expect(handleSubmit).toHaveBeenCalledWith("A cool platformer game");
  });

  it("shows character count", () => {
    render(<PromptInput onSubmit={() => {}} />);
    expect(screen.getByText("0 / 500")).toBeInTheDocument();

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Hello" } });
    expect(screen.getByText("5 / 500")).toBeInTheDocument();
  });
});
