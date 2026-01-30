/**
 * Hook for fetching and managing Gantt resource view data.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type {
  ResourceLane,
  AssignmentBar,
  AssignmentChange,
} from "@/types/ganttResource";

interface ResourceResponse {
  id: string;
  code: string;
  name: string;
  resource_type: string;
  capacity_per_day: string;
}

interface AssignmentResponse {
  id: string;
  activity_id: string;
  start_date: string | null;
  finish_date: string | null;
  units: string;
  activity?: {
    code: string;
    name: string;
    early_start: string | null;
    early_finish: string | null;
    is_critical: boolean;
  };
}

function calculateUtilization(lanes: ResourceLane[]): ResourceLane[] {
  return lanes.map((lane) => {
    const utilization = new Map<string, number>();

    // Calculate daily utilization
    lane.assignments.forEach((assignment) => {
      const current = new Date(assignment.startDate);
      while (current <= assignment.endDate) {
        const dateKey = current.toISOString().split("T")[0];
        const existing = utilization.get(dateKey) || 0;
        utilization.set(
          dateKey,
          existing + assignment.units * lane.capacityPerDay
        );
        current.setDate(current.getDate() + 1);
      }
    });

    // Mark overallocated assignments
    const updatedAssignments = lane.assignments.map((assignment) => {
      let isOverallocated = false;
      const current = new Date(assignment.startDate);
      while (current <= assignment.endDate) {
        const dateKey = current.toISOString().split("T")[0];
        if ((utilization.get(dateKey) || 0) > lane.capacityPerDay) {
          isOverallocated = true;
          break;
        }
        current.setDate(current.getDate() + 1);
      }
      return { ...assignment, isOverallocated };
    });

    return {
      ...lane,
      assignments: updatedAssignments,
      dailyUtilization: utilization,
    };
  });
}

export function useGanttResourceData(
  programId: string,
  startDate: Date,
  endDate: Date
) {
  const queryClient = useQueryClient();

  // Fetch resources with assignments
  const resourcesQuery = useQuery({
    queryKey: [
      "gantt-resources",
      programId,
      startDate.toISOString(),
      endDate.toISOString(),
    ],
    queryFn: async () => {
      // Get resources
      const resourcesRes = await apiClient.get<{ items: ResourceResponse[] }>(
        `/resources?program_id=${programId}`
      );
      const resources = resourcesRes.data.items;

      // Get assignments for each resource
      const resourceLanes: ResourceLane[] = await Promise.all(
        resources.map(async (resource) => {
          const assignmentsRes = await apiClient.get<{
            items: AssignmentResponse[];
          }>(
            `/resources/${resource.id}/assignments?start_date=${startDate.toISOString()}&end_date=${endDate.toISOString()}`
          );

          const assignments: AssignmentBar[] = assignmentsRes.data.items.map(
            (a) => ({
              assignmentId: a.id,
              activityId: a.activity_id,
              activityCode: a.activity?.code || "",
              activityName: a.activity?.name || "",
              startDate: new Date(
                a.start_date || a.activity?.early_start || new Date()
              ),
              endDate: new Date(
                a.finish_date || a.activity?.early_finish || new Date()
              ),
              units: parseFloat(a.units),
              isCritical: a.activity?.is_critical || false,
              isOverallocated: false, // Will be calculated
            })
          );

          return {
            resourceId: resource.id,
            resourceCode: resource.code,
            resourceName: resource.name,
            resourceType: resource.resource_type.toLowerCase() as
              | "labor"
              | "equipment"
              | "material",
            capacityPerDay: parseFloat(resource.capacity_per_day),
            assignments,
            dailyUtilization: new Map(),
          } as ResourceLane;
        })
      );

      // Calculate utilization and overallocation
      return calculateUtilization(resourceLanes);
    },
    enabled: !!programId,
  });

  // Mutation for updating assignments
  const updateAssignment = useMutation({
    mutationFn: async (change: AssignmentChange) => {
      if (change.type === "delete") {
        return apiClient.delete(`/assignments/${change.assignmentId}`);
      }
      return apiClient.patch(`/assignments/${change.assignmentId}`, {
        start_date: change.newStartDate?.toISOString(),
        finish_date: change.newEndDate?.toISOString(),
        units: change.newUnits,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gantt-resources", programId] });
    },
  });

  return {
    resourceLanes: resourcesQuery.data || [],
    isLoading: resourcesQuery.isLoading,
    error: resourcesQuery.error,
    updateAssignment: updateAssignment.mutate,
    isUpdating: updateAssignment.isPending,
    refetch: resourcesQuery.refetch,
  };
}
