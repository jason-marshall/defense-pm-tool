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

  // --- New tests: programId propagation to every tab panel ---

  describe("programId propagation to all tabs", () => {
    it("passes programId to VariancePanel when Variance tab is active", () => {
      render(<ProgramSettings programId="prog-42" />);

      fireEvent.click(screen.getByText("Variance (VRID)"));
      expect(screen.getByText("VariancePanel: prog-42")).toBeInTheDocument();
    });

    it("passes programId to ManagementReservePanel when Reserve tab is active", () => {
      render(<ProgramSettings programId="prog-42" />);

      fireEvent.click(screen.getByText("Management Reserve"));
      expect(screen.getByText("ReservePanel: prog-42")).toBeInTheDocument();
    });

    it("passes programId to SkillsPanel when Skills tab is active", () => {
      render(<ProgramSettings programId="prog-42" />);

      fireEvent.click(screen.getByText("Skills"));
      expect(screen.getByText("SkillsPanel: prog-42")).toBeInTheDocument();
    });
  });

  // --- New tests: tab exclusivity (only one panel renders at a time) ---

  describe("tab exclusivity", () => {
    it("renders only JiraSettings when Jira tab is active", () => {
      render(<ProgramSettings programId="prog-1" />);

      expect(screen.getByTestId("jira-settings")).toBeInTheDocument();
      expect(screen.queryByTestId("variance-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("reserve-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("skills-panel")).not.toBeInTheDocument();
    });

    it("renders only VariancePanel when Variance tab is active", () => {
      render(<ProgramSettings programId="prog-1" />);

      fireEvent.click(screen.getByText("Variance (VRID)"));

      expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();
      expect(screen.getByTestId("variance-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("reserve-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("skills-panel")).not.toBeInTheDocument();
    });

    it("renders only ManagementReservePanel when Reserve tab is active", () => {
      render(<ProgramSettings programId="prog-1" />);

      fireEvent.click(screen.getByText("Management Reserve"));

      expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();
      expect(screen.queryByTestId("variance-panel")).not.toBeInTheDocument();
      expect(screen.getByTestId("reserve-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("skills-panel")).not.toBeInTheDocument();
    });

    it("renders only SkillsPanel when Skills tab is active", () => {
      render(<ProgramSettings programId="prog-1" />);

      fireEvent.click(screen.getByText("Skills"));

      expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();
      expect(screen.queryByTestId("variance-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("reserve-panel")).not.toBeInTheDocument();
      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();
    });
  });

  // --- New tests: tab switching round-trip (reset/cancel-like behavior) ---

  describe("tab switching round-trip", () => {
    it("returns to Jira tab content when clicking Jira Integration after switching away", () => {
      render(<ProgramSettings programId="prog-1" />);

      // Switch away
      fireEvent.click(screen.getByText("Skills"));
      expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();

      // Switch back
      fireEvent.click(screen.getByText("Jira Integration"));
      expect(screen.getByTestId("jira-settings")).toBeInTheDocument();
      expect(screen.queryByTestId("skills-panel")).not.toBeInTheDocument();
    });

    it("cycles through all tabs and returns to the first tab", () => {
      render(<ProgramSettings programId="prog-1" />);

      // Jira (default) -> Variance -> Reserve -> Skills -> Jira
      fireEvent.click(screen.getByText("Variance (VRID)"));
      expect(screen.getByTestId("variance-panel")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Management Reserve"));
      expect(screen.getByTestId("reserve-panel")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Skills"));
      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Jira Integration"));
      expect(screen.getByTestId("jira-settings")).toBeInTheDocument();
    });

    it("clicking the already-active tab does not unmount the panel", () => {
      render(<ProgramSettings programId="prog-1" />);

      // Jira is active by default, click it again
      fireEvent.click(screen.getByText("Jira Integration"));
      expect(screen.getByTestId("jira-settings")).toBeInTheDocument();
    });
  });

  // --- New tests: different programId values ---

  describe("different programId values", () => {
    it("renders with a UUID-style programId", () => {
      const uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";
      render(<ProgramSettings programId={uuid} />);

      expect(screen.getByText(`JiraSettings: ${uuid}`)).toBeInTheDocument();
    });

    it("renders with an empty string programId", () => {
      render(<ProgramSettings programId="" />);

      expect(screen.getByText("JiraSettings:")).toBeInTheDocument();
    });

    it("renders with a numeric string programId", () => {
      render(<ProgramSettings programId="12345" />);

      expect(screen.getByText("JiraSettings: 12345")).toBeInTheDocument();
    });

    it("propagates a different programId to each child panel correctly", () => {
      const programId = "defense-prog-abc";
      render(<ProgramSettings programId={programId} />);

      // Check Jira panel
      expect(
        screen.getByText(`JiraSettings: ${programId}`)
      ).toBeInTheDocument();

      // Switch to variance and check
      fireEvent.click(screen.getByText("Variance (VRID)"));
      expect(
        screen.getByText(`VariancePanel: ${programId}`)
      ).toBeInTheDocument();

      // Switch to reserve and check
      fireEvent.click(screen.getByText("Management Reserve"));
      expect(
        screen.getByText(`ReservePanel: ${programId}`)
      ).toBeInTheDocument();

      // Switch to skills and check
      fireEvent.click(screen.getByText("Skills"));
      expect(
        screen.getByText(`SkillsPanel: ${programId}`)
      ).toBeInTheDocument();
    });
  });

  // --- New tests: heading and structural elements ---

  describe("structural rendering", () => {
    it("renders the Settings heading", () => {
      render(<ProgramSettings programId="prog-1" />);

      expect(screen.getByText("Settings")).toBeInTheDocument();
    });

    it("renders the heading as an h2 element", () => {
      render(<ProgramSettings programId="prog-1" />);

      const heading = screen.getByText("Settings");
      expect(heading.tagName).toBe("H2");
    });

    it("renders exactly 4 tab buttons", () => {
      render(<ProgramSettings programId="prog-1" />);

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(4);
    });

    it("tab buttons are rendered within a nav element", () => {
      render(<ProgramSettings programId="prog-1" />);

      const nav = screen.getByRole("navigation");
      expect(nav).toBeInTheDocument();

      const buttons = nav.querySelectorAll("button");
      expect(buttons).toHaveLength(4);
    });
  });

  // --- New tests: active tab styling ---

  describe("active tab styling", () => {
    it("applies active styling to the default Jira tab", () => {
      render(<ProgramSettings programId="prog-1" />);

      const jiraTab = screen.getByText("Jira Integration");
      expect(jiraTab.className).toContain("border-blue-600");
      expect(jiraTab.className).toContain("text-blue-600");
    });

    it("applies inactive styling to non-active tabs", () => {
      render(<ProgramSettings programId="prog-1" />);

      const varianceTab = screen.getByText("Variance (VRID)");
      expect(varianceTab.className).toContain("border-transparent");
      expect(varianceTab.className).toContain("text-gray-500");
    });

    it("moves active styling when switching tabs", () => {
      render(<ProgramSettings programId="prog-1" />);

      const jiraTab = screen.getByText("Jira Integration");
      const varianceTab = screen.getByText("Variance (VRID)");

      // Initially Jira is active
      expect(jiraTab.className).toContain("border-blue-600");
      expect(varianceTab.className).toContain("border-transparent");

      // Click Variance
      fireEvent.click(varianceTab);

      // Now Variance is active, Jira is not
      expect(varianceTab.className).toContain("border-blue-600");
      expect(varianceTab.className).toContain("text-blue-600");
      expect(jiraTab.className).toContain("border-transparent");
      expect(jiraTab.className).toContain("text-gray-500");
    });

    it("applies active styling to Management Reserve tab when clicked", () => {
      render(<ProgramSettings programId="prog-1" />);

      const reserveTab = screen.getByText("Management Reserve");
      fireEvent.click(reserveTab);

      expect(reserveTab.className).toContain("border-blue-600");
      expect(reserveTab.className).toContain("text-blue-600");
    });

    it("applies active styling to Skills tab when clicked", () => {
      render(<ProgramSettings programId="prog-1" />);

      const skillsTab = screen.getByText("Skills");
      fireEvent.click(skillsTab);

      expect(skillsTab.className).toContain("border-blue-600");
      expect(skillsTab.className).toContain("text-blue-600");
    });
  });

  // --- New tests: re-render with different programId ---

  describe("re-render with different programId", () => {
    it("updates child component when programId prop changes", () => {
      const { rerender } = render(<ProgramSettings programId="prog-1" />);

      expect(screen.getByText("JiraSettings: prog-1")).toBeInTheDocument();

      rerender(<ProgramSettings programId="prog-2" />);

      expect(screen.getByText("JiraSettings: prog-2")).toBeInTheDocument();
      expect(
        screen.queryByText("JiraSettings: prog-1")
      ).not.toBeInTheDocument();
    });

    it("maintains active tab after programId change", () => {
      const { rerender } = render(<ProgramSettings programId="prog-1" />);

      fireEvent.click(screen.getByText("Skills"));
      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();

      rerender(<ProgramSettings programId="prog-2" />);

      // Skills tab should remain active
      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();
      expect(screen.getByText("SkillsPanel: prog-2")).toBeInTheDocument();
    });

    it("propagates new programId to variance panel after re-render", () => {
      const { rerender } = render(<ProgramSettings programId="prog-1" />);

      fireEvent.click(screen.getByText("Variance (VRID)"));
      expect(screen.getByText("VariancePanel: prog-1")).toBeInTheDocument();

      rerender(<ProgramSettings programId="prog-999" />);
      expect(screen.getByText("VariancePanel: prog-999")).toBeInTheDocument();
    });
  });

  // --- New tests: tab ordering ---

  describe("tab ordering", () => {
    it("renders tabs in the correct order", () => {
      render(<ProgramSettings programId="prog-1" />);

      const buttons = screen.getAllByRole("button");
      expect(buttons[0]).toHaveTextContent("Jira Integration");
      expect(buttons[1]).toHaveTextContent("Variance (VRID)");
      expect(buttons[2]).toHaveTextContent("Management Reserve");
      expect(buttons[3]).toHaveTextContent("Skills");
    });
  });

  // --- New tests: rapid tab switching ---

  describe("rapid tab switching", () => {
    it("handles rapid consecutive tab switches correctly", () => {
      render(<ProgramSettings programId="prog-1" />);

      // Rapidly click through all tabs
      fireEvent.click(screen.getByText("Variance (VRID)"));
      fireEvent.click(screen.getByText("Skills"));
      fireEvent.click(screen.getByText("Management Reserve"));
      fireEvent.click(screen.getByText("Jira Integration"));
      fireEvent.click(screen.getByText("Skills"));

      // Only the last-clicked tab should be visible
      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("jira-settings")).not.toBeInTheDocument();
      expect(screen.queryByTestId("variance-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("reserve-panel")).not.toBeInTheDocument();
    });
  });
});
