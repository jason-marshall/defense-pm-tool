import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourcePoolList } from "../ResourcePoolList";
import { ToastProvider } from "@/components/Toast";

const mockUseResourcePools = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useResourcePools", () => ({
  useResourcePools: (...args: unknown[]) => mockUseResourcePools(...args),
  useDeletePool: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
  useCreatePool: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdatePool: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  usePoolMembers: () => ({
    data: [],
    isLoading: false,
  }),
  useAddPoolMember: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useRemovePoolMember: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("@/hooks/useResources", () => ({
  useResources: () => ({
    data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
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

const mockPools = [
  {
    id: "pool-001",
    name: "Engineering Pool",
    code: "ENG-POOL",
    description: "Shared engineering resources",
    owner_id: "user-001",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "pool-002",
    name: "QA Pool",
    code: "QA-POOL",
    description: null,
    owner_id: "user-001",
    is_active: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

describe("ResourcePoolList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseResourcePools.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading resource pools...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseResourcePools.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed"),
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    expect(
      screen.getByText("Failed to load resource pools")
    ).toBeInTheDocument();
  });

  it("renders empty state", () => {
    mockUseResourcePools.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("No resource pools found")).toBeInTheDocument();
  });

  it("renders pools in table", () => {
    mockUseResourcePools.mockReturnValue({
      data: mockPools,
      isLoading: false,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("Engineering Pool")).toBeInTheDocument();
    expect(screen.getByText("QA Pool")).toBeInTheDocument();
    expect(screen.getByText("ENG-POOL")).toBeInTheDocument();
    expect(screen.getByText("QA-POOL")).toBeInTheDocument();
  });

  it("shows active/inactive status badges", () => {
    mockUseResourcePools.mockReturnValue({
      data: mockPools,
      isLoading: false,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    const statuses = screen.getAllByText(/Active|Inactive/);
    expect(statuses.length).toBeGreaterThanOrEqual(2);
  });

  it("renders New Pool button", () => {
    mockUseResourcePools.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    expect(screen.getByText("New Pool")).toBeInTheDocument();
  });

  it("opens form when New Pool clicked", () => {
    mockUseResourcePools.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("New Pool"));

    expect(screen.getByText("Create Resource Pool")).toBeInTheDocument();
  });

  it("calls delete mutation when Delete clicked", async () => {
    mockUseResourcePools.mockReturnValue({
      data: mockPools,
      isLoading: false,
      error: null,
    });
    mockDeleteMutateAsync.mockResolvedValue(undefined);

    render(<ResourcePoolList programId="prog-001" />, { wrapper: Wrapper });

    const deleteButtons = screen.getAllByTitle("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("pool-001");
    });
  });
});
