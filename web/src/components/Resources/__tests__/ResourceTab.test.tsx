import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ResourceTab } from "../ResourceTab";

vi.mock("../ResourceList", () => ({
  ResourceList: ({ programId }: { programId: string }) => (
    <div data-testid="resource-list">ResourceList: {programId}</div>
  ),
}));

vi.mock("../LevelingPanel", () => ({
  LevelingPanel: ({ programId }: { programId: string }) => (
    <div data-testid="leveling-panel">LevelingPanel: {programId}</div>
  ),
}));

vi.mock("@/components/Settings/SkillsPanel", () => ({
  SkillsPanel: ({ programId }: { programId: string }) => (
    <div data-testid="skills-panel">SkillsPanel: {programId}</div>
  ),
}));

vi.mock("@/components/ResourceCost/CostSummaryPanel", () => ({
  CostSummaryPanel: ({ programId }: { programId: string }) => (
    <div data-testid="cost-panel">CostPanel: {programId}</div>
  ),
}));

vi.mock("@/components/Materials/MaterialSummaryPanel", () => ({
  MaterialSummaryPanel: ({ programId }: { programId: string }) => (
    <div data-testid="material-panel">MaterialPanel: {programId}</div>
  ),
}));

vi.mock("@/components/ResourcePools/ResourcePoolList", () => ({
  ResourcePoolList: ({ programId }: { programId: string }) => (
    <div data-testid="pool-list">PoolList: {programId}</div>
  ),
}));

describe("ResourceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 7 tabs", () => {
    render(<ResourceTab programId="prog-1" />);

    expect(screen.getByText("Resources")).toBeInTheDocument();
    expect(screen.getByText("Histogram")).toBeInTheDocument();
    expect(screen.getByText("Leveling")).toBeInTheDocument();
    expect(screen.getByText("Skills")).toBeInTheDocument();
    expect(screen.getByText("Cost")).toBeInTheDocument();
    expect(screen.getByText("Materials")).toBeInTheDocument();
    expect(screen.getByText("Pools")).toBeInTheDocument();
  });

  it("shows Resources tab by default", () => {
    render(<ResourceTab programId="prog-1" />);

    expect(screen.getByTestId("resource-list")).toBeInTheDocument();
    expect(screen.queryByTestId("leveling-panel")).not.toBeInTheDocument();
  });

  it("switches between tabs", () => {
    render(<ResourceTab programId="prog-1" />);

    fireEvent.click(screen.getByText("Leveling"));
    expect(screen.getByTestId("leveling-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("resource-list")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Skills"));
    expect(screen.getByTestId("skills-panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cost"));
    expect(screen.getByTestId("cost-panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Materials"));
    expect(screen.getByTestId("material-panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Pools"));
    expect(screen.getByTestId("pool-list")).toBeInTheDocument();
  });

  it("shows histogram placeholder text", () => {
    render(<ResourceTab programId="prog-1" />);

    fireEvent.click(screen.getByText("Histogram"));
    expect(
      screen.getByText(
        "Select a resource from the Resources tab to view its histogram."
      )
    ).toBeInTheDocument();
  });
});
