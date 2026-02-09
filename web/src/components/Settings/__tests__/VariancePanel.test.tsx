import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VariancePanel } from "../VariancePanel";
import { ToastProvider } from "@/components/Toast";

const mockUseVariancesByProgram = vi.fn();
const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useVariance", () => ({
  useVariancesByProgram: (...args: unknown[]) => mockUseVariancesByProgram(...args),
  useCreateVariance: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateVariance: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteVariance: () => ({
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

const mockVariances = {
  items: [
    {
      id: "var-1",
      program_id: "prog-1",
      wbs_id: null,
      period_id: null,
      created_by: "user-1",
      variance_type: "cost",
      variance_amount: "-5000",
      variance_percent: "-12.5",
      explanation: "Material cost overrun due to supply chain delays requiring renegotiation",
      corrective_action: "Renegotiate supplier contract",
      expected_resolution: "2026-06-01",
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-01T00:00:00Z",
      deleted_at: null,
    },
    {
      id: "var-2",
      program_id: "prog-1",
      wbs_id: null,
      period_id: null,
      created_by: "user-1",
      variance_type: "schedule",
      variance_amount: "-3000",
      variance_percent: "-8.0",
      explanation: "Integration testing delayed due to resource availability",
      corrective_action: null,
      expected_resolution: null,
      created_at: "2026-02-05T00:00:00Z",
      updated_at: "2026-02-05T00:00:00Z",
      deleted_at: null,
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
  pages: 1,
};

describe("VariancePanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: undefined, isLoading: true });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading variance explanations...")).toBeInTheDocument();
  });

  it("shows empty state when no variances exist", () => {
    mockUseVariancesByProgram.mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20, pages: 1 },
      isLoading: false,
    });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No variance explanations found.")).toBeInTheDocument();
  });

  it("displays variance explanations in table", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("cost")).toBeInTheDocument();
    expect(screen.getByText("schedule")).toBeInTheDocument();
    expect(screen.getByText("-12.5%")).toBeInTheDocument();
  });

  it("renders type filter", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    const select = screen.getAllByRole("combobox")[0];
    expect(select).toBeInTheDocument();
  });

  it("opens create form when Add is clicked", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));

    expect(screen.getByText("New Variance Explanation")).toBeInTheDocument();
    expect(screen.getByLabelText("Explanation")).toBeInTheDocument();
  });

  it("submits create form", async () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
    mockCreateMutateAsync.mockResolvedValue({});

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));
    fireEvent.change(screen.getByLabelText("Amount ($)"), { target: { value: "-5000" } });
    fireEvent.change(screen.getByLabelText("Percent (%)"), { target: { value: "-12.5" } });
    fireEvent.change(screen.getByLabelText("Explanation"), {
      target: { value: "A valid explanation that is at least 10 characters" },
    });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          program_id: "prog-1",
          variance_type: "cost",
          explanation: "A valid explanation that is at least 10 characters",
        })
      );
    });
  });

  it("cancels form", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));
    expect(screen.getByText("New Variance Explanation")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("New Variance Explanation")).not.toBeInTheDocument();
  });

  it("has Add button", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Add")).toBeInTheDocument();
  });
});
