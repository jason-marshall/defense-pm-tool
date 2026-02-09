/**
 * API service for Schedule (CPM) endpoints.
 */

import { apiClient } from "@/api/client";
import type { ScheduleCalculationResponse } from "@/types/schedule";

export async function calculateSchedule(
  programId: string
): Promise<ScheduleCalculationResponse> {
  const response = await apiClient.post<ScheduleCalculationResponse>(
    `/schedule/calculate`,
    { program_id: programId }
  );
  return response.data;
}

export async function getScheduleResults(
  programId: string
): Promise<ScheduleCalculationResponse> {
  const response = await apiClient.get<ScheduleCalculationResponse>(
    `/schedule/${programId}`
  );
  return response.data;
}

export const scheduleApi = {
  calculate: calculateSchedule,
  getResults: getScheduleResults,
};
