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

  it("shows loading state initially", () => {
    render(<GamePlayer html="<html><body>test</body></html>" />);
    expect(screen.getByText("Loading game...")).toBeInTheDocument();
  });
});
