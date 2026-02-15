import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import {
  useSkills,
  useCreateSkill,
  useUpdateSkill,
  useDeleteSkill,
  useResourceSkills,
  useAddResourceSkill,
  useUpdateResourceSkill,
  useRemoveResourceSkill,
  useSkillRequirements,
  useAddSkillRequirement,
  useRemoveSkillRequirement,
} from "./useSkills";

vi.mock("@/services/skillApi", () => ({
  getSkills: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  createSkill: vi.fn().mockResolvedValue({ id: "new-1" }),
  updateSkill: vi.fn().mockResolvedValue({ id: "skill-1" }),
  deleteSkill: vi.fn().mockResolvedValue(undefined),
  getResourceSkills: vi.fn().mockResolvedValue([]),
  addResourceSkill: vi.fn().mockResolvedValue({ id: "rs-1" }),
  updateResourceSkill: vi.fn().mockResolvedValue({ id: "rs-1" }),
  removeResourceSkill: vi.fn().mockResolvedValue(undefined),
  getSkillRequirements: vi.fn().mockResolvedValue([]),
  addSkillRequirement: vi.fn().mockResolvedValue({ id: "sr-1" }),
  removeSkillRequirement: vi.fn().mockResolvedValue(undefined),
}));

import * as api from "@/services/skillApi";

let queryClient: QueryClient;

function wrapper({ children }: { children: React.ReactNode }) {
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useSkills hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it("useSkills fetches with params", async () => {
    const { result } = renderHook(() => useSkills({ program_id: "p1" }), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getSkills).toHaveBeenCalledWith({ program_id: "p1" });
  });

  it("useCreateSkill calls createSkill", async () => {
    const { result } = renderHook(() => useCreateSkill(), { wrapper });
    await result.current.mutateAsync({ name: "X", code: "X", program_id: "p1", category: "Technical" });
    expect(api.createSkill).toHaveBeenCalled();
  });

  it("useUpdateSkill calls updateSkill", async () => {
    const { result } = renderHook(() => useUpdateSkill(), { wrapper });
    await result.current.mutateAsync({ id: "s1", data: { name: "Updated" } });
    expect(api.updateSkill).toHaveBeenCalledWith("s1", { name: "Updated" });
  });

  it("useDeleteSkill calls deleteSkill", async () => {
    const { result } = renderHook(() => useDeleteSkill(), { wrapper });
    await result.current.mutateAsync("s1");
    expect(api.deleteSkill).toHaveBeenCalledWith("s1");
  });

  it("useResourceSkills fetches when resourceId truthy", async () => {
    const { result } = renderHook(() => useResourceSkills("r1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getResourceSkills).toHaveBeenCalledWith("r1");
  });

  it("useResourceSkills disabled when resourceId empty", () => {
    const { result } = renderHook(() => useResourceSkills(""), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("useAddResourceSkill calls addResourceSkill", async () => {
    const { result } = renderHook(() => useAddResourceSkill(), { wrapper });
    await result.current.mutateAsync({
      resourceId: "r1",
      data: { skill_id: "s1", proficiency_level: 3, is_certified: false },
    });
    expect(api.addResourceSkill).toHaveBeenCalledWith("r1", { skill_id: "s1", proficiency_level: 3, is_certified: false });
  });

  it("useUpdateResourceSkill calls updateResourceSkill", async () => {
    const { result } = renderHook(() => useUpdateResourceSkill(), { wrapper });
    await result.current.mutateAsync({
      resourceId: "r1",
      skillId: "s1",
      data: { proficiency_level: 5 },
    });
    expect(api.updateResourceSkill).toHaveBeenCalledWith("r1", "s1", { proficiency_level: 5 });
  });

  it("useRemoveResourceSkill calls removeResourceSkill", async () => {
    const { result } = renderHook(() => useRemoveResourceSkill(), { wrapper });
    await result.current.mutateAsync({ resourceId: "r1", skillId: "s1" });
    expect(api.removeResourceSkill).toHaveBeenCalledWith("r1", "s1");
  });

  it("useSkillRequirements fetches when activityId truthy", async () => {
    const { result } = renderHook(() => useSkillRequirements("a1"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.getSkillRequirements).toHaveBeenCalledWith("a1");
  });

  it("useAddSkillRequirement calls addSkillRequirement", async () => {
    const { result } = renderHook(() => useAddSkillRequirement(), { wrapper });
    await result.current.mutateAsync({
      activityId: "a1",
      data: { skill_id: "s1", min_proficiency: 3 },
    });
    expect(api.addSkillRequirement).toHaveBeenCalledWith("a1", { skill_id: "s1", min_proficiency: 3 });
  });

  it("useRemoveSkillRequirement calls removeSkillRequirement", async () => {
    const { result } = renderHook(() => useRemoveSkillRequirement(), { wrapper });
    await result.current.mutateAsync({ activityId: "a1", skillId: "s1" });
    expect(api.removeSkillRequirement).toHaveBeenCalledWith("a1", "s1");
  });
});
