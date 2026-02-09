import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PoolMembersPanel } from "../PoolMembersPanel";
import { ToastProvider } from "@/components/Toast";

const mockUsePoolMembers = vi.fn();
const mockAddMutateAsync = vi.fn();
const mockRemoveMutateAsync = vi.fn();

vi.mock("@/hooks/useResourcePools", () => ({
  usePoolMembers: (...args: unknown[]) => mockUsePoolMembers(...args),
  useAddPoolMember: () => ({
    mutateAsync: mockAddMutateAsync,
    isPending: false,
  }),
  useRemovePoolMember: () => ({
    mutateAsync: mockRemoveMutateAsync,
    isPending: false,
  }),
}));

vi.mock("@/hooks/useResources", () => ({
  useResources: () => ({
    data: {
      items: [
        { id: "res-001", code: "ENG-001", name: "Engineer 1" },
        { id: "res-002", code: "ENG-002", name: "Engineer 2" },
      ],
      total: 2,
      page: 1,
      page_size: 20,
      pages: 1,
    },
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

const mockMembers = [
  {
    id: "member-001",
    pool_id: "pool-001",
    resource_id: "res-001",
    allocation_percentage: "100.00",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  },
];

describe("PoolMembersPanel", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders panel with pool name", () => {
    mockUsePoolMembers.mockReturnValue({ data: [], isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(
      screen.getByText("Members - Engineering Pool")
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockUsePoolMembers.mockReturnValue({ data: undefined, isLoading: true });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Loading members...")).toBeInTheDocument();
  });

  it("shows empty state when no members", () => {
    mockUsePoolMembers.mockReturnValue({ data: [], isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("No members in this pool")).toBeInTheDocument();
  });

  it("renders members in table", () => {
    mockUsePoolMembers.mockReturnValue({ data: mockMembers, isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("shows add member form", () => {
    mockUsePoolMembers.mockReturnValue({ data: [], isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByLabelText("Resource")).toBeInTheDocument();
    expect(screen.getByLabelText("Allocation %")).toBeInTheDocument();
    expect(screen.getByText("Add")).toBeInTheDocument();
  });

  it("filters available resources excluding existing members", () => {
    mockUsePoolMembers.mockReturnValue({ data: mockMembers, isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    // res-001 is already a member so only res-002 should be available
    const select = screen.getByLabelText("Resource");
    expect(select).toBeInTheDocument();
    // Engineer 2 should be available, Engineer 1 should not be in the dropdown
    expect(screen.getByText("ENG-002 - Engineer 2")).toBeInTheDocument();
    expect(screen.queryByText("ENG-001 - Engineer 1")).not.toBeInTheDocument();
  });

  it("calls onClose when Close clicked", () => {
    mockUsePoolMembers.mockReturnValue({ data: [], isLoading: false });

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls add mutation when Add clicked", async () => {
    mockUsePoolMembers.mockReturnValue({ data: [], isLoading: false });
    mockAddMutateAsync.mockResolvedValue({});

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Resource"), {
      target: { value: "res-002" },
    });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(mockAddMutateAsync).toHaveBeenCalledWith({
        poolId: "pool-001",
        data: {
          resource_id: "res-002",
          allocation_percentage: 100,
        },
      });
    });
  });

  it("calls remove mutation when Remove clicked", async () => {
    mockUsePoolMembers.mockReturnValue({ data: mockMembers, isLoading: false });
    mockRemoveMutateAsync.mockResolvedValue(undefined);

    render(
      <PoolMembersPanel
        poolId="pool-001"
        poolName="Engineering Pool"
        programId="prog-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByTitle("Remove"));

    await waitFor(() => {
      expect(mockRemoveMutateAsync).toHaveBeenCalledWith({
        poolId: "pool-001",
        memberId: "member-001",
      });
    });
  });
});
