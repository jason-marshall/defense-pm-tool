import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CriticalPathView } from "../CriticalPathView";
import type { ScheduleResult } from "@/types/schedule";

const mockResults: ScheduleResult[] = [
  {
    activity_id: "act-1",
    activity_code: "A-001",
    activity_name: "Design",
    duration: 10,
    early_start: 0,
    early_finish: 10,
    late_start: 0,
    late_finish: 10,
    total_float: 0,
    free_float: 0,
    is_critical: true,
  },
  {
    activity_id: "act-2",
    activity_code: "A-002",
    activity_name: "Build",
    duration: 15,
    early_start: 10,
    early_finish: 25,
    late_start: 10,
    late_finish: 25,
    total_float: 0,
    free_float: 0,
    is_critical: true,
  },
  {
    activity_id: "act-3",
    activity_code: "A-003",
    activity_name: "Documentation",
    duration: 5,
    early_start: 0,
    early_finish: 5,
    late_start: 20,
    late_finish: 25,
    total_float: 20,
    free_float: 20,
    is_critical: false,
  },
];

const mockCriticalPath = ["act-1", "act-2"];

describe("CriticalPathView", () => {
  it("renders critical path boxes with activity details", () => {
    render(
      <CriticalPathView results={mockResults} criticalPath={mockCriticalPath} />
    );

    expect(screen.getByText("A-001")).toBeInTheDocument();
    expect(screen.getByText("Design")).toBeInTheDocument();
    expect(screen.getByText("10d")).toBeInTheDocument();

    expect(screen.getByText("A-002")).toBeInTheDocument();
    expect(screen.getByText("Build")).toBeInTheDocument();
    expect(screen.getByText("15d")).toBeInTheDocument();

    // Non-critical activity should not appear
    expect(screen.queryByText("Documentation")).not.toBeInTheDocument();
  });

  it("shows arrows between activities", () => {
    const { container } = render(
      <CriticalPathView results={mockResults} criticalPath={mockCriticalPath} />
    );

    // The arrow character → is rendered as &rarr;
    const arrows = container.querySelectorAll(".text-gray-300");
    expect(arrows.length).toBe(1); // One arrow between 2 activities
  });

  it("shows summary count", () => {
    render(
      <CriticalPathView results={mockResults} criticalPath={mockCriticalPath} />
    );

    expect(
      screen.getByText("2 activities on critical path")
    ).toBeInTheDocument();
  });

  it("shows empty state message when no critical activities", () => {
    render(<CriticalPathView results={[]} criticalPath={[]} />);

    expect(
      screen.getByText(
        "No critical path identified. Calculate the schedule first."
      )
    ).toBeInTheDocument();
  });
});
