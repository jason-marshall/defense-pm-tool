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
  getActivityCost,
  getWBSCost,
  getProgramCostSummary,
  syncCostsToEVMS,
  recordCostEntry,
  costApi,
} from "../costApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockActivityCost = {
  activity_id: "act-001",
  activity_code: "ACT-001",
  activity_name: "Design Review",
  planned_cost: "5000.00",
  actual_cost: "4500.00",
  cost_variance: "500.00",
  percent_spent: "90.00",
  resource_breakdown: [
    {
      resource_id: "res-001",
      resource_name: "Engineer 1",
      resource_type: "LABOR",
      planned_cost: "3000.00",
      actual_cost: "2800.00",
    },
  ],
};

const mockProgramCostSummary = {
  program_id: "prog-001",
  total_planned_cost: "100000.00",
  total_actual_cost: "85000.00",
  total_cost_variance: "15000.00",
  labor_cost: "60000.00",
  equipment_cost: "15000.00",
  material_cost: "10000.00",
  resource_count: 5,
  activity_count: 20,
  wbs_breakdown: [],
};

const mockWBSCost = {
  wbs_id: "wbs-001",
  wbs_code: "1.1",
  wbs_name: "Phase 1",
  planned_cost: "25000.00",
  actual_cost: "20000.00",
  cost_variance: "5000.00",
  activity_count: 5,
};

