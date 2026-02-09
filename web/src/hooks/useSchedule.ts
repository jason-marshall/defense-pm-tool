/**
 * React Query hooks for Schedule (CPM) API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { calculateSchedule, getScheduleResults } from "@/services/scheduleApi";

const SCHEDULE_KEY = "schedule";

export function useScheduleResults(programId: string) {
  return useQuery({
    queryKey: [SCHEDULE_KEY, programId],
    queryFn: () => getScheduleResults(programId),
    enabled: !!programId,
  });
}

export function useCalculateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (programId: string) => calculateSchedule(programId),
    onSuccess: (_, programId) => {
      queryClient.invalidateQueries({ queryKey: [SCHEDULE_KEY, programId] });
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}
