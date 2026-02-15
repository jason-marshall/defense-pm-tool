import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ProgramSettings } from "../ProgramSettings";

vi.mock("@/components/Settings/JiraSettings", () => ({
  JiraSettings: ({ programId }: { programId: string }) => (
    <div data-testid="jira-settings">JiraSettings: {programId}</div>
  ),
}));

vi.mock("@/components/Settings/VariancePanel", () => ({
  VariancePanel: ({ programId }: { programId: string }) => (
    <div data-testid="variance-panel">VariancePanel: {programId}</div>
  ),
}));

vi.mock("@/components/Settings/ManagementReservePanel", () => ({
  ManagementReservePanel: ({ programId }: { programId: string }) => (
    <div data-testid="reserve-panel">ReservePanel: {programId}</div>
  ),
}));

vi.mock("@/components/Settings/SkillsPanel", () => ({
  SkillsPanel: ({ programId }: { programId: string }) => (
    <div data-testid="skills-panel">SkillsPanel: {programId}</div>
  ),
}));

describe("ProgramSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 4 tabs", () => {
    render(<ProgramSettings programId="prog-1" />);

    expect(screen.getByText("Jira Integration")).toBeInTheDocument();
    expect(screen.getByText("Variance (VRID)")).toBeInTheDocument();
    expect(screen.getByText("Management Reserve")).toBeInTheDocument();
    expect(screen.getByText("Skills")).toBeInTheDocument();
  });

  it("shows Jira tab content by default", () => {
    render(<ProgramSettings programId="prog-1" />);

    expect(screen.getByTestId("jira-settings")).toBeInTheDocument();
    expect(screen.queryByTestId("variance-panel")).not.toBeInTheDocument();
  });

  it("switches between tabs", () => {
    render(<ProgramSettings programId="prog-1" />);

    fireEvent.click(screen.getByText("Variance (VRID)"));
    expect(screen.getByTestId("variance-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Management Reserve"));
    expect(screen.getByTestId("reserve-panel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Skills"));
    expect(screen.getByTestId("skills-panel")).toBeInTheDocument();
  });

  it("passes programId to child components", () => {
    render(<ProgramSettings programId="prog-1" />);

    expect(screen.getByText("JiraSettings: prog-1")).toBeInTheDocument();
  });
});
