/**
 * ResourceFilterPanel - Filter and search resources in GanttResourceView.
 */

import { useState, useCallback } from "react";
import type { ResourceLane } from "@/types/ganttResource";
import type {
  ResourceFilterState,
  ResourcePool,
  FilterStats,
} from "@/types/resourceFilter";
import "./ResourceFilterPanel.css";

interface ResourceFilterPanelProps {
  resources: ResourceLane[];
  pools: ResourcePool[];
  filter: ResourceFilterState;
  stats: FilterStats;
  onFilterChange: (filter: ResourceFilterState) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

export function ResourceFilterPanel({
  pools,
  filter,
  stats,
  onFilterChange,
  onClearFilters,
  hasActiveFilters,
}: ResourceFilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onFilterChange({ ...filter, searchTerm: e.target.value });
    },
    [filter, onFilterChange]
  );

  const toggleResourceType = useCallback(
    (type: "labor" | "equipment" | "material") => {
      const types = filter.resourceTypes.includes(type)
        ? filter.resourceTypes.filter((t) => t !== type)
        : [...filter.resourceTypes, type];
      onFilterChange({ ...filter, resourceTypes: types });
    },
    [filter, onFilterChange]
  );

  return (
    <div className="resource-filter-panel" data-testid="resource-filter-panel">
      {/* Search bar */}
      <div className="filter-search">
        <svg
          className="search-icon"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          type="text"
          placeholder="Search resources..."
          value={filter.searchTerm}
          onChange={handleSearchChange}
          data-testid="filter-search-input"
        />
        {filter.searchTerm && (
          <button
            className="clear-search"
            onClick={() => onFilterChange({ ...filter, searchTerm: "" })}
            data-testid="clear-search"
            aria-label="Clear search"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Filter toggle */}
      <button
        className={`filter-toggle ${isExpanded ? "expanded" : ""} ${hasActiveFilters ? "has-filters" : ""}`}
        onClick={() => setIsExpanded(!isExpanded)}
        data-testid="filter-toggle"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        </svg>
        Filters
        {hasActiveFilters && <span className="filter-badge" />}
      </button>

      {/* Expanded filters */}
      {isExpanded && (
        <div className="filter-options" data-testid="filter-options">
          {/* Resource type toggles */}
          <div className="filter-group">
            <label>Resource Types</label>
            <div className="type-toggles">
              <button
                className={`type-toggle ${filter.resourceTypes.includes("labor") ? "active" : ""}`}
                onClick={() => toggleResourceType("labor")}
                data-testid="filter-type-labor"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                Labor ({stats.labor})
              </button>
              <button
                className={`type-toggle ${filter.resourceTypes.includes("equipment") ? "active" : ""}`}
                onClick={() => toggleResourceType("equipment")}
                data-testid="filter-type-equipment"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                </svg>
                Equipment ({stats.equipment})
              </button>
              <button
                className={`type-toggle ${filter.resourceTypes.includes("material") ? "active" : ""}`}
                onClick={() => toggleResourceType("material")}
                data-testid="filter-type-material"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16.5 9.4 7.55 4.24" />
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
                Material ({stats.material})
              </button>
            </div>
          </div>

          {/* Quick filters */}
          <div className="filter-group">
            <label>Quick Filters</label>
            <div className="quick-filters">
              <label className="checkbox-filter">
                <input
                  type="checkbox"
                  checked={filter.showOnlyOverallocated}
                  onChange={(e) =>
                    onFilterChange({
                      ...filter,
                      showOnlyOverallocated: e.target.checked,
                    })
                  }
                  data-testid="filter-overallocated"
                />
                Overallocated only ({stats.overallocated})
              </label>
              <label className="checkbox-filter">
                <input
                  type="checkbox"
                  checked={filter.showOnlyWithAssignments}
                  onChange={(e) =>
                    onFilterChange({
                      ...filter,
                      showOnlyWithAssignments: e.target.checked,
                    })
                  }
                  data-testid="filter-with-assignments"
                />
                With assignments ({stats.withAssignments})
              </label>
            </div>
          </div>

          {/* Pool filter */}
          {pools.length > 0 && (
            <div className="filter-group">
              <label>Resource Pools</label>
              <select
                multiple
                value={filter.poolIds}
                onChange={(e) => {
                  const selected = Array.from(
                    e.target.selectedOptions,
                    (opt) => opt.value
                  );
                  onFilterChange({ ...filter, poolIds: selected });
                }}
                data-testid="filter-pools"
              >
                {pools.map((pool) => (
                  <option key={pool.id} value={pool.id}>
                    {pool.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Clear all */}
          {hasActiveFilters && (
            <button
              className="clear-all-filters"
              onClick={onClearFilters}
              data-testid="clear-all-filters"
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}
