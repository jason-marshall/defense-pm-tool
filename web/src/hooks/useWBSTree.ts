/**
 * React Query hooks for WBS (Work Breakdown Structure) API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getWBSTree,
  getWBSElements,
  getWBSElement,
  createWBSElement,
  updateWBSElement,
  deleteWBSElement,
  type WBSElementCreate,
  type WBSElementUpdate,
} from "@/services/wbsApi";

const WBS_KEY = "wbs";
const WBS_TREE_KEY = "wbs-tree";

/**
 * Hook to fetch WBS tree for a program.
 */
export function useWBSTree(programId: string) {
  return useQuery({
    queryKey: [WBS_TREE_KEY, programId],
    queryFn: () => getWBSTree(programId),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch flat list of WBS elements for a program.
 */
export function useWBSElements(programId: string) {
  return useQuery({
    queryKey: [WBS_KEY, "list", programId],
    queryFn: () => getWBSElements(programId),
    enabled: !!programId,
  });
}

/**
 * Hook to fetch a single WBS element.
 */
export function useWBSElement(elementId: string) {
  return useQuery({
    queryKey: [WBS_KEY, elementId],
    queryFn: () => getWBSElement(elementId),
    enabled: !!elementId,
  });
}

/**
 * Hook to create a new WBS element.
 */
export function useCreateWBSElement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WBSElementCreate) => createWBSElement(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [WBS_KEY] });
      queryClient.invalidateQueries({
        queryKey: [WBS_TREE_KEY, variables.programId],
      });
    },
  });
}

/**
 * Hook to update a WBS element.
 */
export function useUpdateWBSElement(programId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      elementId,
      data,
    }: {
      elementId: string;
      data: WBSElementUpdate;
    }) => updateWBSElement(elementId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [WBS_KEY] });
      queryClient.invalidateQueries({ queryKey: [WBS_KEY, variables.elementId] });
      queryClient.invalidateQueries({ queryKey: [WBS_TREE_KEY, programId] });
    },
  });
}

/**
 * Hook to delete a WBS element.
 */
export function useDeleteWBSElement(programId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (elementId: string) => deleteWBSElement(elementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [WBS_KEY] });
      queryClient.invalidateQueries({ queryKey: [WBS_TREE_KEY, programId] });
    },
  });
}
