/**
 * Unit tests for useResourceFilter hook.
 */

import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useResourceFilter } from "./useResourceFilter";
import type { ResourceLane } from "@/types/ganttResource";

describe("useResourceFilter", () => {
  const createMockResource = (
    overrides: Partial<ResourceLane> = {}
  ): ResourceLane => ({
    resourceId: "1",
    resourceCode: "ENG-001",
    resourceName: "Engineer",
    resourceType: "labor",
    capacityPerDay: 8,
    assignments: [],
    dailyUtilization: new Map(),
    ...overrides,
  });

  const mockResources: ResourceLane[] = [
    createMockResource({
      resourceId: "1",
      resourceCode: "ENG-001",
      resourceName: "Senior Engineer",
      resourceType: "labor",
    }),
    createMockResource({
      resourceId: "2",
      resourceCode: "EQ-001",
      resourceName: "Crane A",
      resourceType: "equipment",
    }),
    createMockResource({
      resourceId: "3",
      resourceCode: "MAT-001",
      resourceName: "Steel Beam",
      resourceType: "material",
    }),
    createMockResource({
      resourceId: "4",
      resourceCode: "ENG-002",
      resourceName: "Junior Engineer",
      resourceType: "labor",
      assignments: [
        {
          assignmentId: "a1",
          activityId: "act1",
          activityCode: "ACT-001",
          activityName: "Design",
          startDate: new Date("2026-01-01"),
          endDate: new Date("2026-01-05"),
          units: 1.0,
          isCritical: false,
          isOverallocated: true,
        },
      ],
    }),
  ];

  it("returns all resources with default filter", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));
    expect(result.current.filteredResources).toHaveLength(4);
    expect(result.current.filteredCount).toBe(4);
    expect(result.current.totalCount).toBe(4);
  });

  it("filters by search term matching name", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, searchTerm: "Engineer" }));
    });

    expect(result.current.filteredResources).toHaveLength(2);
    expect(
      result.current.filteredResources.every((r) =>
        r.resourceName.includes("Engineer")
      )
    ).toBe(true);
  });

  it("filters by search term matching code", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, searchTerm: "EQ-001" }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].resourceCode).toBe("EQ-001");
  });

  it("search is case insensitive", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, searchTerm: "crane" }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].resourceName).toBe("Crane A");
  });

  it("filters by single resource type", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, resourceTypes: ["equipment"] }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].resourceType).toBe("equipment");
  });

  it("filters by multiple resource types", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({
        ...f,
        resourceTypes: ["labor", "material"],
      }));
    });

    expect(result.current.filteredResources).toHaveLength(3);
    expect(
      result.current.filteredResources.every(
        (r) => r.resourceType === "labor" || r.resourceType === "material"
      )
    ).toBe(true);
  });

  it("filters by overallocated only", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, showOnlyOverallocated: true }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].resourceCode).toBe("ENG-002");
  });

  it("filters by with assignments only", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({
        ...f,
        showOnlyWithAssignments: true,
      }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].assignments.length).toBeGreaterThan(0);
  });

  it("combines multiple filters", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({
        ...f,
        resourceTypes: ["labor"],
        showOnlyWithAssignments: true,
      }));
    });

    expect(result.current.filteredResources).toHaveLength(1);
    expect(result.current.filteredResources[0].resourceCode).toBe("ENG-002");
  });

  it("calculates stats correctly", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    expect(result.current.stats.total).toBe(4);
    expect(result.current.stats.labor).toBe(2);
    expect(result.current.stats.equipment).toBe(1);
    expect(result.current.stats.material).toBe(1);
    expect(result.current.stats.overallocated).toBe(1);
    expect(result.current.stats.withAssignments).toBe(1);
  });

  it("hasActiveFilters is false with default filter", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it("hasActiveFilters is true with search term", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, searchTerm: "test" }));
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("hasActiveFilters is true with reduced resource types", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({ ...f, resourceTypes: ["labor"] }));
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("clearFilters resets to default state", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({
        ...f,
        searchTerm: "test",
        resourceTypes: ["labor"],
        showOnlyOverallocated: true,
      }));
    });

    expect(result.current.hasActiveFilters).toBe(true);

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.hasActiveFilters).toBe(false);
    expect(result.current.filter.searchTerm).toBe("");
    expect(result.current.filter.resourceTypes).toHaveLength(3);
    expect(result.current.filter.showOnlyOverallocated).toBe(false);
  });

  it("returns empty array when no resources match", () => {
    const { result } = renderHook(() => useResourceFilter(mockResources));

    act(() => {
      result.current.setFilter((f) => ({
        ...f,
        searchTerm: "nonexistent",
      }));
    });

    expect(result.current.filteredResources).toHaveLength(0);
    expect(result.current.filteredCount).toBe(0);
  });
});
