/**
 * API service for WBS (Work Breakdown Structure) endpoints.
 */

import { apiClient } from "@/api/client";
import type { WBSElement, WBSElementTree } from "@/types";

export interface WBSElementCreate {
  programId: string;
  parentId?: string | null;
  wbsCode: string;
  name: string;
  description?: string | null;
  budgetedCost?: string;
  isControlAccount?: boolean;
}

export interface WBSElementUpdate {
  name?: string;
  description?: string | null;
  budgetedCost?: string;
  isControlAccount?: boolean;
}

export interface WBSListResponse {
  items: WBSElement[];
  total: number;
}

/**
 * Get all WBS elements for a program as a flat list.
 */
export async function getWBSElements(
  programId: string
): Promise<WBSListResponse> {
  const response = await apiClient.get<WBSListResponse>(
    `/wbs?program_id=${programId}`
  );
  return response.data;
}

/**
 * Get WBS elements as a hierarchical tree structure.
 */
export async function getWBSTree(
  programId: string
): Promise<WBSElementTree[]> {
  const response = await apiClient.get<WBSElementTree[]>(
    `/wbs/tree?program_id=${programId}`
  );
  return response.data;
}

/**
 * Get a single WBS element by ID.
 */
export async function getWBSElement(elementId: string): Promise<WBSElement> {
  const response = await apiClient.get<WBSElement>(`/wbs/${elementId}`);
  return response.data;
}

/**
 * Create a new WBS element.
 */
export async function createWBSElement(
  data: WBSElementCreate
): Promise<WBSElement> {
  const payload = {
    program_id: data.programId,
    parent_id: data.parentId,
    wbs_code: data.wbsCode,
    name: data.name,
    description: data.description,
    budgeted_cost: data.budgetedCost,
    is_control_account: data.isControlAccount,
  };
  const response = await apiClient.post<WBSElement>("/wbs", payload);
  return response.data;
}

/**
 * Update an existing WBS element.
 */
export async function updateWBSElement(
  elementId: string,
  data: WBSElementUpdate
): Promise<WBSElement> {
  const payload: Record<string, unknown> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.description !== undefined) payload.description = data.description;
  if (data.budgetedCost !== undefined) payload.budgeted_cost = data.budgetedCost;
  if (data.isControlAccount !== undefined)
    payload.is_control_account = data.isControlAccount;

  const response = await apiClient.patch<WBSElement>(
    `/wbs/${elementId}`,
    payload
  );
  return response.data;
}

/**
 * Delete a WBS element and all its children.
 */
export async function deleteWBSElement(elementId: string): Promise<void> {
  await apiClient.delete(`/wbs/${elementId}`);
}
