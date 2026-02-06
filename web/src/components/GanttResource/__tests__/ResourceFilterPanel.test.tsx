/**
 * Unit tests for ResourceFilterPanel component.
 * Tests filter controls, search, type toggles, and clear actions.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ResourceFilterPanel } from "../ResourceFilterPanel";
import type { ResourceFilterState, ResourcePool, FilterStats } from "@/types/resourceFilter";
import type { ResourceLane } from "@/types/ganttResource";

const defaultFilter: ResourceFilterState = {
  searchTerm: "",
  resourceTypes: ["labor", "equipment", "material"],
  showOnlyOverallocated: false,
  showOnlyWithAssignments: false,
  poolIds: [],
};

const defaultStats: FilterStats = {
  total: 10,
  labor: 5,
  equipment: 3,
  material: 2,
  overallocated: 1,
  withAssignments: 7,
};

const defaultResources: ResourceLane[] = [];

const defaultPools: ResourcePool[] = [];

describe("ResourceFilterPanel", () => {
  const defaultProps = {
    resources: defaultResources,
    pools: defaultPools,
    filter: defaultFilter,
    stats: defaultStats,
    onFilterChange: vi.fn(),
    onClearFilters: vi.fn(),
    hasActiveFilters: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders filter panel container", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    expect(screen.getByTestId("resource-filter-panel")).toBeInTheDocument();
  });

  it("renders search input with placeholder", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    const input = screen.getByTestId("filter-search-input");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("placeholder", "Search resources...");
  });

  it("search input value reflects filter.searchTerm", () => {
    render(
      <ResourceFilterPanel
        {...defaultProps}
        filter={{ ...defaultFilter, searchTerm: "crane" }}
      />
    );
    const input = screen.getByTestId("filter-search-input");
    expect(input).toHaveValue("crane");
  });

  it("typing in search calls onFilterChange with updated searchTerm", () => {
    const onFilterChange = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        onFilterChange={onFilterChange}
      />
    );
    const input = screen.getByTestId("filter-search-input");
    fireEvent.change(input, { target: { value: "eng" } });
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      searchTerm: "eng",
    });
  });

  it("clear search button shown when searchTerm is non-empty", () => {
    render(
      <ResourceFilterPanel
        {...defaultProps}
        filter={{ ...defaultFilter, searchTerm: "test" }}
      />
    );
    expect(screen.getByTestId("clear-search")).toBeInTheDocument();
  });

  it("clear search button not shown when searchTerm is empty", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    expect(screen.queryByTestId("clear-search")).not.toBeInTheDocument();
  });

  it("clicking clear search sets searchTerm to empty", () => {
    const onFilterChange = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        filter={{ ...defaultFilter, searchTerm: "crane" }}
        onFilterChange={onFilterChange}
      />
    );
    fireEvent.click(screen.getByTestId("clear-search"));
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      searchTerm: "",
    });
  });

  it("filter toggle button is visible", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    expect(screen.getByTestId("filter-toggle")).toBeInTheDocument();
  });

  it("clicking filter toggle expands options", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    expect(screen.queryByTestId("filter-options")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("filter-toggle"));
    expect(screen.getByTestId("filter-options")).toBeInTheDocument();
  });

  it("resource type toggles shown when expanded", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.getByTestId("filter-type-labor")).toBeInTheDocument();
    expect(screen.getByTestId("filter-type-equipment")).toBeInTheDocument();
    expect(screen.getByTestId("filter-type-material")).toBeInTheDocument();
  });

  it("clicking labor type toggle calls onFilterChange", () => {
    const onFilterChange = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        onFilterChange={onFilterChange}
      />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));
    fireEvent.click(screen.getByTestId("filter-type-labor"));

    // Labor was in the list, so clicking removes it
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      resourceTypes: ["equipment", "material"],
    });
  });

  it("shows stats counts in type buttons", () => {
    render(<ResourceFilterPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.getByTestId("filter-type-labor")).toHaveTextContent("Labor (5)");
    expect(screen.getByTestId("filter-type-equipment")).toHaveTextContent("Equipment (3)");
    expect(screen.getByTestId("filter-type-material")).toHaveTextContent("Material (2)");
  });

  it("overallocated checkbox changes filter", () => {
    const onFilterChange = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        onFilterChange={onFilterChange}
      />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));

    const checkbox = screen.getByTestId("filter-overallocated");
    fireEvent.click(checkbox);
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      showOnlyOverallocated: true,
    });
  });

  it("with assignments checkbox changes filter", () => {
    const onFilterChange = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        onFilterChange={onFilterChange}
      />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));

    const checkbox = screen.getByTestId("filter-with-assignments");
    fireEvent.click(checkbox);
    expect(onFilterChange).toHaveBeenCalledWith({
      ...defaultFilter,
      showOnlyWithAssignments: true,
    });
  });

  it("pool select shown when pools exist", () => {
    const pools: ResourcePool[] = [
      { id: "pool-1", name: "Engineering Pool" },
      { id: "pool-2", name: "Construction Pool" },
    ];
    render(
      <ResourceFilterPanel {...defaultProps} pools={pools} />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.getByTestId("filter-pools")).toBeInTheDocument();
    expect(screen.getByText("Engineering Pool")).toBeInTheDocument();
    expect(screen.getByText("Construction Pool")).toBeInTheDocument();
  });

  it("pool select not shown when pools is empty", () => {
    render(<ResourceFilterPanel {...defaultProps} pools={[]} />);
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.queryByTestId("filter-pools")).not.toBeInTheDocument();
  });

  it("Clear All Filters button shown when hasActiveFilters=true", () => {
    render(
      <ResourceFilterPanel {...defaultProps} hasActiveFilters={true} />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.getByTestId("clear-all-filters")).toBeInTheDocument();
    expect(screen.getByText("Clear All Filters")).toBeInTheDocument();
  });

  it("Clear All Filters not shown when hasActiveFilters=false", () => {
    render(
      <ResourceFilterPanel {...defaultProps} hasActiveFilters={false} />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));

    expect(screen.queryByTestId("clear-all-filters")).not.toBeInTheDocument();
  });

  it("clicking Clear All calls onClearFilters", () => {
    const onClearFilters = vi.fn();
    render(
      <ResourceFilterPanel
        {...defaultProps}
        hasActiveFilters={true}
        onClearFilters={onClearFilters}
      />
    );
    fireEvent.click(screen.getByTestId("filter-toggle"));
    fireEvent.click(screen.getByTestId("clear-all-filters"));

    expect(onClearFilters).toHaveBeenCalledTimes(1);
  });
});
