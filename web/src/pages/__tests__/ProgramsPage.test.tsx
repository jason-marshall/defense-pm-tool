import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ProgramsPage } from "../ProgramsPage";
import { ToastProvider } from "@/components/Toast";
import type { ProgramListResponse } from "@/types/program";

// Mock the hooks
const mockUsePrograms = vi.fn();
const mockCreateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/usePrograms", () => ({
  usePrograms: (...args: unknown[]) => mockUsePrograms(...args),
  useCreateProgram: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useDeleteProgram: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ToastProvider>{children}</ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockProgramList: ProgramListResponse = {
  items: [
    {
      id: "prog-1",
      name: "F-35 Program",
      code: "F35",
      description: "Joint Strike Fighter",
      status: "ACTIVE",
      planned_start_date: "2026-01-01",
      planned_end_date: "2026-12-31",
      actual_start_date: null,
      actual_end_date: null,
      budget_at_completion: "5000000",
      contract_number: "FA-001",
      contract_type: "CPFF",
      owner_id: "user-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "prog-2",
      name: "Drone System",
      code: "DS-01",
      description: null,
      status: "PLANNING",
      planned_start_date: "2026-06-01",
      planned_end_date: "2027-06-01",
      actual_start_date: null,
      actual_end_date: null,
      budget_at_completion: "1000000",
      contract_number: null,
      contract_type: null,
      owner_id: "user-1",
      created_at: "2026-01-15T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

describe("ProgramsPage", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUsePrograms.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ProgramsPage />, { wrapper: Wrapper });

    expect(screen.getByText("Loading programs...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUsePrograms.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Server error"),
    });

    render(<ProgramsPage />, { wrapper: Wrapper });

    expect(screen.getByText(/Error loading programs/)).toBeInTheDocument();
    expect(screen.getByText(/Server error/)).toBeInTheDocument();
  });

  it("renders empty state when no programs exist", () => {
    mockUsePrograms.mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 20 },
      isLoading: false,
      error: null,
    });

    render(<ProgramsPage />, { wrapper: Wrapper });

    expect(screen.getByText("No programs yet.")).toBeInTheDocument();
    expect(screen.getByText("Create your first program")).toBeInTheDocument();
  });

  it("renders programs table with data", () => {
    mockUsePrograms.mockReturnValue({
      data: mockProgramList,
      isLoading: false,
      error: null,
    });

    render(<ProgramsPage />, { wrapper: Wrapper });

    expect(screen.getByText("F35")).toBeInTheDocument();
    expect(screen.getByText("F-35 Program")).toBeInTheDocument();
    expect(screen.getByText("DS-01")).toBeInTheDocument();
    expect(screen.getByText("Drone System")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("PLANNING")).toBeInTheDocument();
  });

  it("opens form modal when New Program is clicked", () => {
    mockUsePrograms.mockReturnValue({
      data: mockProgramList,
      isLoading: false,
      error: null,
    });

    render(<ProgramsPage />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("New Program"));

    expect(screen.getByText("Create Program")).toBeInTheDocument();
  });

  it("handles delete with confirmation", async () => {
    mockUsePrograms.mockReturnValue({
      data: mockProgramList,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ProgramsPage />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith(
      "Are you sure you want to delete this program?"
    );

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("prog-1");
    });
  });

  it("does not delete when confirmation is cancelled", () => {
    mockUsePrograms.mockReturnValue({
      data: mockProgramList,
      isLoading: false,
      error: null,
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ProgramsPage />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
  });
});
