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

let mockCreateIsPending = false;
let mockDeleteIsPending = false;

vi.mock("@/hooks/usePrograms", () => ({
  usePrograms: (...args: unknown[]) => mockUsePrograms(...args),
  useCreateProgram: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: mockCreateIsPending,
  }),
  useDeleteProgram: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: mockDeleteIsPending,
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
    mockCreateIsPending = false;
    mockDeleteIsPending = false;
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

  // --- New tests for improved coverage ---

  describe("create new program", () => {
    it("opens create modal from empty state link", () => {
      mockUsePrograms.mockReturnValue({
        data: { items: [], total: 0, page: 1, page_size: 20 },
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Create your first program"));

      expect(screen.getByText("Create Program")).toBeInTheDocument();
    });

    it("opens create modal from header button and shows form fields", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));

      expect(screen.getByLabelText("Name *")).toBeInTheDocument();
      expect(screen.getByLabelText("Code *")).toBeInTheDocument();
      expect(screen.getByLabelText("Start Date *")).toBeInTheDocument();
      expect(screen.getByLabelText("End Date *")).toBeInTheDocument();
      expect(screen.getByLabelText("Budget at Completion ($)")).toBeInTheDocument();
    });

    it("submits create form and shows success toast", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockCreateMutateAsync.mockResolvedValue({
        id: "prog-3",
        name: "New Program",
        code: "NP-01",
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));

      fireEvent.change(screen.getByLabelText("Name *"), {
        target: { value: "New Program" },
      });
      fireEvent.change(screen.getByLabelText("Code *"), {
        target: { value: "NP-01" },
      });
      fireEvent.change(screen.getByLabelText("Start Date *"), {
        target: { value: "2026-03-01" },
      });
      fireEvent.change(screen.getByLabelText("End Date *"), {
        target: { value: "2026-09-01" },
      });

      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "New Program",
            code: "NP-01",
            planned_start_date: "2026-03-01",
            planned_end_date: "2026-09-01",
          })
        );
      });

      expect(await screen.findByText("Program created")).toBeInTheDocument();
    });

    it("shows error toast when create fails", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockCreateMutateAsync.mockRejectedValue(new Error("Conflict"));

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));

      fireEvent.change(screen.getByLabelText("Name *"), {
        target: { value: "Duplicate Program" },
      });
      fireEvent.change(screen.getByLabelText("Code *"), {
        target: { value: "DUP-01" },
      });
      fireEvent.change(screen.getByLabelText("Start Date *"), {
        target: { value: "2026-03-01" },
      });
      fireEvent.change(screen.getByLabelText("End Date *"), {
        target: { value: "2026-09-01" },
      });

      fireEvent.click(screen.getByText("Create"));

      expect(await screen.findByText("Failed to save program")).toBeInTheDocument();
    });

    it("closes create modal when Cancel is clicked", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));
      expect(screen.getByText("Create Program")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));

      expect(screen.queryByText("Create Program")).not.toBeInTheDocument();
    });

    it("closes create modal when close button is clicked", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));
      expect(screen.getByText("Create Program")).toBeInTheDocument();

      fireEvent.click(screen.getByLabelText("Close"));

      expect(screen.queryByText("Create Program")).not.toBeInTheDocument();
    });

    it("closes modal after successful create", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockCreateMutateAsync.mockResolvedValue({ id: "prog-3" });

      render(<ProgramsPage />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("New Program"));

      fireEvent.change(screen.getByLabelText("Name *"), {
        target: { value: "New Program" },
      });
      fireEvent.change(screen.getByLabelText("Code *"), {
        target: { value: "NP-01" },
      });
      fireEvent.change(screen.getByLabelText("Start Date *"), {
        target: { value: "2026-03-01" },
      });
      fireEvent.change(screen.getByLabelText("End Date *"), {
        target: { value: "2026-09-01" },
      });

      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.queryByText("Create Program")).not.toBeInTheDocument();
      });
    });
  });

  describe("delete program", () => {
    it("deletes second program when its delete button is clicked", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockDeleteMutateAsync.mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<ProgramsPage />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[1]);

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("prog-2");
      });
    });

    it("shows success toast after successful delete", async () => {
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

      expect(await screen.findByText("Program deleted successfully")).toBeInTheDocument();
    });

    it("shows error toast when delete fails", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockDeleteMutateAsync.mockRejectedValue(new Error("Server error"));
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<ProgramsPage />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      expect(await screen.findByText("Failed to delete program")).toBeInTheDocument();
    });

    it("disables delete button when delete is pending", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockDeleteIsPending = true;

      render(<ProgramsPage />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      expect(deleteButtons[0]).toBeDisabled();
      expect(deleteButtons[1]).toBeDisabled();
    });
  });

  describe("edit program", () => {
    it("opens edit modal when Edit button is clicked", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Edit Program")).toBeInTheDocument();
    });

    it("populates form with existing program data when editing", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByLabelText("Name *")).toHaveValue("F-35 Program");
      expect(screen.getByLabelText("Code *")).toHaveValue("F35");
    });

    it("shows Update button instead of Create when editing", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Update")).toBeInTheDocument();
      expect(screen.queryByText("Create")).not.toBeInTheDocument();
    });

    it("submits edit form and shows success toast", async () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });
      mockCreateMutateAsync.mockResolvedValue({ id: "prog-1" });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      fireEvent.change(screen.getByLabelText("Name *"), {
        target: { value: "F-35 Updated" },
      });

      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "F-35 Updated",
            code: "F35",
          })
        );
      });

      expect(await screen.findByText("Program updated")).toBeInTheDocument();
    });

    it("closes edit modal when Cancel is clicked", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Edit Program")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));

      expect(screen.queryByText("Edit Program")).not.toBeInTheDocument();
    });

    it("edits second program and populates its data", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[1]);

      expect(screen.getByText("Edit Program")).toBeInTheDocument();
      expect(screen.getByLabelText("Name *")).toHaveValue("Drone System");
      expect(screen.getByLabelText("Code *")).toHaveValue("DS-01");
    });
  });

  describe("table display", () => {
    it("renders table headers", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("Code")).toBeInTheDocument();
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
      expect(screen.getByText("Start Date")).toBeInTheDocument();
      expect(screen.getByText("End Date")).toBeInTheDocument();
      expect(screen.getByText("BAC")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });

    it("renders program dates correctly", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("2026-01-01")).toBeInTheDocument();
      expect(screen.getByText("2026-12-31")).toBeInTheDocument();
      expect(screen.getByText("2026-06-01")).toBeInTheDocument();
      expect(screen.getByText("2027-06-01")).toBeInTheDocument();
    });

    it("renders budget at completion formatted as currency", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("$5,000,000")).toBeInTheDocument();
      expect(screen.getByText("$1,000,000")).toBeInTheDocument();
    });

    it("renders dash when budget_at_completion is null", () => {
      const programWithNoBudget: ProgramListResponse = {
        items: [
          {
            ...mockProgramList.items[0],
            budget_at_completion: "",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      };
      mockUsePrograms.mockReturnValue({
        data: programWithNoBudget,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("-")).toBeInTheDocument();
    });

    it("renders program links that navigate to program detail", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      const f35Links = screen.getAllByRole("link", { name: /F-35 Program|F35/ });
      expect(f35Links.length).toBeGreaterThan(0);
      expect(f35Links[0]).toHaveAttribute("href", "/programs/prog-1");
    });

    it("renders status badges with correct text for ON_HOLD", () => {
      const onHoldProgram: ProgramListResponse = {
        items: [
          {
            ...mockProgramList.items[0],
            status: "ON_HOLD",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      };
      mockUsePrograms.mockReturnValue({
        data: onHoldProgram,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("ON HOLD")).toBeInTheDocument();
    });

    it("renders status badges for COMPLETED status", () => {
      const completedProgram: ProgramListResponse = {
        items: [
          {
            ...mockProgramList.items[0],
            status: "COMPLETED",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      };
      mockUsePrograms.mockReturnValue({
        data: completedProgram,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("COMPLETED")).toBeInTheDocument();
    });

    it("renders status badges for CANCELLED status", () => {
      const cancelledProgram: ProgramListResponse = {
        items: [
          {
            ...mockProgramList.items[0],
            status: "CANCELLED",
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      };
      mockUsePrograms.mockReturnValue({
        data: cancelledProgram,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("CANCELLED")).toBeInTheDocument();
    });
  });

  describe("error state details", () => {
    it("renders generic error message for non-Error objects", () => {
      mockUsePrograms.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: "something went wrong",
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText(/Error loading programs/)).toBeInTheDocument();
      expect(screen.getByText(/Unknown error/)).toBeInTheDocument();
    });

    it("renders specific error message from Error objects", () => {
      mockUsePrograms.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Forbidden: insufficient permissions"),
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(
        screen.getByText(/Forbidden: insufficient permissions/)
      ).toBeInTheDocument();
    });
  });

  describe("page header", () => {
    it("renders Programs heading", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("Programs")).toBeInTheDocument();
    });

    it("always shows the New Program button in header", () => {
      mockUsePrograms.mockReturnValue({
        data: mockProgramList,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      expect(screen.getByText("New Program")).toBeInTheDocument();
    });
  });

  describe("data edge cases", () => {
    it("handles undefined data items gracefully", () => {
      mockUsePrograms.mockReturnValue({
        data: { items: undefined, total: 0, page: 1, page_size: 20 },
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      // Should show empty state since items ?? [] results in []
      expect(screen.getByText("No programs yet.")).toBeInTheDocument();
    });

    it("handles null data gracefully", () => {
      mockUsePrograms.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(<ProgramsPage />, { wrapper: Wrapper });

      // data?.items ?? [] => undefined ?? [] => []
      expect(screen.getByText("No programs yet.")).toBeInTheDocument();
    });
  });
});
