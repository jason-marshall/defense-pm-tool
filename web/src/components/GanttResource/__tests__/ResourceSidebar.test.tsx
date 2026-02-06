/**
 * Unit tests for ResourceSidebar component.
 * Tests rendering of resource info in the left panel.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResourceSidebar } from "../ResourceSidebar";
import type { ResourceLane } from "@/types/ganttResource";

const makeResource = (overrides: Partial<ResourceLane> = {}): ResourceLane => ({
  resourceId: "res-1",
  resourceCode: "ENG-001",
  resourceName: "Senior Engineer",
  resourceType: "labor",
  capacityPerDay: 8,
  assignments: [],
  dailyUtilization: new Map(),
  ...overrides,
});

const defaultResources: ResourceLane[] = [
  makeResource(),
  makeResource({
    resourceId: "res-2",
    resourceCode: "EQP-001",
    resourceName: "Crane A",
    resourceType: "equipment",
    capacityPerDay: 10,
  }),
  makeResource({
    resourceId: "res-3",
    resourceCode: "MAT-001",
    resourceName: "Steel Beams",
    resourceType: "material",
    capacityPerDay: 100,
  }),
];

describe("ResourceSidebar", () => {
  const defaultProps = {
    resources: defaultResources,
    rowHeight: 40,
    headerHeight: 60,
  };

  it("renders sidebar container", () => {
    render(<ResourceSidebar {...defaultProps} />);
    expect(screen.getByTestId("resource-sidebar")).toBeInTheDocument();
  });

  it("shows Resources header", () => {
    render(<ResourceSidebar {...defaultProps} />);
    expect(screen.getByText("Resources")).toBeInTheDocument();
  });

  it("renders correct number of resource rows", () => {
    render(<ResourceSidebar {...defaultProps} />);
    expect(screen.getByTestId("sidebar-row-res-1")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar-row-res-2")).toBeInTheDocument();
    expect(screen.getByTestId("sidebar-row-res-3")).toBeInTheDocument();
  });

  it("shows resource code and name", () => {
    render(<ResourceSidebar {...defaultProps} />);
    expect(screen.getByText("ENG-001")).toBeInTheDocument();
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText("EQP-001")).toBeInTheDocument();
    expect(screen.getByText("Crane A")).toBeInTheDocument();
    expect(screen.getByText("MAT-001")).toBeInTheDocument();
    expect(screen.getByText("Steel Beams")).toBeInTheDocument();
  });

  it("shows type badge L for labor", () => {
    render(
      <ResourceSidebar
        {...defaultProps}
        resources={[makeResource({ resourceType: "labor" })]}
      />
    );
    expect(screen.getByText("L")).toBeInTheDocument();
  });

  it("shows type badge E for equipment", () => {
    render(
      <ResourceSidebar
        {...defaultProps}
        resources={[makeResource({ resourceId: "res-eq", resourceType: "equipment" })]}
      />
    );
    expect(screen.getByText("E")).toBeInTheDocument();
  });

  it("shows type badge M for material", () => {
    render(
      <ResourceSidebar
        {...defaultProps}
        resources={[makeResource({ resourceId: "res-mat", resourceType: "material" })]}
      />
    );
    expect(screen.getByText("M")).toBeInTheDocument();
  });

  it("shows capacity formatted as hours/day", () => {
    render(<ResourceSidebar {...defaultProps} />);
    expect(screen.getByText("8h/d")).toBeInTheDocument();
    expect(screen.getByText("10h/d")).toBeInTheDocument();
    expect(screen.getByText("100h/d")).toBeInTheDocument();
  });

  it("header height is set via style", () => {
    const { container } = render(<ResourceSidebar {...defaultProps} />);
    const header = container.querySelector(".resource-sidebar-header") as HTMLElement;
    expect(header).toHaveStyle({ height: "60px" });
  });

  it("row height is set via style", () => {
    render(<ResourceSidebar {...defaultProps} />);
    const row = screen.getByTestId("sidebar-row-res-1");
    expect(row).toHaveStyle({ height: "40px" });
  });

  it("empty resources list renders no rows", () => {
    render(<ResourceSidebar {...defaultProps} resources={[]} />);
    expect(screen.getByTestId("resource-sidebar")).toBeInTheDocument();
    expect(screen.getByText("Resources")).toBeInTheDocument();
    expect(screen.queryByTestId(/^sidebar-row-/)).not.toBeInTheDocument();
  });
});
