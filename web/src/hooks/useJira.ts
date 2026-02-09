/**
 * React Query hooks for Jira integration API.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getIntegrationByProgram,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  testConnection,
  syncWbs,
  syncActivities,
  syncProgress,
  getMappings,
  createMapping,
  deleteMapping,
  getSyncLogs,
} from "@/services/jiraApi";
import type {
  JiraIntegrationCreate,
  JiraIntegrationUpdate,
  JiraMappingCreate,
} from "@/types/jira";

const JIRA_KEY = "jira";

export function useJiraIntegration(programId: string) {
  return useQuery({
    queryKey: [JIRA_KEY, "integration", programId],
    queryFn: () => getIntegrationByProgram(programId),
    enabled: !!programId,
    retry: false,
  });
}

export function useCreateJiraIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: JiraIntegrationCreate) => createIntegration(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [JIRA_KEY, "integration", variables.program_id],
      });
    },
  });
}

export function useUpdateJiraIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      integrationId,
      data,
    }: {
      integrationId: string;
      data: JiraIntegrationUpdate;
    }) => updateIntegration(integrationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [JIRA_KEY] });
    },
  });
}

export function useDeleteJiraIntegration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (integrationId: string) => deleteIntegration(integrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [JIRA_KEY] });
    },
  });
}

export function useTestJiraConnection() {
  return useMutation({
    mutationFn: (integrationId: string) => testConnection(integrationId),
  });
}

export function useSyncJira() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      integrationId,
      type,
    }: {
      integrationId: string;
      type: "wbs" | "activities" | "progress";
    }) => {
      switch (type) {
        case "wbs":
          return syncWbs(integrationId);
        case "activities":
          return syncActivities(integrationId);
        case "progress":
          return syncProgress(integrationId);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [JIRA_KEY] });
    },
  });
}

export function useJiraMappings(integrationId: string) {
  return useQuery({
    queryKey: [JIRA_KEY, "mappings", integrationId],
    queryFn: () => getMappings(integrationId),
    enabled: !!integrationId,
  });
}

export function useCreateJiraMapping() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      integrationId,
      data,
    }: {
      integrationId: string;
      data: JiraMappingCreate;
    }) => createMapping(integrationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [JIRA_KEY, "mappings"] });
    },
  });
}

export function useDeleteJiraMapping() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mappingId: string) => deleteMapping(mappingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [JIRA_KEY, "mappings"] });
    },
  });
}

export function useJiraSyncLogs(integrationId: string, limit?: number) {
  return useQuery({
    queryKey: [JIRA_KEY, "logs", integrationId, limit],
    queryFn: () => getSyncLogs(integrationId, limit),
    enabled: !!integrationId,
  });
}
