/**
 * React Query hooks for CPR Report API.
 */

import { useQuery } from "@tanstack/react-query";
import {
  getCPRFormat1,
  getCPRFormat3,
  getCPRFormat5,
  getReportAuditTrail,
} from "@/services/reportApi";

const REPORTS_KEY = "reports";

export function useCPRFormat1(programId: string, periodId?: string) {
  return useQuery({
    queryKey: [REPORTS_KEY, "format1", programId, periodId],
    queryFn: () => getCPRFormat1(programId, periodId),
    enabled: !!programId,
  });
}

export function useCPRFormat3(programId: string) {
  return useQuery({
    queryKey: [REPORTS_KEY, "format3", programId],
    queryFn: () => getCPRFormat3(programId),
    enabled: !!programId,
  });
}

export function useCPRFormat5(programId: string) {
  return useQuery({
    queryKey: [REPORTS_KEY, "format5", programId],
    queryFn: () => getCPRFormat5(programId),
    enabled: !!programId,
  });
}

export function useReportAuditTrail(programId: string) {
  return useQuery({
    queryKey: [REPORTS_KEY, "audit", programId],
    queryFn: () => getReportAuditTrail(programId),
    enabled: !!programId,
  });
}
