import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useSkills,
  useCreateSkill,
  useDeleteSkill,
  useResourceSkills,
  useAddResourceSkill,
  useRemoveResourceSkill,
  useSkillRequirements,
  useAddSkillRequirement,
  useRemoveSkillRequirement,
} from "./useSkills";

vi.mock("@/services/skillApi", () => ({
  getSkills: vi.fn(),
  createSkill: vi.fn(),
  updateSkill: vi.fn(),
  deleteSkill: vi.fn(),
  getResourceSkills: vi.fn(),
  addResourceSkill: vi.fn(),
  updateResourceSkill: vi.fn(),
  removeResourceSkill: vi.fn(),
  getSkillRequirements: vi.fn(),
  addSkillRequirement: vi.fn(),
  removeSkillRequirement: vi.fn(),
}));

import {
  getSkills,
  createSkill,
  deleteSkill,
  getResourceSkills,
  addResourceSkill,
  removeResourceSkill,
  getSkillRequirements,
  addSkillRequirement,
  removeSkillRequirement,
} from "@/services/skillApi";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(QueryClientProvider, { client: queryClient }, children);

describe("useSkills", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches skills", async () => {
    vi.mocked(getSkills).mockResolvedValue({ items: [], total: 0 });

    const { result } = renderHook(() => useSkills(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSkills).toHaveBeenCalledWith(undefined);
  });
});

describe("useCreateSkill", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("creates a skill", async () => {
    vi.mocked(createSkill).mockResolvedValue({ id: "skill-1", name: "Python" });

    const { result } = renderHook(() => useCreateSkill(), { wrapper });

    result.current.mutate({ name: "Python", category: "Engineering" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(createSkill).toHaveBeenCalled();
  });
});

describe("useDeleteSkill", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("deletes a skill", async () => {
    vi.mocked(deleteSkill).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteSkill(), { wrapper });

    result.current.mutate("skill-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(deleteSkill).toHaveBeenCalledWith("skill-1");
  });
});

describe("useResourceSkills", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches resource skills", async () => {
    vi.mocked(getResourceSkills).mockResolvedValue([]);

    const { result } = renderHook(() => useResourceSkills("res-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getResourceSkills).toHaveBeenCalledWith("res-1");
  });

  it("does not fetch when resourceId is empty", () => {
    renderHook(() => useResourceSkills(""), { wrapper });
    expect(getResourceSkills).not.toHaveBeenCalled();
  });
});

describe("useAddResourceSkill", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("adds a skill to a resource", async () => {
    vi.mocked(addResourceSkill).mockResolvedValue({ id: "rs-1" });

    const { result } = renderHook(() => useAddResourceSkill(), { wrapper });

    result.current.mutate({
      resourceId: "res-1",
      data: { skill_id: "skill-1", proficiency_level: 3 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addResourceSkill).toHaveBeenCalled();
  });
});

describe("useRemoveResourceSkill", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("removes a skill from a resource", async () => {
    vi.mocked(removeResourceSkill).mockResolvedValue(undefined);

    const { result } = renderHook(() => useRemoveResourceSkill(), { wrapper });

    result.current.mutate({ resourceId: "res-1", skillId: "skill-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removeResourceSkill).toHaveBeenCalledWith("res-1", "skill-1");
  });
});

describe("useSkillRequirements", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("fetches skill requirements for an activity", async () => {
    vi.mocked(getSkillRequirements).mockResolvedValue([]);

    const { result } = renderHook(() => useSkillRequirements("act-1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(getSkillRequirements).toHaveBeenCalledWith("act-1");
  });

  it("does not fetch when activityId is empty", () => {
    renderHook(() => useSkillRequirements(""), { wrapper });
    expect(getSkillRequirements).not.toHaveBeenCalled();
  });
});

describe("useAddSkillRequirement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("adds a skill requirement", async () => {
    vi.mocked(addSkillRequirement).mockResolvedValue({ id: "req-1" });

    const { result } = renderHook(() => useAddSkillRequirement(), { wrapper });

    result.current.mutate({
      activityId: "act-1",
      data: { skill_id: "skill-1", min_proficiency: 2 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(addSkillRequirement).toHaveBeenCalled();
  });
});

describe("useRemoveSkillRequirement", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("removes a skill requirement", async () => {
    vi.mocked(removeSkillRequirement).mockResolvedValue(undefined);

    const { result } = renderHook(() => useRemoveSkillRequirement(), { wrapper });

    result.current.mutate({ activityId: "act-1", skillId: "skill-1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(removeSkillRequirement).toHaveBeenCalledWith("act-1", "skill-1");
  });
});
