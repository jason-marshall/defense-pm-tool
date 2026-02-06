/**
 * Unit tests for UtilizationOverlay component.
 * Tests daily utilization background color rendering.
 *
 * Note: The component generates date keys via `day.toISOString().split("T")[0]`
 * which returns UTC dates. We use a helper to compute the same key for the Map
 * to ensure tests work regardless of local timezone.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UtilizationOverlay } from "../UtilizationOverlay";
import type {
  ResourceLane,
  GanttResourceViewConfig,
} from "@/types/ganttResource";
import { eachDayOfInterval } from "date-fns";

/**
 * Return the date key that the component will generate for a given local Date.
 * This mirrors the component logic: `day.toISOString().split("T")[0]`.
 */
function toDateKey(date: Date): string {
  return date.toISOString().split("T")[0];
}

// Use local-time Date constructor to match eachDayOfInterval behavior
const configStartDate = new Date(2026, 1, 2);  // Feb 2, local
const configEndDate = new Date(2026, 1, 6);    // Feb 6, local

const baseConfig: GanttResourceViewConfig = {
  startDate: configStartDate,
  endDate: configEndDate,
  scale: "day" as const,
  rowHeight: 40,
  headerHeight: 60,
  sidebarWidth: 200,
  showUtilization: true,
  highlightOverallocations: true,
};

// Pre-compute the days the component will generate
const days = eachDayOfInterval({ start: configStartDate, end: configEndDate });

const makeLane = (
  utilization: Map<string, number> = new Map()
): ResourceLane => ({
  resourceId: "res-1",
  resourceCode: "ENG-001",
  resourceName: "Senior Engineer",
  resourceType: "labor",
  capacityPerDay: 8,
  assignments: [],
  dailyUtilization: utilization,
});

describe("UtilizationOverlay", () => {
  it("renders overlay container with correct testid", () => {
    const lane = makeLane();
    render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    expect(
      screen.getByTestId("utilization-overlay-res-1")
    ).toBeInTheDocument();
  });

  it("renders cells for each day", () => {
    const lane = makeLane();
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    // Feb 2 to Feb 6 inclusive = 5 days
    const cells = container.querySelectorAll(".utilization-cell");
    expect(cells.length).toBe(5);
  });

  it("zero utilization results in transparent background", () => {
    const lane = makeLane(new Map());
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    // All cells should have transparent background (no utilization data)
    cells.forEach((cell) => {
      const el = cell as HTMLElement;
      expect(el.style.backgroundColor).toBe("transparent");
    });
  });

  it("under-utilized results in green tint", () => {
    // 3h out of 8h capacity = 37.5% -> <=50% -> green
    const key = toDateKey(days[0]);
    const utilMap = new Map([[key, 3]]);
    const lane = makeLane(utilMap);
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    const firstCell = cells[0] as HTMLElement;
    expect(firstCell.style.backgroundColor).toContain("rgba(34, 197, 94");
  });

  it("moderate utilization results in yellow tint", () => {
    // 5h out of 8h capacity = 62.5% -> <=80% -> yellow
    const key = toDateKey(days[1]);
    const utilMap = new Map([[key, 5]]);
    const lane = makeLane(utilMap);
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    const cell = cells[1] as HTMLElement;
    expect(cell.style.backgroundColor).toContain("rgba(234, 179, 8");
  });

  it("near capacity results in orange tint", () => {
    // 7h out of 8h capacity = 87.5% -> <=100% -> orange
    const key = toDateKey(days[2]);
    const utilMap = new Map([[key, 7]]);
    const lane = makeLane(utilMap);
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    const cell = cells[2] as HTMLElement;
    expect(cell.style.backgroundColor).toContain("rgba(249, 115, 22");
  });

  it("over-allocated results in red tint", () => {
    // 12h out of 8h capacity = 150% -> >100% -> red
    const key = toDateKey(days[3]);
    const utilMap = new Map([[key, 12]]);
    const lane = makeLane(utilMap);
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    const cell = cells[3] as HTMLElement;
    expect(cell.style.backgroundColor).toContain("rgba(239, 68, 68");
  });

  it("cells have correct title attribute", () => {
    // 4h out of 8h = 50%
    const key = toDateKey(days[0]);
    const utilMap = new Map([[key, 4]]);
    const lane = makeLane(utilMap);
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    const firstCell = cells[0] as HTMLElement;
    expect(firstCell.title).toBe(`${key}: 4.0h / 8h (50%)`);
  });

  it("cell positioning uses dayWidth", () => {
    const lane = makeLane();
    const { container } = render(
      <UtilizationOverlay lane={lane} config={baseConfig} dayWidth={40} />
    );
    const cells = container.querySelectorAll(".utilization-cell");
    // Check left positioning: index * dayWidth
    expect(cells[0]).toHaveStyle({ left: "0px", width: "40px" });
    expect(cells[1]).toHaveStyle({ left: "40px", width: "40px" });
    expect(cells[2]).toHaveStyle({ left: "80px", width: "40px" });
    expect(cells[3]).toHaveStyle({ left: "120px", width: "40px" });
    expect(cells[4]).toHaveStyle({ left: "160px", width: "40px" });
  });
});
