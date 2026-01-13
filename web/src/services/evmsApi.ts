/**
 * API service for EVMS (Earned Value Management System) endpoints.
 */

import { apiClient } from "@/api/client";

export interface EVMSPeriod {
  id: string;
  programId: string;
  periodStart: string;
  periodEnd: string;
  periodName: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  notes: string | null;
  cumulativeBcws: string;
  cumulativeBcwp: string;
  cumulativeAcwp: string;
  costVariance: string | null;
  scheduleVariance: string | null;
  cpi: string | null;
  spi: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EVMSPeriodData {
  id: string;
  periodId: string;
  wbsId: string;
  bcws: string;
  bcwp: string;
  acwp: string;
  cumulativeBcws: string;
  cumulativeBcwp: string;
  cumulativeAcwp: string;
  cv: string;
  sv: string;
  cpi: string | null;
  spi: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EVMSPeriodWithData extends EVMSPeriod {
  periodData: EVMSPeriodData[];
}

export interface EVMSSummary {
  programId: string;
  programName: string;
  budgetAtCompletion: string;
  cumulativeBcws: string;
  cumulativeBcwp: string;
  cumulativeAcwp: string;
  costVariance: string | null;
  scheduleVariance: string | null;
  cpi: string | null;
  spi: string | null;
  estimateAtCompletion: string | null;
  estimateToComplete: string | null;
  varianceAtCompletion: string | null;
  tcpiEac: string | null;
  tcpiBac: string | null;
  percentComplete: string;
  percentSpent: string;
  latestPeriod: EVMSPeriod | null;
}

export interface EVMSPeriodListResponse {
  items: EVMSPeriod[];
  total: number;
}

export interface EVMSPeriodCreate {
  programId: string;
  periodStart: string;
  periodEnd: string;
  periodName: string;
  notes?: string | null;
}

export interface EVMSPeriodDataCreate {
  wbsId: string;
  bcws: string;
  bcwp: string;
  acwp: string;
}

/**
 * Get EVMS periods for a program.
 */
export async function getEVMSPeriods(
  programId: string,
  status?: string
): Promise<EVMSPeriodListResponse> {
  const params = new URLSearchParams({ program_id: programId });
  if (status) params.append("status", status);

  const response = await apiClient.get<EVMSPeriodListResponse>(
    `/evms/periods?${params.toString()}`
  );
  return response.data;
}

/**
 * Get a single EVMS period with its data.
 */
export async function getEVMSPeriodWithData(
  periodId: string
): Promise<EVMSPeriodWithData> {
  const response = await apiClient.get<EVMSPeriodWithData>(
    `/evms/periods/${periodId}`
  );
  return response.data;
}

/**
 * Get EVMS summary for a program.
 */
export async function getEVMSSummary(programId: string): Promise<EVMSSummary> {
  const response = await apiClient.get<EVMSSummary>(
    `/evms/summary/${programId}`
  );
  return response.data;
}

/**
 * Create a new EVMS period.
 */
export async function createEVMSPeriod(
  data: EVMSPeriodCreate
): Promise<EVMSPeriod> {
  const payload = {
    program_id: data.programId,
    period_start: data.periodStart,
    period_end: data.periodEnd,
    period_name: data.periodName,
    notes: data.notes,
  };
  const response = await apiClient.post<EVMSPeriod>("/evms/periods", payload);
  return response.data;
}

/**
 * Add period data to an EVMS period.
 */
export async function addPeriodData(
  periodId: string,
  data: EVMSPeriodDataCreate
): Promise<EVMSPeriodData> {
  const payload = {
    wbs_id: data.wbsId,
    bcws: data.bcws,
    bcwp: data.bcwp,
    acwp: data.acwp,
  };
  const response = await apiClient.post<EVMSPeriodData>(
    `/evms/periods/${periodId}/data`,
    payload
  );
  return response.data;
}

/**
 * Delete an EVMS period.
 */
export async function deleteEVMSPeriod(periodId: string): Promise<void> {
  await apiClient.delete(`/evms/periods/${periodId}`);
}
