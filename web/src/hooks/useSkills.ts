/**
 * React Query hooks for Skills, Resource Skills, and Skill Requirements.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSkills,
  createSkill,
  updateSkill,
  deleteSkill,
  getResourceSkills,
  addResourceSkill,
  updateResourceSkill,
  removeResourceSkill,
  getSkillRequirements,
  addSkillRequirement,
  removeSkillRequirement,
} from "@/services/skillApi";
import type {
  SkillCreate,
  SkillUpdate,
  ResourceSkillCreate,
  ResourceSkillUpdate,
  SkillRequirementCreate,
} from "@/types/skill";

const SKILLS_KEY = "skills";
const RESOURCE_SKILLS_KEY = "resource-skills";
const SKILL_REQUIREMENTS_KEY = "skill-requirements";

// === Skill Hooks ===

export function useSkills(params?: {
  program_id?: string;
  category?: string;
  is_active?: boolean;
  page?: number;
}) {
  return useQuery({
    queryKey: [SKILLS_KEY, params],
    queryFn: () => getSkills(params),
  });
}

export function useCreateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillCreate) => createSkill(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] });
    },
  });
}

export function useUpdateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SkillUpdate }) => updateSkill(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] });
    },
  });
}

export function useDeleteSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSkill(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SKILLS_KEY] });
    },
  });
}

// === Resource Skill Hooks ===

export function useResourceSkills(resourceId: string) {
  return useQuery({
    queryKey: [RESOURCE_SKILLS_KEY, resourceId],
    queryFn: () => getResourceSkills(resourceId),
    enabled: !!resourceId,
  });
}

export function useAddResourceSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      resourceId,
      data,
    }: {
      resourceId: string;
      data: ResourceSkillCreate;
    }) => addResourceSkill(resourceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [RESOURCE_SKILLS_KEY, variables.resourceId],
      });
    },
  });
}

export function useUpdateResourceSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      resourceId,
      skillId,
      data,
    }: {
      resourceId: string;
      skillId: string;
      data: ResourceSkillUpdate;
    }) => updateResourceSkill(resourceId, skillId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [RESOURCE_SKILLS_KEY, variables.resourceId],
      });
    },
  });
}

export function useRemoveResourceSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      resourceId,
      skillId,
    }: {
      resourceId: string;
      skillId: string;
    }) => removeResourceSkill(resourceId, skillId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [RESOURCE_SKILLS_KEY, variables.resourceId],
      });
    },
  });
}

// === Skill Requirement Hooks ===

export function useSkillRequirements(activityId: string) {
  return useQuery({
    queryKey: [SKILL_REQUIREMENTS_KEY, activityId],
    queryFn: () => getSkillRequirements(activityId),
    enabled: !!activityId,
  });
}

export function useAddSkillRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      activityId,
      data,
    }: {
      activityId: string;
      data: SkillRequirementCreate;
    }) => addSkillRequirement(activityId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [SKILL_REQUIREMENTS_KEY, variables.activityId],
      });
    },
  });
}

export function useRemoveSkillRequirement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      activityId,
      skillId,
    }: {
      activityId: string;
      skillId: string;
    }) => removeSkillRequirement(activityId, skillId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: [SKILL_REQUIREMENTS_KEY, variables.activityId],
      });
    },
  });
}
