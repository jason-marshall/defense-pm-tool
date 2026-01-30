/**
 * Hook for filtering resources in GanttResourceView.
 */

import { useState, useMemo, useCallback } from "react";
import type { ResourceLane } from "@/types/ganttResource";
import type { ResourceFilterState, FilterStats } from "@/types/resourceFilter";
import { defaultFilterState } from "@/types/resourceFilter";

export function useResourceFilter(resources: ResourceLane[]) {
  const [filter, setFilter] = useState<ResourceFilterState>(defaultFilterState);

  const filteredResources = useMemo(() => {
    return resources.filter((resource) => {
      // Search term filter
      if (filter.searchTerm) {
        const search = filter.searchTerm.toLowerCase();
        if (
          !resource.resourceName.toLowerCase().includes(search) &&
          !resource.resourceCode.toLowerCase().includes(search)
        ) {
          return false;
        }
      }

      // Resource type filter
      if (!filter.resourceTypes.includes(resource.resourceType)) {
        return false;
      }

      // Overallocated filter
      if (filter.showOnlyOverallocated) {
        const hasOverallocation = resource.assignments.some(
          (a) => a.isOverallocated
        );
        if (!hasOverallocation) return false;
      }

      // With assignments filter
      if (filter.showOnlyWithAssignments) {
        if (resource.assignments.length === 0) return false;
      }

      return true;
    });
  }, [resources, filter]);

  const stats: FilterStats = useMemo(
    () => ({
      total: resources.length,
      labor: resources.filter((r) => r.resourceType === "labor").length,
      equipment: resources.filter((r) => r.resourceType === "equipment").length,
      material: resources.filter((r) => r.resourceType === "material").length,
      overallocated: resources.filter((r) =>
        r.assignments.some((a) => a.isOverallocated)
      ).length,
      withAssignments: resources.filter((r) => r.assignments.length > 0).length,
    }),
    [resources]
  );

  const updateFilter = useCallback(
    (
      updater:
        | ResourceFilterState
        | ((prev: ResourceFilterState) => ResourceFilterState)
    ) => {
      if (typeof updater === "function") {
        setFilter(updater);
      } else {
        setFilter(updater);
      }
    },
    []
  );

  const clearFilters = useCallback(() => {
    setFilter(defaultFilterState);
  }, []);

  const hasActiveFilters = useMemo(() => {
    return (
      filter.searchTerm !== "" ||
      filter.resourceTypes.length < 3 ||
      filter.showOnlyOverallocated ||
      filter.showOnlyWithAssignments ||
      filter.poolIds.length > 0
    );
  }, [filter]);

  return {
    filter,
    setFilter: updateFilter,
    filteredResources,
    filteredCount: filteredResources.length,
    totalCount: resources.length,
    stats,
    hasActiveFilters,
    clearFilters,
  };
}
