import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MaterialSummaryPanel } from "../MaterialSummaryPanel";
import { ToastProvider } from "@/components/Toast";

const mockUseProgramMaterials = vi.fn();

vi.mock("@/hooks/useMaterial", () => ({
  useProgramMaterials: (...args: unknown[]) =>
    mockUseProgramMaterials(...args),
  useConsumeMaterial: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockMaterialData = {
  program_id: "prog-001",
  material_count: 2,
  total_value: "50000.00",
  consumed_value: "15000.00",
  remaining_value: "35000.00",
  materials: [
    {
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
    },
    {
      resource_id: "res-002",
      resource_code: "MAT-002",
      resource_name: "Copper Wire",
      quantity_unit: "m",
      quantity_available: "500.00",
      quantity_assigned: "400.00",
      quantity_consumed: "380.00",
      quantity_remaining: "20.00",
      percent_consumed: "95.00",
      unit_cost: "10.00",
      total_value: "5000.00",
      consumed_value: "3800.00",
    },
  ],
};

describe("MaterialSummaryPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("Loading material data...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(
      screen.getByText("Failed to load material data")
    ).toBeInTheDocument();
  });

  it("renders no data state", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("No material data available")).toBeInTheDocument();
  });

  it("renders material summary cards", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: mockMaterialData,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("Material Tracking")).toBeInTheDocument();
    expect(screen.getByText("Materials")).toBeInTheDocument();
    expect(screen.getByText("Total Value")).toBeInTheDocument();
    expect(screen.getByText("Consumed Value")).toBeInTheDocument();
    expect(screen.getByText("Remaining Value")).toBeInTheDocument();
  });

  it("renders materials in table", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: mockMaterialData,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("Steel Plate")).toBeInTheDocument();
    expect(screen.getByText("Copper Wire")).toBeInTheDocument();
    expect(screen.getByText("MAT-001")).toBeInTheDocument();
    expect(screen.getByText("MAT-002")).toBeInTheDocument();
  });

  it("renders consumption progress percentages", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: mockMaterialData,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("38%")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
  });

  it("renders empty state when no materials", () => {
    const emptyData = {
      ...mockMaterialData,
      materials: [],
      material_count: 0,
    };
    mockUseProgramMaterials.mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("No materials found")).toBeInTheDocument();
  });

  it("renders quantity units", () => {
    mockUseProgramMaterials.mockReturnValue({
      data: mockMaterialData,
      isLoading: false,
      error: null,
    });

    render(<MaterialSummaryPanel programId="prog-001" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("kg")).toBeInTheDocument();
    expect(screen.getByText("m")).toBeInTheDocument();
  });
});
