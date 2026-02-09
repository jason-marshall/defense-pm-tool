import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getActivities,
  getActivity,
  createActivity,
  updateActivity,
  deleteActivity,
  activityApi,
} from "../activityApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockActivity = {
  id: "act-1",
  program_id: "prog-1",
  wbs_id: null,
  name: "Design Review",
  code: "DR-001",
  description: null,
  duration: 10,
  remaining_duration: null,
  percent_complete: "50.00",
  budgeted_cost: "25000",
  actual_cost: "12000",
  constraint_type: null,
  constraint_date: null,
  early_start: 0,
  early_finish: 10,
  late_start: 0,
  late_finish: 10,
  total_float: 0,
  free_float: 0,
  is_critical: true,
  is_milestone: false,
  actual_start: null,
  actual_finish: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockListResponse = {
  items: [mockActivity],
  total: 1,
};

describe("activityApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getActivities", () => {
    it("should fetch activities for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getActivities("prog-1");

      expect(mockedGet).toHaveBeenCalledWith(
        "/activities?program_id=prog-1"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Network error"));

      await expect(getActivities("prog-1")).rejects.toThrow("Network error");
    });
  });

  describe("getActivity", () => {
    it("should fetch a single activity by id", async () => {
      mockedGet.mockResolvedValue({ data: mockActivity });

      const result = await getActivity("act-1");

      expect(mockedGet).toHaveBeenCalledWith("/activities/act-1");
      expect(result).toEqual(mockActivity);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getActivity("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createActivity", () => {
    it("should post activity data", async () => {
      mockedPost.mockResolvedValue({ data: mockActivity });

      const createData = {
        program_id: "prog-1",
        name: "Design Review",
        code: "DR-001",
        duration: 10,
      };

      const result = await createActivity(createData);

      expect(mockedPost).toHaveBeenCalledWith("/activities", createData);
      expect(result).toEqual(mockActivity);
    });

    it("should include optional fields when provided", async () => {
      mockedPost.mockResolvedValue({ data: mockActivity });

      const createData = {
        program_id: "prog-1",
        name: "Milestone",
        code: "MS-001",
        duration: 0,
        is_milestone: true,
        budgeted_cost: "10000",
      };

      await createActivity(createData);

      expect(mockedPost).toHaveBeenCalledWith("/activities", createData);
    });

    it("should propagate validation errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createActivity({
          program_id: "",
          name: "",
          code: "",
          duration: -1,
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("updateActivity", () => {
    it("should patch activity with partial data", async () => {
      const updated = { ...mockActivity, name: "Updated Review" };
      mockedPatch.mockResolvedValue({ data: updated });

      const result = await updateActivity("act-1", { name: "Updated Review" });

      expect(mockedPatch).toHaveBeenCalledWith("/activities/act-1", {
        name: "Updated Review",
      });
      expect(result).toEqual(updated);
    });

    it("should propagate errors", async () => {
      mockedPatch.mockRejectedValue(new Error("Conflict"));

      await expect(
        updateActivity("act-1", { name: "Dup" })
      ).rejects.toThrow("Conflict");
    });
  });

  describe("deleteActivity", () => {
    it("should send delete request", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteActivity("act-1");

      expect(mockedDelete).toHaveBeenCalledWith("/activities/act-1");
    });

    it("should return void", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      const result = await deleteActivity("act-1");

      expect(result).toBeUndefined();
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteActivity("act-1")).rejects.toThrow("Forbidden");
    });
  });

  describe("activityApi object", () => {
    it("should export list as getActivities", () => {
      expect(activityApi.list).toBe(getActivities);
    });

    it("should export get as getActivity", () => {
      expect(activityApi.get).toBe(getActivity);
    });

    it("should export create as createActivity", () => {
      expect(activityApi.create).toBe(createActivity);
    });

    it("should export update as updateActivity", () => {
      expect(activityApi.update).toBe(updateActivity);
    });

    it("should export delete as deleteActivity", () => {
      expect(activityApi.delete).toBe(deleteActivity);
    });
  });
});
