/**
 * Unit tests for ResourceTimeline component.
 * Tests rendering of timeline header with date labels.
 *
 * Note: We use `new Date(year, monthIndex, day)` to create local-time dates,
 * avoiding UTC-offset issues that arise from ISO string parsing in jsdom.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResourceTimeline } from "../ResourceTimeline";
import type { GanttResourceViewConfig } from "@/types/ganttResource";

const makeConfig = (overrides: Partial<GanttResourceViewConfig> = {}): GanttResourceViewConfig => ({
  startDate: new Date(2026, 1, 2),  // Mon Feb 2
  endDate: new Date(2026, 1, 15),   // Sun Feb 15 (2 weeks)
  scale: "day" as const,
  rowHeight: 40,
  headerHeight: 60,
  sidebarWidth: 200,
  showUtilization: true,
  highlightOverallocations: true,
  ...overrides,
});

describe("ResourceTimeline", () => {
  it("renders timeline container", () => {
    const config = makeConfig();
    render(<ResourceTimeline config={config} width={800} />);
    expect(screen.getByTestId("resource-timeline")).toBeInTheDocument();
  });

  it("shows month headers", () => {
    const config = makeConfig();
    render(<ResourceTimeline config={config} width={800} />);
    expect(screen.getByText("Feb 2026")).toBeInTheDocument();
  });

  it("renders day cells", () => {
    const config = makeConfig({
      startDate: new Date(2026, 1, 10),
      endDate: new Date(2026, 1, 12),
      scale: "day",
    });
    render(<ResourceTimeline config={config} width={400} />);
    // Feb 10, 11, 12 -> day labels "10", "11", "12"
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("day scale shows all day labels", () => {
    const config = makeConfig({
      startDate: new Date(2026, 1, 2),
      endDate: new Date(2026, 1, 8),
      scale: "day",
    });
    const { container } = render(<ResourceTimeline config={config} width={600} />);
    // 7 days: Feb 2-8, all should have labels
    const dayLabels = container.querySelectorAll(".timeline-day-label");
    expect(dayLabels.length).toBe(7);
  });

  it("weekend cells have weekend class", () => {
    // Feb 7 (Sat) and Feb 8 (Sun) are weekends in 2026
    const config = makeConfig({
      startDate: new Date(2026, 1, 6),  // Friday
      endDate: new Date(2026, 1, 9),    // Monday
      scale: "day",
    });
    const { container } = render(<ResourceTimeline config={config} width={400} />);
    const weekendCells = container.querySelectorAll(".timeline-day.weekend");
    // Sat Feb 7 and Sun Feb 8 are weekends
    expect(weekendCells.length).toBe(2);
  });

  it("width style is set correctly", () => {
    const config = makeConfig();
    render(<ResourceTimeline config={config} width={1200} />);
    const timeline = screen.getByTestId("resource-timeline");
    expect(timeline).toHaveStyle({ width: "1200px" });
  });

  it("height matches headerHeight from config", () => {
    const config = makeConfig({ headerHeight: 80 });
    render(<ResourceTimeline config={config} width={800} />);
    const timeline = screen.getByTestId("resource-timeline");
    expect(timeline).toHaveStyle({ height: "80px" });
  });
});
