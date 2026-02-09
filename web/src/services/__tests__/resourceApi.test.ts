import { describe, it, expect, vi, beforeEach } from "vitest";
import { ResourceType } from "@/types/resource";

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
  getResources,
  getResource,
  createResource,
  updateResource,
  deleteResource,
  resourceApi,
} from "../resourceApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

const mockResource = {
  id: "res-001",
  program_id: "prog-001",
  name: "Senior Engineer",
  code: "SE-001",
  resource_type: ResourceType.LABOR,
  capacity_per_day: 8,
  cost_rate: 150.0,
  effective_date: "2026-01-01",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockListResponse = {
  items: [mockResource],
  total: 1,
  page: 1,
  page_size: 50,
  pages: 1,
};

describe("resourceApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getResources", () => {
    it("should fetch resources with only programId", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      const result = await getResources("prog-001");

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources?program_id=prog-001"
      );
      expect(result).toEqual(mockListResponse);
    });

    it("should include resource_type filter when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getResources("prog-001", { resource_type: "LABOR" });

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources?program_id=prog-001&resource_type=LABOR"
      );
    });

    it("should include is_active filter when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getResources("prog-001", { is_active: true });

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources?program_id=prog-001&is_active=true"
      );
    });

    it("should include is_active=false filter", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getResources("prog-001", { is_active: false });

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources?program_id=prog-001&is_active=false"
      );
    });

    it("should include both filters when provided", async () => {
      mockedGet.mockResolvedValue({ data: mockListResponse });

      await getResources("prog-001", {
        resource_type: "EQUIPMENT",
        is_active: true,
      });

      expect(mockedGet).toHaveBeenCalledWith(
        "/resources?program_id=prog-001&resource_type=EQUIPMENT&is_active=true"
      );
    });

    it("should propagate errors", async () => {
      const error = new Error("Network error");
      mockedGet.mockRejectedValue(error);

      await expect(getResources("prog-001")).rejects.toThrow("Network error");
    });
  });

  describe("getResource", () => {
    it("should fetch a single resource by id", async () => {
      mockedGet.mockResolvedValue({ data: mockResource });

      const result = await getResource("res-001");

      expect(mockedGet).toHaveBeenCalledWith("/resources/res-001");
      expect(result).toEqual(mockResource);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getResource("bad-id")).rejects.toThrow("Not found");
    });
  });

  describe("createResource", () => {
    it("should post resource data to /resources", async () => {
      mockedPost.mockResolvedValue({ data: mockResource });

      const createData = {
        program_id: "prog-001",
        name: "Senior Engineer",
        code: "SE-001",
        resource_type: ResourceType.LABOR,
        capacity_per_day: 8,
        cost_rate: 150.0,
        effective_date: "2026-01-01",
        is_active: true,
      };

      const result = await createResource(createData);

      expect(mockedPost).toHaveBeenCalledWith("/resources", {
        program_id: "prog-001",
        name: "Senior Engineer",
        code: "SE-001",
        resource_type: "LABOR",
        capacity_per_day: 8,
        cost_rate: 150.0,
        effective_date: "2026-01-01",
        is_active: true,
      });
      expect(result).toEqual(mockResource);
    });

    it("should handle optional fields as undefined", async () => {
      mockedPost.mockResolvedValue({ data: mockResource });

      const createData = {
        program_id: "prog-001",
        name: "Crane",
        code: "CR-001",
        resource_type: ResourceType.EQUIPMENT,
      };

      await createResource(createData);

      expect(mockedPost).toHaveBeenCalledWith("/resources", {
        program_id: "prog-001",
        name: "Crane",
        code: "CR-001",
        resource_type: "EQUIPMENT",
        capacity_per_day: undefined,
        cost_rate: undefined,
        effective_date: undefined,
        is_active: undefined,
      });
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Validation error"));

      await expect(
        createResource({
          program_id: "prog-001",
          name: "",
          code: "",
          resource_type: ResourceType.LABOR,
        })
      ).rejects.toThrow("Validation error");
    });
  });

  describe("updateResource", () => {
    it("should put partial update data", async () => {
      const updated = { ...mockResource, name: "Lead Engineer" };
      mockedPut.mockResolvedValue({ data: updated });

      const result = await updateResource("res-001", { name: "Lead Engineer" });

      expect(mockedPut).toHaveBeenCalledWith("/resources/res-001", {
        name: "Lead Engineer",
      });
      expect(result).toEqual(updated);
    });

    it("should include only defined fields in payload", async () => {
      mockedPut.mockResolvedValue({ data: mockResource });

      await updateResource("res-001", {
        capacity_per_day: 6,
        is_active: false,
      });

      expect(mockedPut).toHaveBeenCalledWith("/resources/res-001", {
        capacity_per_day: 6,
        is_active: false,
      });
    });

    it("should send empty payload when no fields provided", async () => {
      mockedPut.mockResolvedValue({ data: mockResource });

      await updateResource("res-001", {});

      expect(mockedPut).toHaveBeenCalledWith("/resources/res-001", {});
    });

    it("should include all fields when all are provided", async () => {
      mockedPut.mockResolvedValue({ data: mockResource });

      await updateResource("res-001", {
        name: "Updated",
        code: "UPD-001",
        resource_type: ResourceType.MATERIAL,
        capacity_per_day: 100,
        cost_rate: 25.0,
        effective_date: "2026-06-01",
        is_active: false,
      });

      expect(mockedPut).toHaveBeenCalledWith("/resources/res-001", {
        name: "Updated",
        code: "UPD-001",
        resource_type: ResourceType.MATERIAL,
        capacity_per_day: 100,
        cost_rate: 25.0,
        effective_date: "2026-06-01",
        is_active: false,
      });
    });

    it("should propagate errors", async () => {
      mockedPut.mockRejectedValue(new Error("Conflict"));

      await expect(
        updateResource("res-001", { name: "Dup" })
      ).rejects.toThrow("Conflict");
    });
  });

  describe("deleteResource", () => {
    it("should send delete request with correct id", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deleteResource("res-001");

      expect(mockedDelete).toHaveBeenCalledWith("/resources/res-001");
    });

    it("should return void", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      const result = await deleteResource("res-001");

      expect(result).toBeUndefined();
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Forbidden"));

      await expect(deleteResource("res-001")).rejects.toThrow("Forbidden");
    });
  });

  describe("resourceApi object", () => {
    it("should export list as getResources", () => {
      expect(resourceApi.list).toBe(getResources);
    });

    it("should export get as getResource", () => {
      expect(resourceApi.get).toBe(getResource);
    });

    it("should export create as createResource", () => {
      expect(resourceApi.create).toBe(createResource);
    });

    it("should export update as updateResource", () => {
      expect(resourceApi.update).toBe(updateResource);
    });

    it("should export delete as deleteResource", () => {
      expect(resourceApi.delete).toBe(deleteResource);
    });
  });
});
