import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState
        icon={<span data-testid="test-icon" />}
        title="No results found"
        description="Try adjusting your search."
      />,
    );
    expect(screen.getByText("No results found")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your search.")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(
      <EmptyState
        icon={<span data-testid="test-icon" />}
        title="No data"
        description="No data available."
        action={<button>Retry</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("has status role for accessibility", () => {
    render(
      <EmptyState
        icon={<span />}
        title="Empty"
        description="Nothing here."
      />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
