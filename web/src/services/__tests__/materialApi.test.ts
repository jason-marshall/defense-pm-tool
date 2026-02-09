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
  getMaterialStatus,
  consumeMaterial,
  getProgramMaterials,
  materialApi,
} from "../materialApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockMaterialStatus = {
  resource_id: "res-001",
  resource_code: "MAT-001",
  resource_name: "Steel Plate",
  quantity_unit: "kg",
  quantity_available: "1000.00",
  quantity_assigned: "800.00",
  quantity_consumed: "300.00",
  quantity_remaining: "500.00",
  percent_consumed: "37.50",
  unit_cost: "25.00",
  total_value: "25000.00",
  consumed_value: "7500.00",
};

const mockProgramMaterials = {
  program_id: "prog-001",
  material_count: 3,
  total_value: "75000.00",
  consumed_value: "25000.00",
  remaining_value: "50000.00",
  materials: [mockMaterialStatus],
};

describe("materialApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getMaterialStatus", () => {
    it("should fetch material status by resource ID", async () => {
      mockedGet.mockResolvedValue({ data: mockMaterialStatus });

      const result = await getMaterialStatus("res-001");

      expect(mockedGet).toHaveBeenCalledWith("/materials/resources/res-001");
      expect(result).toEqual(mockMaterialStatus);
    });

    it("should return all quantity fields", async () => {
      mockedGet.mockResolvedValue({ data: mockMaterialStatus });

      const result = await getMaterialStatus("res-001");

      expect(result.quantity_available).toBe("1000.00");
      expect(result.quantity_consumed).toBe("300.00");
      expect(result.quantity_remaining).toBe("500.00");
      expect(result.percent_consumed).toBe("37.50");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Not found"));

      await expect(getMaterialStatus("invalid")).rejects.toThrow("Not found");
    });
  });

  describe("consumeMaterial", () => {
    it("should post consumption request", async () => {
      const mockConsumption = {
        assignment_id: "assign-001",
        quantity_consumed: "50.00",
        remaining_assigned: "450.00",
        cost_incurred: "1250.00",
      };
      mockedPost.mockResolvedValue({ data: mockConsumption });

      const result = await consumeMaterial("assign-001", 50);

      expect(mockedPost).toHaveBeenCalledWith(
        "/materials/assignments/assign-001/consume",
        { quantity: 50 }
      );
      expect(result).toEqual(mockConsumption);
    });

    it("should return consumption result", async () => {
      const mockConsumption = {
        assignment_id: "assign-001",
        quantity_consumed: "100.00",
        remaining_assigned: "400.00",
        cost_incurred: "2500.00",
      };
      mockedPost.mockResolvedValue({ data: mockConsumption });

      const result = await consumeMaterial("assign-001", 100);

      expect(result.quantity_consumed).toBe("100.00");
      expect(result.cost_incurred).toBe("2500.00");
    });

    it("should propagate errors", async () => {
      mockedPost.mockRejectedValue(new Error("Insufficient quantity"));

      await expect(consumeMaterial("assign-001", 9999)).rejects.toThrow(
        "Insufficient quantity"
      );
    });
  });

  describe("getProgramMaterials", () => {
    it("should fetch program materials summary", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramMaterials });

      const result = await getProgramMaterials("prog-001");

      expect(mockedGet).toHaveBeenCalledWith("/materials/programs/prog-001");
      expect(result).toEqual(mockProgramMaterials);
    });

    it("should return material list", async () => {
      mockedGet.mockResolvedValue({ data: mockProgramMaterials });

      const result = await getProgramMaterials("prog-001");

      expect(result.material_count).toBe(3);
      expect(result.materials).toHaveLength(1);
      expect(result.materials[0].resource_name).toBe("Steel Plate");
    });

    it("should propagate errors", async () => {
      mockedGet.mockRejectedValue(new Error("Forbidden"));

      await expect(getProgramMaterials("prog-001")).rejects.toThrow(
        "Forbidden"
      );
    });
  });

  describe("materialApi object", () => {
    it("should export getStatus as getMaterialStatus", () => {
      expect(materialApi.getStatus).toBe(getMaterialStatus);
    });

    it("should export consume as consumeMaterial", () => {
      expect(materialApi.consume).toBe(consumeMaterial);
    });

    it("should export getProgramMaterials", () => {
      expect(materialApi.getProgramMaterials).toBe(getProgramMaterials);
    });

    it("should have exactly three methods", () => {
      expect(Object.keys(materialApi)).toHaveLength(3);
    });
  });
});
