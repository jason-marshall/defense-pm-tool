import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PoolAvailabilityView } from "../PoolAvailabilityView";

const mockUsePoolAvailability = vi.fn();

vi.mock("@/hooks/useResourcePools", () => ({
  usePoolAvailability: (...args: unknown[]) => mockUsePoolAvailability(...args),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("PoolAvailabilityView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUsePoolAvailability.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderWithProviders(
      <PoolAvailabilityView poolId="pool-1" poolName="Engineering Pool" />
    );

    expect(screen.getByText("Loading availability...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUsePoolAvailability.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    renderWithProviders(
      <PoolAvailabilityView poolId="pool-1" poolName="Engineering Pool" />
    );

    expect(
      screen.getByText("Failed to load availability")
    ).toBeInTheDocument();
  });

  it("renders resource table with data", () => {
    mockUsePoolAvailability.mockReturnValue({
      data: {
        conflict_count: 0,
        conflicts: [],
        resources: [
          {
            resource_id: "res-1",
            resource_name: "Alice",
            available_hours: 160,
            assigned_hours: 80,
          },
          {
            resource_id: "res-2",
            resource_name: "Bob",
            available_hours: 160,
            assigned_hours: 120,
          },
        ],
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <PoolAvailabilityView poolId="pool-1" poolName="Engineering Pool" />
    );

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Resource")).toBeInTheDocument();
    expect(screen.getByText("Available Hours")).toBeInTheDocument();
  });

  it("shows conflicts warning when conflicts exist", () => {
    mockUsePoolAvailability.mockReturnValue({
      data: {
        conflict_count: 2,
        conflicts: [
          {
            resource_name: "Alice",
            conflict_date: "2026-02-15",
            overallocation_hours: 4,
            programs_involved: ["Program A", "Program B"],
          },
          {
            resource_name: "Bob",
            conflict_date: "2026-02-16",
            overallocation_hours: 2,
            programs_involved: ["Program A"],
          },
        ],
        resources: [],
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <PoolAvailabilityView poolId="pool-1" poolName="Engineering Pool" />
    );

    expect(screen.getByText("2 Conflicts Found")).toBeInTheDocument();
  });

  it("shows no-conflicts success message", () => {
    mockUsePoolAvailability.mockReturnValue({
      data: {
        conflict_count: 0,
        conflicts: [],
        resources: [],
      },
      isLoading: false,
      error: null,
    });

    renderWithProviders(
      <PoolAvailabilityView poolId="pool-1" poolName="Engineering Pool" />
    );

    expect(
      screen.getByText("No conflicts found in the selected date range")
    ).toBeInTheDocument();
  });
});
