/**
 * ResourceSidebar - Shows resource information in the left panel.
 */

import type { ResourceLane } from "@/types/ganttResource";

interface ResourceSidebarProps {
  resources: ResourceLane[];
  rowHeight: number;
  headerHeight: number;
}

const resourceTypeIcons: Record<string, string> = {
  labor: "L",
  equipment: "E",
  material: "M",
};

const resourceTypeColors: Record<string, string> = {
  labor: "#3b82f6",
  equipment: "#f59e0b",
  material: "#10b981",
};

export function ResourceSidebar({
  resources,
  rowHeight,
  headerHeight,
}: ResourceSidebarProps) {
  return (
    <div className="resource-sidebar" data-testid="resource-sidebar">
      {/* Header */}
      <div
        className="resource-sidebar-header"
        style={{ height: headerHeight }}
      >
        <span className="resource-sidebar-title">Resources</span>
      </div>

      {/* Resource rows */}
      <div className="resource-sidebar-rows">
        {resources.map((resource) => (
          <div
            key={resource.resourceId}
            className="resource-sidebar-row"
            style={{ height: rowHeight }}
            data-testid={`sidebar-row-${resource.resourceId}`}
          >
            <span
              className="resource-type-badge"
              style={{
                backgroundColor: resourceTypeColors[resource.resourceType],
              }}
              title={resource.resourceType}
            >
              {resourceTypeIcons[resource.resourceType]}
            </span>
            <div className="resource-info">
              <span className="resource-code">{resource.resourceCode}</span>
              <span className="resource-name" title={resource.resourceName}>
                {resource.resourceName}
              </span>
            </div>
            <span className="resource-capacity">
              {resource.capacityPerDay}h/d
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
