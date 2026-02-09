import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
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
  skillApi,
} from "../skillApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

const mockSkill = {
  id: "skill-1",
  name: "Systems Engineering",
  code: "SE",
  category: "Technical",
  description: null,
  is_active: true,
  requires_certification: false,
  certification_expiry_months: null,
  program_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockResourceSkill = {
  id: "rs-1",
  resource_id: "res-1",
  skill_id: "skill-1",
  proficiency_level: 3,
  is_certified: false,
  certification_date: null,
  certification_expires_at: null,
  verified_by: null,
  verified_at: null,
  notes: null,
  skill: mockSkill,
};

const mockSkillReq = {
  id: "sr-1",
  activity_id: "act-1",
  skill_id: "skill-1",
  required_level: 2,
  is_mandatory: true,
  skill: mockSkill,
};

describe("skillApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getSkills", () => {
    it("should fetch skills without params", async () => {
      mockedGet.mockResolvedValue({ data: { items: [mockSkill], total: 1, page: 1, page_size: 20 } });

      const result = await getSkills();

      expect(mockedGet).toHaveBeenCalledWith("/skills");
      expect(result.items).toHaveLength(1);
    });

    it("should include query params", async () => {
      mockedGet.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 20 } });

      await getSkills({ program_id: "prog-1", category: "Technical" });

      expect(mockedGet).toHaveBeenCalledWith(
        "/skills?program_id=prog-1&category=Technical"
      );
    });
  });

  describe("createSkill", () => {
    it("should post skill data", async () => {
      mockedPost.mockResolvedValue({ data: mockSkill });

      const result = await createSkill({ name: "Systems Engineering", code: "SE" });

      expect(mockedPost).toHaveBeenCalledWith("/skills", { name: "Systems Engineering", code: "SE" });
      expect(result).toEqual(mockSkill);
    });
  });

  describe("updateSkill", () => {
    it("should patch skill data", async () => {
      mockedPatch.mockResolvedValue({ data: mockSkill });

      await updateSkill("skill-1", { name: "Updated Skill" });

      expect(mockedPatch).toHaveBeenCalledWith("/skills/skill-1", { name: "Updated Skill" });
    });
  });

  describe("deleteSkill", () => {
    it("should delete skill", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteSkill("skill-1");

      expect(mockedDelete).toHaveBeenCalledWith("/skills/skill-1");
    });
  });

  describe("getResourceSkills", () => {
    it("should fetch skills for a resource", async () => {
      mockedGet.mockResolvedValue({ data: [mockResourceSkill] });

      const result = await getResourceSkills("res-1");

      expect(mockedGet).toHaveBeenCalledWith("/resources/res-1/skills");
      expect(result).toHaveLength(1);
    });
  });

  describe("addResourceSkill", () => {
    it("should post resource skill assignment", async () => {
      mockedPost.mockResolvedValue({ data: mockResourceSkill });

      await addResourceSkill("res-1", { skill_id: "skill-1", proficiency_level: 3 });

      expect(mockedPost).toHaveBeenCalledWith("/resources/res-1/skills", {
        skill_id: "skill-1",
        proficiency_level: 3,
      });
    });
  });

  describe("updateResourceSkill", () => {
    it("should put updated resource skill", async () => {
      mockedPut.mockResolvedValue({ data: mockResourceSkill });

      await updateResourceSkill("res-1", "skill-1", { proficiency_level: 4 });

      expect(mockedPut).toHaveBeenCalledWith("/resources/res-1/skills/skill-1", {
        proficiency_level: 4,
      });
    });
  });

  describe("removeResourceSkill", () => {
    it("should delete resource skill", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await removeResourceSkill("res-1", "skill-1");

      expect(mockedDelete).toHaveBeenCalledWith("/resources/res-1/skills/skill-1");
    });
  });

  describe("getSkillRequirements", () => {
    it("should fetch skill requirements for activity", async () => {
      mockedGet.mockResolvedValue({ data: [mockSkillReq] });

      const result = await getSkillRequirements("act-1");

      expect(mockedGet).toHaveBeenCalledWith("/activities/act-1/skill-requirements");
      expect(result).toHaveLength(1);
    });
  });

  describe("addSkillRequirement", () => {
    it("should post skill requirement", async () => {
      mockedPost.mockResolvedValue({ data: mockSkillReq });

      await addSkillRequirement("act-1", { skill_id: "skill-1", required_level: 2 });

      expect(mockedPost).toHaveBeenCalledWith("/activities/act-1/skill-requirements", {
        skill_id: "skill-1",
        required_level: 2,
      });
    });
  });

  describe("removeSkillRequirement", () => {
    it("should delete skill requirement", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await removeSkillRequirement("act-1", "skill-1");

      expect(mockedDelete).toHaveBeenCalledWith("/activities/act-1/skill-requirements/skill-1");
    });
  });

  describe("skillApi object", () => {
    it("should export all methods", () => {
      expect(skillApi.list).toBe(getSkills);
      expect(skillApi.create).toBe(createSkill);
      expect(skillApi.update).toBe(updateSkill);
      expect(skillApi.delete).toBe(deleteSkill);
      expect(skillApi.getResourceSkills).toBe(getResourceSkills);
      expect(skillApi.addResourceSkill).toBe(addResourceSkill);
      expect(skillApi.updateResourceSkill).toBe(updateResourceSkill);
      expect(skillApi.removeResourceSkill).toBe(removeResourceSkill);
      expect(skillApi.getSkillRequirements).toBe(getSkillRequirements);
      expect(skillApi.addSkillRequirement).toBe(addSkillRequirement);
      expect(skillApi.removeSkillRequirement).toBe(removeSkillRequirement);
    });
  });
});
