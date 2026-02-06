import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getResourceAssignments,
  getActivityAssignments,
  createAssignment,
  updateAssignment,
  deleteAssignment,
  assignmentApi,
} from "../assignmentApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

const mockAssignment = {
  id: "asgn-001",
  activity_id: "act-001",
  resource_id: "res-001",
  units: 1.0,
  start_date: "2026-03-01",
  finish_date: "2026-03-15",
  resource: {
    id: "res-001",
    code: "SE-001",
    name: "Senior Engineer",
    resource_type: "LABOR",
  },
};

const mockAssignment2 = {
  id: "asgn-002",
  activity_id: "act-002",
  resource_id: "res-001",
  units: 0.5,
  start_date: "2026-04-01",
  finish_date: null,
};

describe("assignmentApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getResourceAssignments", () => {
    it("should fetch assignments for a resource", async () => {
      const assignments = [mockAssignment, mockAssignment2];
      mockedGet.mockResolvedValue({ data: assignments });

      const result = await getResourceAssignments("res-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources/res-001/assignments"
      );
      expect(result).toEqual(assignments);
    });

    it("should return empty array when no assignments", async () => {
      mockedGet.mockResolvedValue({ data: [] });

      const result = await getResourceAssignments("res-999");

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources/res-999/assignments"
      );
      expect(result).toEqual([]);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getResourceAssignments("bad-id")).rejects.toThrow(
        "Not found"
      );
    });
  });

  describe("getActivityAssignments", () => {
    it("should fetch assignments for an activity", async () => {
      const assignments = [mockAssignment];
      mockedGet.mockResolvedValue({ data: assignments });

      const result = await getActivityAssignments("act-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/activities/act-001/assignments"
      );
      expect(result).toEqual(assignments);
    });

    it("should return empty array when no assignments", async () => {
      mockedGet.mockResolvedValue({ data: [] });

      const result = await getActivityAssignments("act-999");

      expect(mockedGet).toHaveBeenCalledWith(
        "/activities/act-999/assignments"
      );
      expect(result).toEqual([]);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getActivityAssignments("act-bad")).rejects.toThrow(
        "Server error"
      );
    });
  });

  describe("createAssignment", () => {
    it("should post assignment data with all fields", async () => {
      mockedPost.mockResolvedValue({ data: mockAssignment });

      const createData = {
        activity_id: "act-001",
        resource_id: "res-001",
        units: 1.0,
        start_date: "2026-03-01",
        finish_date: "2026-03-15",
      };

      const result = await createAssignment("res-001", createData);

      expect(mockedPost).toHaveBeenCalledWith(
        "/resources/res-001/assignments",
        {
          activity_id: "act-001",
          resource_id: "res-001",
          units: 1.0,
          start_date: "2026-03-01",
          finish_date: "2026-03-15",
        }
      );
      expect(result).toEqual(mockAssignment);
    });

    it("should handle optional fields as undefined", async () => {
      mockedPost.mockResolvedValue({ data: mockAssignment });

      const createData = {
        activity_id: "act-001",
        resource_id: "res-001",
      };

      await createAssignment("res-001", createData);

      expect(mockedPost).toHaveBeenCalledWith(
        "/resources/res-001/assignments",
        {
          activity_id: "act-001",
          resource_id: "res-001",
          units: undefined,
          start_date: undefined,
          finish_date: undefined,
        }
      );
    });

    it("should use the resourceId parameter in the URL", async () => {
      mockedPost.mockResolvedValue({ data: mockAssignment });

      await createAssignment("res-abc", {
        activity_id: "act-001",
        resource_id: "res-abc",
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/resources/res-abc/assignments",
        expect.any(Object)
      );
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Duplicate assignment"));

      await expect(
        createAssignment("res-001", {
          activity_id: "act-001",
          resource_id: "res-001",
        })
      ).rejects.toThrow("Duplicate assignment");
    });
  });

  describe("updateAssignment", () => {
    it("should put partial update data to correct URL", async () => {
      const updated = { ...mockAssignment, units: 0.75 };
      mockedPut.mockResolvedValue({ data: updated });

      const result = await updateAssignment("asgn-001", { units: 0.75 });

      expect(mockedPut).toHaveBeenCalledWith("/assignments/asgn-001", {
        units: 0.75,
      });
      expect(result).toEqual(updated);
    });

    it("should include only defined fields in payload", async () => {
      mockedPut.mockResolvedValue({ data: mockAssignment });

      await updateAssignment("asgn-001", {
        start_date: "2026-04-01",
        finish_date: "2026-04-30",
      });

      expect(mockedPut).toHaveBeenCalledWith("/assignments/asgn-001", {
        start_date: "2026-04-01",
        finish_date: "2026-04-30",
      });
    });

    it("should send empty payload when no fields provided", async () => {
      mockedPut.mockResolvedValue({ data: mockAssignment });

      await updateAssignment("asgn-001", {});

      expect(mockedPut).toHaveBeenCalledWith("/assignments/asgn-001", {});
    });

    it("should include all fields when all are provided", async () => {
      mockedPut.mockResolvedValue({ data: mockAssignment });

      await updateAssignment("asgn-001", {
        units: 2.0,
        start_date: "2026-05-01",
        finish_date: "2026-05-31",
      });

      expect(mockedPut).toHaveBeenCalledWith("/assignments/asgn-001", {
        units: 2.0,
        start_date: "2026-05-01",
        finish_date: "2026-05-31",
      });
    });

    it("should propagate errors", async () => {
      mockedPut.mockRejectedValue(new Error("Not found"));

      await expect(
        updateAssignment("bad-id", { units: 1 })
      ).rejects.toThrow("Not found");
    });
  });

  describe("deleteAssignment", () => {
    it("should send delete request with correct id", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteAssignment("asgn-001");

      expect(mockedDelete).toHaveBeenCalledWith("/assignments/asgn-001");
    });

    it("should return void", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      const result = await deleteAssignment("asgn-001");

      expect(result).toBeUndefined();
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteAssignment("asgn-001")).rejects.toThrow("Forbidden");
    });
  });

  describe("assignmentApi object", () => {
    it("should export listByResource as getResourceAssignments", () => {
      expect(assignmentApi.listByResource).toBe(getResourceAssignments);
    });

    it("should export listByActivity as getActivityAssignments", () => {
      expect(assignmentApi.listByActivity).toBe(getActivityAssignments);
    });

    it("should export create as createAssignment", () => {
      expect(assignmentApi.create).toBe(createAssignment);
    });

    it("should export update as updateAssignment", () => {
      expect(assignmentApi.update).toBe(updateAssignment);
    });

    it("should export delete as deleteAssignment", () => {
      expect(assignmentApi.delete).toBe(deleteAssignment);
    });
  });
});