describe("costApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getActivityCost", () => {
    it("should fetch activity cost by ID", async () => {
      mockedGet.mockResolvedValue({ data: mockActivityCost });

      const result = await getActivityCost("act-001");

      expect(mockedGet).toHaveBeenCalledWith("/cost/activities/act-001");
      expect(result).toEqual(mockActivityCost);
    });

    it("should return resource breakdown", async () => {
      mockedGet.mockResolvedValue({ data: mockActivityCost });

      const result = await getActivityCost("act-001");

      expect(result.resource_breakdown).toHaveLength(1);
      expect(result.resource_breakdown[0].resource_name).toBe("Engineer 1");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getActivityCost("invalid")).rejects.toThrow("Not found");
    });
  });

  describe("getWBSCost", () => {
    it("should fetch WBS cost without include_children", async () => {
      mockedGet.mockResolvedValue({ data: mockWBSCost });

      const result = await getWBSCost("wbs-001");

      expect(mockedGet).toHaveBeenCalledWith("/cost/wbs/wbs-001");
      expect(result).toEqual(mockWBSCost);
    });

    it("should append include_children when true", async () => {
      mockedGet.mockResolvedValue({ data: mockWBSCost });

      await getWBSCost("wbs-001", true);

      expect(mockedGet).toHaveBeenCalledWith(
        "/cost/wbs/wbs-001?include_children=true"
      );
    });

    it("should append include_children when false", async () => {
      mockedGet.mockResolvedValue({ data: mockWBSCost });

      await getWBSCost("wbs-001", false);

      expect(mockedGet).toHaveBeenCalledWith(
        "/cost/wbs/wbs-001?include_children=false"
      );
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Server error"));

      await expect(getWBSCost("wbs-001")).rejects.toThrow("Server error");
    });
  });

  describe("getProgramCostSummary", () => {
    it("should fetch program cost summary", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramCostSummary });

      const result = await getProgramCostSummary("prog-001");

      expect(mockedGet).toHaveBeenCalledWith("/cost/programs/prog-001");
      expect(result).toEqual(mockProgramCostSummary);
    });

    it("should return all cost fields", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramCostSummary });

      const result = await getProgramCostSummary("prog-001");

      expect(result.total_planned_cost).toBe("100000.00");
      expect(result.labor_cost).toBe("60000.00");
      expect(result.resource_count).toBe(5);
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getProgramCostSummary("prog-001")).rejects.toThrow(
        "Forbidden"
      );
    });
  });

  describe("syncCostsToEVMS", () => {
    it("should post sync request with period_id", async () => {
      const mockSync = {
        period_id: "period-001",
        acwp_updated: "85000.00",
        wbs_elements_updated: 5,
        success: true,
        warnings: [],
      };
      mockedPost.mockResolvedValue({ data: mockSync });

      const result = await syncCostsToEVMS("prog-001", "period-001");

      expect(mockedPost).toHaveBeenCalledWith(
        "/cost/programs/prog-001/evms-sync?period_id=period-001"
      );
      expect(result).toEqual(mockSync);
    });

    it("should return sync result with warnings", async () => {
      const mockSync = {
        period_id: "period-002",
        acwp_updated: "50000.00",
        wbs_elements_updated: 3,
        success: true,
        warnings: ["Missing cost data for WBS 1.2"],
      };
      mockedPost.mockResolvedValue({ data: mockSync });

      const result = await syncCostsToEVMS("prog-001", "period-002");

      expect(result.warnings).toHaveLength(1);
      expect(result.success).toBe(true);
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Sync failed"));

      await expect(syncCostsToEVMS("prog-001", "period-001")).rejects.toThrow(
        "Sync failed"
      );
    });
  });

  describe("recordCostEntry", () => {
    it("should post cost entry with required fields", async () => {
      const mockEntry = {
        id: "entry-001",
        assignment_id: "assign-001",
        entry_date: "2026-01-15",
        hours_worked: "8.00",
        cost_incurred: "800.00",
        quantity_used: null,
        notes: null,
        created_at: "2026-01-15T10:00:00Z",
      };
      mockedPost.mockResolvedValue({ data: mockEntry });

      const result = await recordCostEntry("assign-001", {
        entry_date: "2026-01-15",
        hours_worked: 8,
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/cost/assignments/assign-001/entries",
        { entry_date: "2026-01-15", hours_worked: 8 }
      );
      expect(result).toEqual(mockEntry);
    });

    it("should include optional fields when provided", async () => {
      const mockEntry = {
        id: "entry-002",
        assignment_id: "assign-001",
        entry_date: "2026-01-15",
        hours_worked: "4.00",
        cost_incurred: "400.00",
        quantity_used: "10.00",
        notes: "Half day",
        created_at: "2026-01-15T10:00:00Z",
      };
      mockedPost.mockResolvedValue({ data: mockEntry });

      await recordCostEntry("assign-001", {
        entry_date: "2026-01-15",
        hours_worked: 4,
        quantity_used: 10,
        notes: "Half day",
      });

      expect(mockedPost).toHaveBeenCalledWith(
        "/cost/assignments/assign-001/entries",
        {
          entry_date: "2026-01-15",
          hours_worked: 4,
          quantity_used: 10,
          notes: "Half day",
        }
      );
    });

    it("should not include undefined optional fields", async () => {
      const mockEntry = {
        id: "entry-003",
        assignment_id: "assign-001",
        entry_date: "2026-01-15",
        hours_worked: "8.00",
        cost_incurred: "800.00",
        quantity_used: null,
        notes: null,
        created_at: "2026-01-15T10:00:00Z",
      };
      mockedPost.mockResolvedValue({ data: mockEntry });

      await recordCostEntry("assign-001", {
        entry_date: "2026-01-15",
        hours_worked: 8,
      });

      const callPayload = mockedPost.mock.calls[0][1] as Record<string, unknown>;
      expect(callPayload).not.toHaveProperty("quantity_used");
      expect(callPayload).not.toHaveProperty("notes");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Invalid entry"));

      await expect(
        recordCostEntry("assign-001", {
          entry_date: "2026-01-15",
          hours_worked: 8,
        })
      ).rejects.toThrow("Invalid entry");
    });
  });

  describe("costApi object", () => {
    it("should export getActivityCost", () => {
      expect(costApi.getActivityCost).toBe(getActivityCost);
    });

    it("should export getWBSCost", () => {
      expect(costApi.getWBSCost).toBe(getWBSCost);
    });

    it("should export getProgramCostSummary", () => {
      expect(costApi.getProgramCostSummary).toBe(getProgramCostSummary);
    });

    it("should export syncCostsToEVMS", () => {
      expect(costApi.syncCostsToEVMS).toBe(syncCostsToEVMS);
    });

    it("should export recordCostEntry", () => {
      expect(costApi.recordCostEntry).toBe(recordCostEntry);
    });

    it("should have exactly five methods", () => {
      expect(Object.keys(costApi)).toHaveLength(5);
    });
  });
});
