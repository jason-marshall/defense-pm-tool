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
  resourcePoolApi,
} from "../resourcePoolApi";
import { PoolAccessLevel } from "@/types/resourcePool";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);
const mockedDelete = vi.mocked(apiClient.delete);

const mockPool = {
  id: "pool-001",
  name: "Engineering Pool",
  code: "ENG-POOL",
  description: "Shared engineering resources",
  owner_id: "user-001",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockMember = {
  id: "member-001",
  pool_id: "pool-001",
  resource_id: "res-001",
  allocation_percentage: "100.00",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

describe("resourcePoolApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("listPools", () => {
    it("should fetch all pools", async () => {
      mockedGet.mockResolvedValue({ data: [mockPool] });

      const result = await listPools();

      expect(mockedGet).toHaveBeenCalledWith("/resource-pools");
      expect(result).toEqual([mockPool]);
    });

    it("should return empty array when no pools", async () => {
      mockedGet.mockResolvedValue({ data: [] });

      const result = await listPools();

      expect(result).toEqual([]);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Unauthorized"));

      await expect(listPools()).rejects.toThrow("Unauthorized");
    });
  });

  describe("getPool", () => {
    it("should fetch pool by ID", async () => {
      mockedGet.mockResolvedValue({ data: mockPool });

      const result = await getPool("pool-001");

      expect(mockedGet).toHaveBeenCalledWith("/resource-pools/pool-001");
      expect(result).toEqual(mockPool);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getPool("invalid")).rejects.toThrow("Not found");
    });
  });

  describe("createPool", () => {
    it("should create pool with required fields", async () => {
      mockedPost.mockResolvedValue({ data: mockPool });

      const result = await createPool({ name: "Engineering Pool", code: "ENG-POOL" });

      expect(mockedPost).toHaveBeenCalledWith("/resource-pools", {
        name: "Engineering Pool",
        code: "ENG-POOL",
      });
      expect(result).toEqual(mockPool);
    });

    it("should include description when provided", async () => {
      mockedPost.mockResolvedValue({ data: mockPool });

      await createPool({
        name: "Engineering Pool",
        code: "ENG-POOL",
        description: "Shared resources",
      });

      expect(mockedPost).toHaveBeenCalledWith("/resource-pools", {
        name: "Engineering Pool",
        code: "ENG-POOL",
        description: "Shared resources",
      });
    });

    it("should not include description when undefined", async () => {
      mockedPost.mockResolvedValue({ data: mockPool });

      await createPool({ name: "Pool", code: "POOL" });

      const payload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(payload).not.toHaveProperty("description");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Duplicate code"));

      await expect(
        createPool({ name: "Pool", code: "DUP" })
      ).rejects.toThrow("Duplicate code");
    });
  });

  describe("updatePool", () => {
    it("should patch pool with name", async () => {
      mockedPatch.mockResolvedValue({ data: { ...mockPool, name: "Updated" } });

      const result = await updatePool("pool-001", { name: "Updated" });

      expect(mockedPatch).toHaveBeenCalledWith("/resource-pools/pool-001", {
        name: "Updated",
      });
      expect(result.name).toBe("Updated");
    });

    it("should only include provided fields", async () => {
      mockedPatch.mockResolvedValue({ data: mockPool });

      await updatePool("pool-001", { is_active: false });

      expect(mockedPatch).toHaveBeenCalledWith("/resource-pools/pool-001", {
        is_active: false,
      });
    });

    it("should propagate errors", async () => {
      mockedPatch.mockRejectedValue(new Error("Forbidden"));

      await expect(
        updatePool("pool-001", { name: "Test" })
      ).rejects.toThrow("Forbidden");
    });
  });

  describe("deletePool", () => {
    it("should delete pool by ID", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await deletePool("pool-001");

      expect(mockedDelete).toHaveBeenCalledWith("/resource-pools/pool-001");
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Not found"));

      await expect(deletePool("invalid")).rejects.toThrow("Not found");
    });
  });

  describe("listPoolMembers", () => {
    it("should fetch members for a pool", async () => {
      mockedGet.mockResolvedValue({ data: [mockMember] });

      const result = await listPoolMembers("pool-001");

      expect(mockedGet).toHaveBeenCalledWith("/resource-pools/pool-001/members");
      expect(result).toEqual([mockMember]);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(listPoolMembers("pool-001")).rejects.toThrow("Server error");
    });
  });

  describe("addPoolMember", () => {
    it("should add member with resource_id", async () => {
      mockedPost.mockResolvedValue({ data: mockMember });

      const result = await addPoolMember("pool-001", {
        resource_id: "res-001",
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/resource-pools/pool-001/members",
        { resource_id: "res-001" }
      );
      expect(result).toEqual(mockMember);
    });

    it("should include allocation_percentage when provided", async () => {
      mockedPost.mockResolvedValue({ data: mockMember });

      await addPoolMember("pool-001", {
        resource_id: "res-001",
        allocation_percentage: 50,
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/resource-pools/pool-001/members",
        { resource_id: "res-001", allocation_percentage: 50 }
      );
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Already a member"));

      await expect(
        addPoolMember("pool-001", { resource_id: "res-001" })
      ).rejects.toThrow("Already a member");
    });
  });

  describe("removePoolMember", () => {
    it("should remove member by ID", async () => {
      mockedDelete.mockResolvedValue({ data: undefined });

      await removePoolMember("pool-001", "member-001");

      expect(mockedDelete).toHaveBeenCalledWith(
        "/resource-pools/pool-001/members/member-001"
      );
    });

    it("should propagate errors", async () => {
      mockedDelete.mockRejectedValue(new Error("Not found"));

      await expect(
        removePoolMember("pool-001", "invalid")
      ).rejects.toThrow("Not found");
    });
  });

  describe("grantPoolAccess", () => {
    it("should grant access to a program", async () => {
      const mockAccess = {
        id: "access-001",
        pool_id: "pool-001",
        program_id: "prog-001",
        access_level: "EDITOR",
        granted_by: "user-001",
        granted_at: "2026-01-01T00:00:00Z",
      };
      mockedPost.mockResolvedValue({ data: mockAccess });

      const result = await grantPoolAccess("pool-001", {
        program_id: "prog-001",
        access_level: PoolAccessLevel.EDITOR,
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/resource-pools/pool-001/access",
        { program_id: "prog-001", access_level: "EDITOR" }
      );
      expect(result).toEqual(mockAccess);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Forbidden"));

      await expect(
        grantPoolAccess("pool-001", {
          program_id: "prog-001",
          access_level: PoolAccessLevel.VIEWER,
        })
      ).rejects.toThrow("Forbidden");
    });
  });

  describe("getPoolAvailability", () => {
    it("should fetch availability with date range", async () => {
      const mockAvailability = {
        pool_id: "pool-001",
        pool_name: "Engineering Pool",
        date_range_start: "2026-01-01",
        date_range_end: "2026-01-31",
        resources: [],
        conflict_count: 0,
        conflicts: [],
      };
      mockedGet.mockResolvedValue({ data: mockAvailability });

      const result = await getPoolAvailability(
        "pool-001",
        "2026-01-01",
        "2026-01-31"
      );

      expect(mockedGet).toHaveBeenCalledWith(
        "/resource-pools/pool-001/availability?start_date=2026-01-01&end_date=2026-01-31"
      );
      expect(result).toEqual(mockAvailability);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Bad request"));

      await expect(
        getPoolAvailability("pool-001", "invalid", "invalid")
      ).rejects.toThrow("Bad request");
    });
  });

  describe("checkConflict", () => {
    it("should post conflict check request", async () => {
      const mockConflictResult = {
        has_conflicts: false,
        conflict_count: 0,
        conflicts: [],
      };
      mockedPost.mockResolvedValue({ data: mockConflictResult });

      const result = await checkConflict({
        resource_id: "res-001",
        program_id: "prog-001",
        start_date: "2026-01-01",
        end_date: "2026-01-31",
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/resource-pools/check-conflict",
        {
          resource_id: "res-001",
          program_id: "prog-001",
          start_date: "2026-01-01",
          end_date: "2026-01-31",
        }
      );
      expect(result).toEqual(mockConflictResult);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Server error"));

      await expect(
        checkConflict({
          resource_id: "res-001",
          program_id: "prog-001",
          start_date: "2026-01-01",
          end_date: "2026-01-31",
        })
      ).rejects.toThrow("Server error");
    });
  });

  describe("resourcePoolApi object", () => {
    it("should export list as listPools", () => {
      expect(resourcePoolApi.list).toBe(listPools);
    });

    it("should export get as getPool", () => {
      expect(resourcePoolApi.get).toBe(getPool);
    });

    it("should export create as createPool", () => {
      expect(resourcePoolApi.create).toBe(createPool);
    });

    it("should export update as updatePool", () => {
      expect(resourcePoolApi.update).toBe(updatePool);
    });

    it("should export delete as deletePool", () => {
      expect(resourcePoolApi.delete).toBe(deletePool);
    });

    it("should export all eleven methods", () => {
      expect(Object.keys(resourcePoolApi)).toHaveLength(11);
    });
  });
});
