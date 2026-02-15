import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DependencyList } from "../DependencyList";
import { ToastProvider } from "@/components/Toast";
import type { DependencyListResponse } from "@/types/dependency";

// Mock the hooks
const mockUseDependencies = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useDependencies", () => ({
  useDependencies: (...args: unknown[]) => mockUseDependencies(...args),
  useDeleteDependency: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}));

// Mock DependencyFormModal to avoid deep dependencies
vi.mock("../DependencyFormModal", () => ({
  DependencyFormModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="dependency-form-modal">
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockDependencies: DependencyListResponse = {
  items: [
    {
      id: "dep-1",
      predecessor_id: "act-1",
      successor_id: "act-2",
      dependency_type: "FS",
      lag: 0,
      predecessor_name: "Design Review",
      successor_name: "Code Implementation",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "dep-2",
      predecessor_id: "act-2",
      successor_id: "act-3",
      dependency_type: "SS",
      lag: 2,
      predecessor_name: "Code Implementation",
      successor_name: "Testing",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "dep-3",
      predecessor_id: "act-3",
      successor_id: "act-4",
      dependency_type: "FF",
      lag: -1,
      predecessor_name: "Testing",
      successor_name: "Documentation",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 3,
};

describe("DependencyList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseDependencies.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading dependencies...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseDependencies.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      screen.getByText("Error loading dependencies")
    ).toBeInTheDocument();
  });

  it("renders empty state when no dependencies", () => {
    mockUseDependencies.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No dependencies defined.")).toBeInTheDocument();
    expect(
      screen.getByText("Add your first dependency")
    ).toBeInTheDocument();
  });

  it("renders dependency table with data", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Design Review")).toBeInTheDocument();
    // "Code Implementation" appears twice: as successor of dep-1 and predecessor of dep-2
    expect(screen.getAllByText("Code Implementation")).toHaveLength(2);
    // "Testing" appears twice: as successor of dep-2 and predecessor of dep-3
    expect(screen.getAllByText("Testing")).toHaveLength(2);
    expect(screen.getByText("Documentation")).toBeInTheDocument();
  });

  it("renders dependency type badges", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("FS")).toBeInTheDocument();
    expect(screen.getByText("SS")).toBeInTheDocument();
    expect(screen.getByText("FF")).toBeInTheDocument();
  });

  it("shows lag values for each dependency", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("0d")).toBeInTheDocument();
    expect(screen.getByText("2d")).toBeInTheDocument();
    expect(screen.getByText("-1d")).toBeInTheDocument();
  });

  it("opens form modal when Add Dependency is clicked", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Dependency"));

    expect(screen.getByTestId("dependency-form-modal")).toBeInTheDocument();
  });

  it("handles delete with confirmation", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this dependency?");
  });

  it("calls mutateAsync with correct id when delete is confirmed", async () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("dep-1");
    });
  });

  it("does not call mutateAsync when delete is cancelled", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith("Delete this dependency?");
    expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
  });

  it("deletes the correct dependency when clicking second delete button", async () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    fireEvent.click(deleteButtons[1]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("dep-2");
    });
  });

  it("shows success toast after successful delete", async () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Dependency deleted")).toBeInTheDocument();
    });
  });

  it("shows error toast when delete fails", async () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockRejectedValue(new Error("Server error"));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Failed to delete dependency")).toBeInTheDocument();
    });
  });

  it("opens form modal from empty state link", () => {
    mockUseDependencies.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add your first dependency"));

    expect(screen.getByTestId("dependency-form-modal")).toBeInTheDocument();
  });

  it("closes form modal when onClose is called", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    // Open the modal
    fireEvent.click(screen.getByText("Add Dependency"));
    expect(screen.getByTestId("dependency-form-modal")).toBeInTheDocument();

    // Close the modal
    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByTestId("dependency-form-modal")).not.toBeInTheDocument();
  });

  it("renders SF type badge with correct styling", () => {
    const sfDependency: DependencyListResponse = {
      items: [
        {
          id: "dep-sf",
          predecessor_id: "act-10",
          successor_id: "act-11",
          dependency_type: "SF",
          lag: 0,
          predecessor_name: "Milestone A",
          successor_name: "Milestone B",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: null,
        },
      ],
      total: 1,
    };
    mockUseDependencies.mockReturnValue({
      data: sfDependency,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const badge = screen.getByText("SF");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-orange-100");
    expect(badge.className).toContain("text-orange-700");
  });

  it("falls back to truncated IDs when names are missing", () => {
    const noNameDeps: DependencyListResponse = {
      items: [
        {
          id: "dep-noname",
          predecessor_id: "abcdefgh-1234-5678-9012-ijklmnopqrst",
          successor_id: "zyxwvuts-9876-5432-1098-rqponmlkjihg",
          dependency_type: "FS",
          lag: 0,
          predecessor_name: undefined,
          successor_name: undefined,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: null,
        },
      ],
      total: 1,
    };
    mockUseDependencies.mockReturnValue({
      data: noNameDeps,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    // Should show first 8 chars of the UUIDs
    expect(screen.getByText("abcdefgh")).toBeInTheDocument();
    expect(screen.getByText("zyxwvuts")).toBeInTheDocument();
  });

  it("renders table column headers", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Predecessor")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Successor")).toBeInTheDocument();
    expect(screen.getByText("Lag")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("does not show modal initially", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByTestId("dependency-form-modal")).not.toBeInTheDocument();
  });

  it("passes programId to useDependencies hook", () => {
    mockUseDependencies.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<DependencyList programId="test-program-42" />, { wrapper: Wrapper });

    expect(mockUseDependencies).toHaveBeenCalledWith("test-program-42");
  });

  it("renders delete button for each dependency row", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByLabelText("Delete dependency");
    expect(deleteButtons).toHaveLength(3);
  });

  it("does not render table in loading state", () => {
    mockUseDependencies.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByText("Predecessor")).not.toBeInTheDocument();
    expect(screen.queryByText("Add Dependency")).not.toBeInTheDocument();
  });

  it("does not render table in error state", () => {
    mockUseDependencies.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.queryByText("Predecessor")).not.toBeInTheDocument();
    expect(screen.queryByText("Add Dependency")).not.toBeInTheDocument();
  });

  it("handles data with null items gracefully", () => {
    mockUseDependencies.mockReturnValue({
      data: { items: undefined },
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    // Falls back to empty array via nullish coalescing
    expect(screen.getByText("No dependencies defined.")).toBeInTheDocument();
  });

  it("renders heading text", () => {
    mockUseDependencies.mockReturnValue({
      data: mockDependencies,
      isLoading: false,
      error: null,
    });

    render(<DependencyList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Dependencies")).toBeInTheDocument();
  });
});
