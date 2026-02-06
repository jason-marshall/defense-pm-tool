import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import {
  getWBSElements,
  getWBSTree,
  getWBSElement,
  createWBSElement,
  updateWBSElement,
  deleteWBSElement,
} from "../wbsApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockWBSElement = {
  id: "wbs-001",
  programId: "prog-001",
  parentId: null,
  wbsCode: "1.0",
  name: "Project Management",
  description: "Overall project management activities",
  level: 1,
  budgetedCost: "50000.00",
  isControlAccount: false,
  createdAt: "2026-01-15T00:00:00Z",
  updatedAt: null,
};

const mockChildElement = {
  id: "wbs-002",
  programId: "prog-001",
  parentId: "wbs-001",
  wbsCode: "1.1",
  name: "Planning",
  description: "Planning phase",
  level: 2,
  budgetedCost: "20000.00",
  isControlAccount: true,
  createdAt: "2026-01-15T00:00:00Z",
  updatedAt: null,
};

const mockListResponse = {
  items: [mockWBSElement, mockChildElement],
  total: 2,
};

const mockTreeNode = {
  ...mockWBSElement,
  children: [
    {
      ...mockChildElement,
      children: [],
    },
  ],
};

describe("wbsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getWBSElements", () => {
    it("should fetch WBS elements for a program", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getWBSElements("prog-001");

      expect(mockedGet).toHaveBeenCalledWith("/wbs?program_id=prog-001");
      expect(result).toEqual(mockListResponse);
    });

    it("should return items and total from response", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getWBSElements("prog-001");

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it("should handle empty list response", async () => {
      const emptyResponse = { items: [], total: 0 };
      mockedGet.mockResolvedValue({ data: emptyResponse });

      const result = await getWBSElements("prog-999");

      expect(mockedGet).toHaveBeenCalledWith("/wbs?program_id=prog-999");
      expect(result.items).toHaveLength(0);
      expect(result.total).toBe(0);
    });

    it("should construct URL with the given programId", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getWBSElements("abc-def-123");

      expect(mockedGet).toHaveBeenCalledWith("/wbs?program_id=abc-def-123");
    });

    it("should propagate errors", async () => {
      const error = new Error("Network error");
      mockedGet.mockRejectedValue(error);

      await expect(getWBSElements("prog-001")).rejects.toThrow("Network error");
    });
  });

  describe("getWBSTree", () => {
    it("should fetch WBS tree for a program", async () => {
      mockedGet.mockResolvedValue({ data: [mockTreeNode] });

      const result = await getWBSTree("prog-001");

      expect(mockedGet).toHaveBeenCalledWith("/wbs/tree?program_id=prog-001");
      expect(result).toEqual([mockTreeNode]);
    });

    it("should return an array of tree nodes", async () => {
      mockedGet.mockResolvedValue({ data: [mockTreeNode] });

      const result = await getWBSTree("prog-001");

      expect(Array.isArray(result)).toBe(true);
      expect(result).toHaveLength(1);
      expect(result[0].children).toHaveLength(1);
    });

    it("should handle empty tree", async () => {
      mockedGet.mockResolvedValue({ data: [] });

      const result = await getWBSTree("prog-001");

      expect(result).toEqual([]);
    });

    it("should construct URL with the given programId", async () => {
      mockedGet.mockResolvedValue({ data: [] });

      await getWBSTree("xyz-789");

      expect(mockedGet).toHaveBeenCalledWith("/wbs/tree?program_id=xyz-789");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getWBSTree("prog-001")).rejects.toThrow("Server error");
    });
  });

  describe("getWBSElement", () => {
    it("should fetch a single WBS element by ID", async () => {
      mockedGet.mockResolvedValue({ data: mockWBSElement });

      const result = await getWBSElement("wbs-001");

      expect(mockedGet).toHaveBeenCalledWith("/wbs/wbs-001");
      expect(result).toEqual(mockWBSElement);
    });

    it("should construct URL with the given elementId", async () => {
      mockedGet.mockResolvedValue({ data: mockChildElement });

      await getWBSElement("wbs-002");

      expect(mockedGet).toHaveBeenCalledWith("/wbs/wbs-002");
    });

    it("should return the element data directly", async () => {
      mockedGet.mockResolvedValue({ data: mockWBSElement });

      const result = await getWBSElement("wbs-001");

      expect(result.id).toBe("wbs-001");
      expect(result.name).toBe("Project Management");
    });

    it("should propagate errors for not found", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getWBSElement("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createWBSElement", () => {
    it("should post WBS element with all fields", async () => {
      mockedPost.mockResolvedValue({ data: mockWBSElement });

      const createData = {
        programId: "prog-001",
        parentId: null as string | null,
        wbsCode: "1.0",
        name: "Project Management",
        description: "Overall project management activities",
        budgetedCost: "50000.00",
        isControlAccount: false,
      };

      const result = await createWBSElement(createData);

      expect(mockedPost).toHaveBeenCalledWith("/wbs", {
        program_id: "prog-001",
        parent_id: null,
        wbs_code: "1.0",
        name: "Project Management",
        description: "Overall project management activities",
        budgeted_cost: "50000.00",
        is_control_account: false,
      });
      expect(result).toEqual(mockWBSElement);
    });

    it("should transform camelCase to snake_case in payload", async () => {
      mockedPost.mockResolvedValue({ data: mockChildElement });

      await createWBSElement({
        programId: "prog-001",
        parentId: "wbs-001",
        wbsCode: "1.1",
        name: "Planning",
        budgetedCost: "20000.00",
        isControlAccount: true,
      });

      const payload = mockedPost.mock.calls[0][1];
      expect(payload).toHaveProperty("program_id", "prog-001");
      expect(payload).toHaveProperty("parent_id", "wbs-001");
      expect(payload).toHaveProperty("wbs_code", "1.1");
      expect(payload).toHaveProperty("budgeted_cost", "20000.00");
      expect(payload).toHaveProperty("is_control_account", true);
    });

    it("should handle optional fields as undefined", async () => {
      mockedPost.mockResolvedValue({ data: mockWBSElement });

      await createWBSElement({
        programId: "prog-001",
        wbsCode: "2.0",
        name: "Engineering",
      });

      expect(mockedPost).toHaveBeenCalledWith("/wbs", {
        program_id: "prog-001",
        parent_id: undefined,
        wbs_code: "2.0",
        name: "Engineering",
        description: undefined,
        budgeted_cost: undefined,
        is_control_account: undefined,
      });
    });

    it("should send null parentId when explicitly set to null", async () => {
      mockedPost.mockResolvedValue({ data: mockWBSElement });

      await createWBSElement({
        programId: "prog-001",
        parentId: null,
        wbsCode: "1.0",
        name: "Root Element",
      });

      const payload = mockedPost.mock.calls[0][1];
      expect(payload.parent_id).toBeNull();
    });

    it("should send parentId when provided", async () => {
      mockedPost.mockResolvedValue({ data: mockChildElement });

      await createWBSElement({
        programId: "prog-001",
        parentId: "wbs-001",
        wbsCode: "1.1",
        name: "Child Element",
      });

      const payload = mockedPost.mock.calls[0][1];
      expect(payload.parent_id).toBe("wbs-001");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createWBSElement({
          programId: "prog-001",
          wbsCode: "",
          name: "",
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("updateWBSElement", () => {
    it("should patch WBS element with all fields", async () => {
      const updated = { ...mockWBSElement, name: "Updated PM" };
      mockedPatch.mockResolvedValue({ data: updated });

      const result = await updateWBSElement("wbs-001", {
        name: "Updated PM",
        description: "Updated description",
        budgetedCost: "75000.00",
        isControlAccount: true,
      });

      expect(mockedPatch).toHaveBeenCalledWith("/wbs/wbs-001", {
        name: "Updated PM",
        description: "Updated description",
        budgeted_cost: "75000.00",
        is_control_account: true,
      });
      expect(result).toEqual(updated);
    });

    it("should include only defined fields in payload", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", { name: "New Name" });

      expect(mockedPatch).toHaveBeenCalledWith("/wbs/wbs-001", {
        name: "New Name",
      });
    });

    it("should send empty payload when no fields provided", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", {});

      expect(mockedPatch).toHaveBeenCalledWith("/wbs/wbs-001", {});
    });

    it("should transform budgetedCost to budgeted_cost", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", { budgetedCost: "60000.00" });

      const payload = mockedPatch.mock.calls[0][1];
      expect(payload).toHaveProperty("budgeted_cost", "60000.00");
      expect(payload).not.toHaveProperty("budgetedCost");
    });

    it("should transform isControlAccount to is_control_account", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", { isControlAccount: true });

      const payload = mockedPatch.mock.calls[0][1];
      expect(payload).toHaveProperty("is_control_account", true);
      expect(payload).not.toHaveProperty("isControlAccount");
    });

    it("should allow setting description to null", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", { description: null });

      expect(mockedPatch).toHaveBeenCalledWith("/wbs/wbs-001", {
        description: null,
      });
    });

    it("should not include name when undefined", async () => {
      mockedPatch.mockResolvedValue({ data: mockWBSElement });

      await updateWBSElement("wbs-001", { budgetedCost: "10000.00" });

      const payload = mockedPatch.mock.calls[0][1];
      expect(payload).not.toHaveProperty("name");
    });

    it("should construct URL with the given elementId", async () => {
      mockedPatch.mockResolvedValue({ data: mockChildElement });

      await updateWBSElement("wbs-002", { name: "Updated Child" });

      expect(mockedPatch).toHaveBeenCalledWith("/wbs/wbs-002", {
        name: "Updated Child",
      });
    });

    it("should propagate errors", async () => {
      mockedPatch.mockRejectedValue(new Error("Conflict"));

      await expect(
        updateWBSElement("wbs-001", { name: "Dup" })
      ).rejects.toThrow("Conflict");
    });
  });

  describe("deleteWBSElement", () => {
    it("should send delete request with correct id", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteWBSElement("wbs-001");

      expect(mockedDelete).toHaveBeenCalledWith("/wbs/wbs-001");
    });

    it("should construct URL with the given elementId", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteWBSElement("wbs-002");

      expect(mockedDelete).toHaveBeenCalledWith("/wbs/wbs-002");
    });

    it("should return void", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      const result = await deleteWBSElement("wbs-001");

      expect(result).toBeUndefined();
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteWBSElement("wbs-001")).rejects.toThrow("Forbidden");
    });

    it("should propagate not found errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Not found"));

      await expect(deleteWBSElement("bad-id")).rejects.toThrow("Not found");
    });
  });
});
