/**
 * React Query hooks for Programs API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getPrograms,
  getProgram,
  createProgram,
  updateProgram,
  deleteProgram,
} from "@/services/programApi";
import type { ProgramCreate, ProgramUpdate } from "@/types/program";

const PROGRAMS_KEY = "programs";

export function usePrograms(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: [PROGRAMS_KEY, params],
    queryFn: () => getPrograms(params),
  });
}

export function useProgram(id: string) {
  return useQuery({
    queryKey: [PROGRAMS_KEY, id],
    queryFn: () => getProgram(id),
    enabled: !!id,
  });
}

export function useCreateProgram() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProgramCreate) => createProgram(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
    },
  });
}

export function useUpdateProgram() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProgramUpdate }) =>
      updateProgram(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY, variables.id] });
    },
  });
}

export function useDeleteProgram() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteProgram(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
    },
  });
}
