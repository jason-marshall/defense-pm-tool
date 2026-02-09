import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourcePoolForm } from "../ResourcePoolForm";
import { ToastProvider } from "@/components/Toast";

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

vi.mock("@/hooks/useResourcePools", () => ({
  useCreatePool: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdatePool: () => ({
    mutateAsync: mockUpdateMutateAsync,
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

describe("ResourcePoolForm", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders create form", () => {
    render(<ResourcePoolForm onClose={onClose} />, { wrapper: Wrapper });

    expect(screen.getByText("Create Resource Pool")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Code")).toBeInTheDocument();
    expect(screen.getByLabelText("Description (optional)")).toBeInTheDocument();
  });

  it("renders edit form with pool data", () => {
    const pool = {
      id: "pool-001",
      name: "Engineering Pool",
      code: "ENG-POOL",
      description: "Shared resources",
      owner_id: "user-001",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    render(<ResourcePoolForm pool={pool} onClose={onClose} />, {
      wrapper: Wrapper,
    });

    expect(screen.getByText("Edit Pool")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Engineering Pool")).toBeInTheDocument();
  });

  it("hides code field in edit mode", () => {
    const pool = {
      id: "pool-001",
      name: "Engineering Pool",
      code: "ENG-POOL",
      description: null,
      owner_id: "user-001",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    render(<ResourcePoolForm pool={pool} onClose={onClose} />, {
      wrapper: Wrapper,
    });

    expect(screen.queryByLabelText("Code")).not.toBeInTheDocument();
  });

  it("calls onClose when Cancel clicked", () => {
    render(<ResourcePoolForm onClose={onClose} />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls create mutation on submit", async () => {
    mockCreateMutateAsync.mockResolvedValue({});

    render(<ResourcePoolForm onClose={onClose} />, { wrapper: Wrapper });

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "New Pool" },
    });
    fireEvent.change(screen.getByLabelText("Code"), {
      target: { value: "NEW-POOL" },
    });
    fireEvent.click(screen.getByText("Create Pool"));

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith({
        name: "New Pool",
        code: "NEW-POOL",
        description: undefined,
      });
    });
  });

  it("calls update mutation when editing", async () => {
    const pool = {
      id: "pool-001",
      name: "Engineering Pool",
      code: "ENG-POOL",
      description: null,
      owner_id: "user-001",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockUpdateMutateAsync.mockResolvedValue({});

    render(<ResourcePoolForm pool={pool} onClose={onClose} />, {
      wrapper: Wrapper,
    });

    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Updated Pool" },
    });
    fireEvent.click(screen.getByText("Update Pool"));

    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
        poolId: "pool-001",
        data: {
          name: "Updated Pool",
          description: undefined,
        },
      });
    });
  });
});
