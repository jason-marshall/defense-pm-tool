/**
 * API service for CPR Report endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  CPRFormat1Report,
  CPRFormat3Report,
  CPRFormat5Report,
  ReportAuditEntry,
} from "@/types/report";

export async function getCPRFormat1(
  programId: string,
  periodId?: string
): Promise<CPRFormat1Report> {
  const params = new URLSearchParams();
  if (periodId) params.append("period_id", periodId);
  const query = params.toString();
  const response = await apiClient.get<CPRFormat1Report>(
    `/reports/cpr/format1/${programId}${query ? `?${query}` : ""}`
  );
  return response.data;
}

export async function getCPRFormat3(
  programId: string
): Promise<CPRFormat3Report> {
  const response = await apiClient.get<CPRFormat3Report>(
    `/reports/cpr/format3/${programId}`
  );
  return response.data;
}

export async function getCPRFormat5(
  programId: string
): Promise<CPRFormat5Report> {
  const response = await apiClient.get<CPRFormat5Report>(
    `/reports/cpr/format5/${programId}`
  );
  return response.data;
}

export async function downloadReportPDF(
  programId: string,
  format: string
): Promise<Blob> {
  const response = await apiClient.get(
    `/reports/cpr/${format}/${programId}/pdf`,
    { responseType: "blob" }
  );
  return response.data as Blob;
}

export async function getReportAuditTrail(
  programId: string
): Promise<ReportAuditEntry[]> {
  const response = await apiClient.get<ReportAuditEntry[]>(
    `/reports/audit/${programId}`
  );
  return response.data;
}

export const reportApi = {
  format1: getCPRFormat1,
  format3: getCPRFormat3,
  format5: getCPRFormat5,
  downloadPDF: downloadReportPDF,
  auditTrail: getReportAuditTrail,
};
