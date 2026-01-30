/**
 * React Query hooks for Resource Leveling API.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  previewLeveling,
  runLeveling,
  applyLeveling,
} from "@/services/levelingApi";
import type { LevelingOptions } from "@/types/leveling";

/**
 * Hook to run leveling algorithm.
 */
export function useRunLeveling() {
  return useMutation({
    mutationFn: ({
      programId,
      options,
    }: {
      programId: string;
      options: Partial<LevelingOptions>;
    }) => runLeveling(programId, options),
  });
}

/**
 * Hook to preview leveling without applying.
 */
export function usePreviewLeveling() {
  return useMutation({
    mutationFn: ({
      programId,
      options,
    }: {
      programId: string;
      options?: Partial<LevelingOptions>;
    }) => previewLeveling(programId, options),
  });
}

/**
 * Hook to apply selected leveling shifts.
 */
export function useApplyLeveling() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      programId,
      shiftIds,
    }: {
      programId: string;
      shiftIds: string[];
    }) => applyLeveling(programId, shiftIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      queryClient.invalidateQueries({ queryKey: ["histogram"] });
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
      queryClient.invalidateQueries({ queryKey: ["resources"] });
    },
  });
}
