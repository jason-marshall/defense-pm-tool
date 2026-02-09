/**
 * API service for Program management endpoints.
 */

import { apiClient } from "@/api/client";
import type {
  Program,
  ProgramCreate,
  ProgramUpdate,
  ProgramListResponse,
} from "@/types/program";

export async function getPrograms(
  params?: { page?: number; page_size?: number; status?: string }
): Promise<ProgramListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.append("page", String(params.page));
  if (params?.page_size) searchParams.append("page_size", String(params.page_size));
  if (params?.status) searchParams.append("status", params.status);
  const query = searchParams.toString();
  const response = await apiClient.get<ProgramListResponse>(
    `/programs${query ? `?${query}` : ""}`
  );
  return response.data;
}

export async function getProgram(id: string): Promise<Program> {
  const response = await apiClient.get<Program>(`/programs/${id}`);
  return response.data;
}

export async function createProgram(data: ProgramCreate): Promise<Program> {
  const response = await apiClient.post<Program>("/programs", data);
  return response.data;
}

export async function updateProgram(
  id: string,
  data: ProgramUpdate
): Promise<Program> {
  const response = await apiClient.patch<Program>(`/programs/${id}`, data);
  return response.data;
}

export async function deleteProgram(id: string): Promise<void> {
  await apiClient.delete(`/programs/${id}`);
}

export const programApi = {
  list: getPrograms,
  get: getProgram,
  create: createProgram,
  update: updateProgram,
  delete: deleteProgram,
};
