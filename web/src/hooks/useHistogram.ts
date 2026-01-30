/**
 * React Query hooks for Resource Histogram API.
 */

import { useQuery } from "@tanstack/react-query";
import {
  getResourceHistogram,
  getProgramHistogram,
} from "@/services/histogramApi";

const HISTOGRAM_KEY = "histogram";

/**
 * Hook to fetch histogram data for a single resource.
 */
export function useResourceHistogram(
  resourceId: string,
  startDate: string,
  endDate: string,
  granularity: string = "daily"
) {
  return useQuery({
    queryKey: [HISTOGRAM_KEY, "resource", resourceId, startDate, endDate, granularity],
    queryFn: () => getResourceHistogram(resourceId, startDate, endDate, granularity),
    enabled: !!resourceId && !!startDate && !!endDate,
  });
}

/**
 * Hook to fetch histogram data for all resources in a program.
 */
export function useProgramHistogram(
  programId: string,
  startDate?: string,
  endDate?: string
) {
  return useQuery({
    queryKey: [HISTOGRAM_KEY, "program", programId, startDate, endDate],
    queryFn: () => getProgramHistogram(programId, startDate, endDate),
    enabled: !!programId,
  });
}
