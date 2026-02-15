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

  // ============================================================
  // NEW TESTS: Simulate scenario
  // ============================================================

  describe("simulate scenario", () => {
    it("shows success toast after successful simulation", async () => {
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

      // Toast should show success
      await waitFor(() => {
        expect(screen.getByText("Simulation complete")).toBeInTheDocument();
      });
    });

    it("shows error toast when simulation fails", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      mockSimulateMutateAsync.mockRejectedValue(new Error("Server error"));

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Simulate"));

      await waitFor(() => {
        expect(screen.getByText("Simulation failed")).toBeInTheDocument();
      });
    });

    it("does not show Simulate button for simulated scenarios", () => {
      const simulatedOnly: ScenarioListResponse = {
        items: [
          {
            id: "sc-sim",
            program_id: "prog-1",
            name: "Already Simulated",
            description: null,
            status: "simulated",
            changes: [],
            simulation_results: {
              duration_p10: 10,
              duration_p50: 12,
              duration_p80: 14,
              duration_p90: 16,
              cost_p50: "100000",
              cost_p90: "120000",
            },
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: simulatedOnly,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // No Simulate button should be present
      expect(screen.queryByText("Simulate")).not.toBeInTheDocument();
    });

    it("does not show Simulate button for promoted scenarios", () => {
      const promotedOnly: ScenarioListResponse = {
        items: [
          {
            id: "sc-prom",
            program_id: "prog-1",
            name: "Promoted Scenario",
            description: null,
            status: "promoted",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: promotedOnly,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.queryByText("Simulate")).not.toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Promote scenario
  // ============================================================

  describe("promote scenario", () => {
    it("shows confirmation before promoting", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockPromoteMutateAsync.mockResolvedValue(undefined);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Promote"));

      expect(confirmSpy).toHaveBeenCalledWith("Promote this scenario to baseline?");

      confirmSpy.mockRestore();
    });

    it("promotes scenario when confirmed", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockPromoteMutateAsync.mockResolvedValue(undefined);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Promote"));

      await waitFor(() => {
        expect(mockPromoteMutateAsync).toHaveBeenCalledWith("sc-2");
      });

      // Toast should show success
      await waitFor(() => {
        expect(screen.getByText("Scenario promoted to baseline")).toBeInTheDocument();
      });

      confirmSpy.mockRestore();
    });

    it("does not promote when confirmation is cancelled", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Promote"));

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockPromoteMutateAsync).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("shows error toast when promotion fails", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockPromoteMutateAsync.mockRejectedValue(new Error("Promotion error"));

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Promote"));

      await waitFor(() => {
        expect(screen.getByText("Promotion failed")).toBeInTheDocument();
      });

      confirmSpy.mockRestore();
    });

    it("does not show Promote button for draft scenarios", () => {
      const draftOnly: ScenarioListResponse = {
        items: [
          {
            id: "sc-draft",
            program_id: "prog-1",
            name: "Draft Only",
            description: null,
            status: "draft",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: draftOnly,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.queryByText("Promote")).not.toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Delete scenario with confirmation
  // ============================================================

  describe("delete scenario", () => {
    it("shows confirmation before deleting", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockDeleteMutateAsync.mockResolvedValue(undefined);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Click delete on the first scenario
      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalledWith("Delete this scenario?");

      confirmSpy.mockRestore();
    });

    it("deletes scenario when confirmed", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockDeleteMutateAsync.mockResolvedValue(undefined);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("sc-1");
      });

      // Success toast
      await waitFor(() => {
        expect(screen.getByText("Scenario deleted")).toBeInTheDocument();
      });

      confirmSpy.mockRestore();
    });

    it("does not delete when confirmation is cancelled", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockDeleteMutateAsync).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("shows error toast when delete fails", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockDeleteMutateAsync.mockRejectedValue(new Error("Delete error"));

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText("Delete failed")).toBeInTheDocument();
      });

      confirmSpy.mockRestore();
    });

    it("can delete the second scenario", async () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
      mockDeleteMutateAsync.mockResolvedValue(undefined);

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Delete second scenario
      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[1]);

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("sc-2");
      });

      confirmSpy.mockRestore();
    });

    it("has accessible delete button labels", () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(
        screen.getByLabelText("Delete scenario Optimistic Schedule")
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText("Delete scenario Risk Mitigation")
      ).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Loading/error/empty states (extended)
  // ============================================================

  describe("loading/error/empty states", () => {
    it("does not render scenario cards in loading state", () => {
      mockUseScenarios.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.queryByText("Optimistic Schedule")).not.toBeInTheDocument();
      expect(screen.queryByText("Simulate")).not.toBeInTheDocument();
      expect(screen.queryByText("Promote")).not.toBeInTheDocument();
    });

    it("does not render scenario cards in error state", () => {
      mockUseScenarios.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Network failure"),
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Error loading scenarios")).toBeInTheDocument();
      expect(screen.queryByText("Optimistic Schedule")).not.toBeInTheDocument();
    });

    it("renders heading even when empty", () => {
      mockUseScenarios.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Scenarios")).toBeInTheDocument();
      expect(screen.getByText("No scenarios created yet.")).toBeInTheDocument();
    });

    it("handles data with undefined items gracefully", () => {
      mockUseScenarios.mockReturnValue({
        data: {},
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Should fallback to empty state since items is undefined
      expect(screen.getByText("No scenarios created yet.")).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Scenario status display
  // ============================================================

  describe("scenario status display", () => {
    it("renders promoted status correctly", () => {
      const promotedScenario: ScenarioListResponse = {
        items: [
          {
            id: "sc-prom",
            program_id: "prog-1",
            name: "Promoted Plan",
            description: "This was promoted",
            status: "promoted",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: "2026-01-20T00:00:00Z",
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: promotedScenario,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("promoted")).toBeInTheDocument();
      expect(screen.getByText("Promoted Plan")).toBeInTheDocument();
      // No Simulate or Promote buttons for promoted scenarios
      expect(screen.queryByText("Simulate")).not.toBeInTheDocument();
      expect(screen.queryByText("Promote")).not.toBeInTheDocument();
    });

    it("renders archived status correctly", () => {
      const archivedScenario: ScenarioListResponse = {
        items: [
          {
            id: "sc-arch",
            program_id: "prog-1",
            name: "Archived Plan",
            description: null,
            status: "archived",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: archivedScenario,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("archived")).toBeInTheDocument();
      expect(screen.queryByText("Simulate")).not.toBeInTheDocument();
      expect(screen.queryByText("Promote")).not.toBeInTheDocument();
    });

    it("does not show description when it is null", () => {
      const noDesc: ScenarioListResponse = {
        items: [
          {
            id: "sc-nodesc",
            program_id: "prog-1",
            name: "No Description",
            description: null,
            status: "draft",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: noDesc,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("No Description")).toBeInTheDocument();
      // Only the scenario name, status, and change count should be rendered
      const paragraphs = document.querySelectorAll("p.text-sm.text-gray-500");
      expect(paragraphs.length).toBe(0);
    });

    it("shows 0 changes for scenario with no changes", () => {
      const noChanges: ScenarioListResponse = {
        items: [
          {
            id: "sc-nochange",
            program_id: "prog-1",
            name: "Empty Changes",
            description: null,
            status: "draft",
            changes: [],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: noChanges,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("0 changes")).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Simulation results display
  // ============================================================

  describe("simulation results display", () => {
    it("does not show simulation results when null", () => {
      const noResults: ScenarioListResponse = {
        items: [
          {
            id: "sc-noresults",
            program_id: "prog-1",
            name: "No Results Yet",
            description: null,
            status: "draft",
            changes: [
              {
                activity_id: "act-1",
                field: "duration",
                old_value: "5",
                new_value: "10",
              },
            ],
            simulation_results: null,
            created_at: "2026-01-15T00:00:00Z",
            updated_at: null,
          },
        ],
        total: 1,
      };
      mockUseScenarios.mockReturnValue({
        data: noResults,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Should not see any P10/P50/P80/P90 labels
      expect(screen.queryByText("P10:")).not.toBeInTheDocument();
      expect(screen.queryByText("P50:")).not.toBeInTheDocument();
      expect(screen.queryByText("P80:")).not.toBeInTheDocument();
      expect(screen.queryByText("P90:")).not.toBeInTheDocument();
    });

    it("renders all simulation percentile values with correct labels", () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Check for P-labels
      expect(screen.getByText("P10:")).toBeInTheDocument();
      expect(screen.getByText("P50:")).toBeInTheDocument();
      expect(screen.getByText("P80:")).toBeInTheDocument();
      expect(screen.getByText("P90:")).toBeInTheDocument();

      // Check for values
      expect(screen.getByText("12d")).toBeInTheDocument();
      expect(screen.getByText("15d")).toBeInTheDocument();
      expect(screen.getByText("18d")).toBeInTheDocument();
      expect(screen.getByText("20d")).toBeInTheDocument();
    });
  });

  // ============================================================
  // NEW TESTS: Multiple scenarios interaction
  // ============================================================

  describe("multiple scenarios interaction", () => {
    it("renders all delete buttons for every scenario", () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      expect(deleteButtons.length).toBe(2);
    });

    it("renders correct action buttons per scenario status", () => {
      mockUseScenarios.mockReturnValue({
        data: mockScenarios,
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="prog-1" />, { wrapper: Wrapper });

      // Draft scenario (sc-1) should have Simulate, no Promote
      expect(screen.getByText("Simulate")).toBeInTheDocument();

      // Simulated scenario (sc-2) should have Promote, no second Simulate
      expect(screen.getByText("Promote")).toBeInTheDocument();

      // Only 1 Simulate and 1 Promote
      const simulateButtons = screen.getAllByText("Simulate");
      expect(simulateButtons.length).toBe(1);
      const promoteButtons = screen.getAllByText("Promote");
      expect(promoteButtons.length).toBe(1);
    });

    it("passes correct programId to useScenarios hook", () => {
      mockUseScenarios.mockReturnValue({
        data: { items: [], total: 0 },
        isLoading: false,
        error: null,
      });

      render(<ScenarioList programId="my-program-123" />, { wrapper: Wrapper });

      expect(mockUseScenarios).toHaveBeenCalledWith("my-program-123");
    });
  });
});
