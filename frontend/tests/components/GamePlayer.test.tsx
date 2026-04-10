import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import GamePlayer from "../../src/components/GamePlayer";

describe("GamePlayer", () => {
  it("renders iframe with sandbox attribute", () => {
    render(<GamePlayer html="<html><body>test</body></html>" />);
    const iframe = screen.getByTitle("Game");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("sandbox", "allow-scripts");
  });

  it("renders iframe immediately without loading overlay", () => {
    render(<GamePlayer html="<html><body>test</body></html>" />);
    // No loading overlay — iframe renders directly
    const iframe = screen.getByTitle("Game");
    expect(iframe).toBeInTheDocument();
    // Loading text should NOT be present
    expect(screen.queryByText(/загружаем/i)).not.toBeInTheDocument();
  });
});
