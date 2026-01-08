/**
 * React Query hooks for Programs API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { Program, ProgramCreate, PaginatedResponse } from "@/types";

const PROGRAMS_KEY = "programs";

export function usePrograms(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: [PROGRAMS_KEY, page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<Program>>(
        `/programs?page=${page}&page_size=${pageSize}`
      );
      return response.data;
    },
  });
}

export function useProgram(id: string) {
  return useQuery({
    queryKey: [PROGRAMS_KEY, id],
    queryFn: async () => {
      const response = await apiClient.get<Program>(`/programs/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateProgram() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ProgramCreate) => {
      const response = await apiClient.post<Program>("/programs", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
    },
  });
}

export function useUpdateProgram(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<ProgramCreate>) => {
      const response = await apiClient.patch<Program>(`/programs/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY, id] });
    },
  });
}

export function useDeleteProgram() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/programs/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PROGRAMS_KEY] });
    },
  });
}
