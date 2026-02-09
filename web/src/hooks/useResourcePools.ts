/**
 * React Query hooks for Resource Pool management API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listPools,
  getPool,
  createPool,
  updatePool,
  deletePool,
  listPoolMembers,
  addPoolMember,
  removePoolMember,
  grantPoolAccess,
  getPoolAvailability,
  checkConflict,
} from "@/services/resourcePoolApi";
import type {
  ResourcePoolCreate,
  ResourcePoolUpdate,
  PoolMemberCreate,
  PoolAccessCreate,
  ConflictCheckRequest,
} from "@/types/resourcePool";

const POOLS_KEY = "resource-pools";

/**
 * Hook to fetch all accessible pools.
 */
export function useResourcePools() {
  return useQuery({
    queryKey: [POOLS_KEY],
    queryFn: () => listPools(),
  });
}

/**
 * Hook to fetch a single pool.
 */
export function useResourcePool(poolId: string) {
  return useQuery({
    queryKey: [POOLS_KEY, poolId],
    queryFn: () => getPool(poolId),
    enabled: !!poolId,
  });
}

/**
 * Hook to create a resource pool.
 */
export function useCreatePool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ResourcePoolCreate) => createPool(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POOLS_KEY] });
    },
  });
}

/**
 * Hook to update a resource pool.
 */
export function useUpdatePool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poolId, data }: { poolId: string; data: ResourcePoolUpdate }) =>
      updatePool(poolId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [POOLS_KEY] });
      queryClient.invalidateQueries({ queryKey: [POOLS_KEY, variables.poolId] });
    },
  });
}

/**
 * Hook to delete a resource pool.
 */
export function useDeletePool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (poolId: string) => deletePool(poolId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POOLS_KEY] });
    },
  });
}

/**
 * Hook to fetch pool members.
 */
export function usePoolMembers(poolId: string) {
  return useQuery({
    queryKey: [POOLS_KEY, poolId, "members"],
    queryFn: () => listPoolMembers(poolId),
    enabled: !!poolId,
  });
}

/**
 * Hook to add a pool member.
 */
export function useAddPoolMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poolId, data }: { poolId: string; data: PoolMemberCreate }) =>
      addPoolMember(poolId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [POOLS_KEY, variables.poolId, "members"],
      });
    },
  });
}

/**
 * Hook to remove a pool member.
 */
export function useRemovePoolMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poolId, memberId }: { poolId: string; memberId: string }) =>
      removePoolMember(poolId, memberId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [POOLS_KEY, variables.poolId, "members"],
      });
    },
  });
}

/**
 * Hook to grant pool access.
 */
export function useGrantPoolAccess() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ poolId, data }: { poolId: string; data: PoolAccessCreate }) =>
      grantPoolAccess(poolId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [POOLS_KEY, variables.poolId] });
    },
  });
}

/**
 * Hook to fetch pool availability.
 */
export function usePoolAvailability(
  poolId: string,
  startDate: string,
  endDate: string
) {
  return useQuery({
    queryKey: [POOLS_KEY, poolId, "availability", startDate, endDate],
    queryFn: () => getPoolAvailability(poolId, startDate, endDate),
    enabled: !!poolId && !!startDate && !!endDate,
  });
}

/**
 * Hook to check assignment conflicts.
 */
export function useCheckConflict() {
  return useMutation({
    mutationFn: (data: ConflictCheckRequest) => checkConflict(data),
  });
}
