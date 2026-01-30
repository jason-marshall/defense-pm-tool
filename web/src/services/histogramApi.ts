/**
 * API service for Resource Histogram endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  ResourceHistogramData,
  ProgramHistogramResponse,
} from "@/types/histogram";

/**
 * Get histogram data for a single resource.
 */
export async function getResourceHistogram(
  resourceId: string,
  startDate: string,
  endDate: string,
  granularity: string = "daily"
): Promise<ResourceHistogramData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    granularity,
  });
  const response = await apiClient.get<ResourceHistogramData>(
    `/resources/${resourceId}/histogram?${params.toString()}`
  );
  return response.data;
}

/**
 * Get histogram data for all resources in a program.
 */
export async function getProgramHistogram(
  programId: string,
  startDate?: string,
  endDate?: string
): Promise<ProgramHistogramResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);

  const url = `/programs/${programId}/histogram${params.toString() ? `?${params.toString()}` : ""}`;
  const response = await apiClient.get<ProgramHistogramResponse>(url);
  return response.data;
}

export const histogramApi = {
  getResourceHistogram,
  getProgramHistogram,
};
