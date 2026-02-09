import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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
});
