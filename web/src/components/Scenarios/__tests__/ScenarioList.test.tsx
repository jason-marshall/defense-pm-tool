import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScenarioList } from "../ScenarioList";
import { ToastProvider } from "@/components/Toast";
import type { ScenarioListResponse } from "@/types/scenario";

// Mock the hooks
const mockUseScenarios = vi.fn();
const mockSimulateMutateAsync = vi.fn();
const mockPromoteMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useScenarios", () => ({
  useScenarios: (...args: unknown[]) => mockUseScenarios(...args),
  useSimulateScenario: () => ({
    mutateAsync: mockSimulateMutateAsync,
    isPending: false,
  }),
  usePromoteScenario: () => ({
    mutateAsync: mockPromoteMutateAsync,
    isPending: false,
  }),
  useDeleteScenario: () => ({
    mutateAsync: mockDeleteMutateAsync,
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

const mockScenarios: ScenarioListResponse = {
  items: [
    {
      id: "sc-1",
      program_id: "prog-1",
      name: "Optimistic Schedule",
      description: "Best case scenario",
      status: "draft",
      changes: [
        {
          activity_id: "act-1",
          activity_name: "Design",
          field: "duration",
          old_value: "10",
          new_value: "8",
        },
      ],
      simulation_results: null,
      created_at: "2026-01-15T00:00:00Z",
      updated_at: null,
    },
    {
      id: "sc-2",
      program_id: "prog-1",
      name: "Risk Mitigation",
      description: null,
      status: "simulated",
      changes: [
        {
          activity_id: "act-2",
          activity_name: "Testing",
          field: "duration",
          old_value: "5",
          new_value: "7",
        },
        {
          activity_id: "act-3",
          activity_name: "Deploy",
          field: "duration",
          old_value: "3",
          new_value: "5",
        },
      ],
      simulation_results: {
        duration_p10: 12,
        duration_p50: 15,
        duration_p80: 18,
        duration_p90: 20,
        cost_p50: "250000",
        cost_p90: "300000",
      },
      created_at: "2026-01-20T00:00:00Z",
      updated_at: "2026-01-21T00:00:00Z",
    },
  ],
  total: 2,
};

describe("ScenarioList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseScenarios.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading scenarios...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseScenarios.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading scenarios")).toBeInTheDocument();
  });

  it("renders empty state when no scenarios", () => {
    mockUseScenarios.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText("No scenarios created yet.")
    ).toBeInTheDocument();
  });

  it("renders scenario cards with names and statuses", () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Optimistic Schedule")).toBeInTheDocument();
    expect(screen.getByText("Risk Mitigation")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText("simulated")).toBeInTheDocument();
    expect(screen.getByText("Best case scenario")).toBeInTheDocument();
  });

  it("shows change count for each scenario", () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("1 changes")).toBeInTheDocument();
    expect(screen.getByText("2 changes")).toBeInTheDocument();
  });

  it("shows Simulate button for draft scenarios", () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Simulate")).toBeInTheDocument();
  });

  it("shows Promote button for simulated scenarios", () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Promote")).toBeInTheDocument();
  });

  it("displays simulation results when available", () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("12d")).toBeInTheDocument(); // P10
    expect(screen.getByText("15d")).toBeInTheDocument(); // P50
    expect(screen.getByText("18d")).toBeInTheDocument(); // P80
    expect(screen.getByText("20d")).toBeInTheDocument(); // P90
  });

  it("calls simulate when Simulate button is clicked", async () => {
    mockUseScenarios.mockReturnValue({
      data: mockScenarios,
      isLoading: false,
      error: null,
    });
    mockSimulateMutateAsync.mockResolvedValue(undefined);

    render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Simulate"));

    await waitFor(() => {
      expect(mockSimulateMutateAsync).toHaveBeenCalledWith("sc-1");
    });
  });
});
