import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ManagementReservePanel } from "../ManagementReservePanel";
import { ToastProvider } from "@/components/Toast";

const mockUseMRStatus = vi.fn();
const mockUseMRHistory = vi.fn();
const mockInitMutateAsync = vi.fn();
const mockChangeMutateAsync = vi.fn();

vi.mock("@/hooks/useMR", () => ({
  useMRStatus: (...args: unknown[]) => mockUseMRStatus(...args),
  useMRHistory: (...args: unknown[]) => mockUseMRHistory(...args),
  useInitializeMR: () => ({
    mutateAsync: mockInitMutateAsync,
    isPending: false,
  }),
  useRecordMRChange: () => ({
    mutateAsync: mockChangeMutateAsync,
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

const mockStatus = {
  program_id: "prog-1",
  current_balance: "50000",
  initial_mr: "100000",
  total_changes_in: "10000",
  total_changes_out: "60000",
  change_count: 3,
  last_change_at: "2026-02-01T12:00:00Z",
};

const mockHistory = {
  items: [
    {
      id: "log-1",
      program_id: "prog-1",
      period_id: null,
      beginning_mr: "0",
      changes_in: "100000",
      changes_out: "0",
      ending_mr: "100000",
      reason: "Initial allocation",
      approved_by: "user-1",
      created_at: "2026-01-01T12:00:00Z",
    },
  ],
  total: 1,
  program_id: "prog-1",
  current_balance: "100000",
};

describe("ManagementReservePanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseMRStatus.mockReturnValue({ data: undefined, isLoading: true });
    mockUseMRHistory.mockReturnValue({ data: undefined, isLoading: true });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading Management Reserve...")).toBeInTheDocument();
  });

  it("shows initialize form when MR is not yet set up", () => {
    mockUseMRStatus.mockReturnValue({
      data: { ...mockStatus, change_count: 0 },
      isLoading: false,
    });
    mockUseMRHistory.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Initialize Management Reserve")).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Amount/)).toBeInTheDocument();
  });

  it("shows status cards when initialized", () => {
    mockUseMRStatus.mockReturnValue({ data: mockStatus, isLoading: false });
    mockUseMRHistory.mockReturnValue({ data: mockHistory, isLoading: false });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Current Balance")).toBeInTheDocument();
    expect(screen.getByText("$50,000")).toBeInTheDocument();
    expect(screen.getByText("Total In")).toBeInTheDocument();
    expect(screen.getByText("Total Out")).toBeInTheDocument();
  });

  it("shows record change form when initialized", () => {
    mockUseMRStatus.mockReturnValue({ data: mockStatus, isLoading: false });
    mockUseMRHistory.mockReturnValue({ data: mockHistory, isLoading: false });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Record MR Change")).toBeInTheDocument();
    expect(screen.getByLabelText(/Add to MR/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Release from MR/)).toBeInTheDocument();
  });

  it("shows history table with entries", () => {
    mockUseMRStatus.mockReturnValue({ data: mockStatus, isLoading: false });
    mockUseMRHistory.mockReturnValue({ data: mockHistory, isLoading: false });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("MR History")).toBeInTheDocument();
    expect(screen.getByText("Initial allocation")).toBeInTheDocument();
  });

  it("calls initialize mutation", async () => {
    mockUseMRStatus.mockReturnValue({
      data: { ...mockStatus, change_count: 0 },
      isLoading: false,
    });
    mockUseMRHistory.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false });
    mockInitMutateAsync.mockResolvedValue({});

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.change(screen.getByLabelText(/Initial Amount/), {
      target: { value: "100000" },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "Initial allocation" },
    });
    fireEvent.click(screen.getByText("Initialize MR"));

    await waitFor(() => {
      expect(mockInitMutateAsync).toHaveBeenCalledWith({
        programId: "prog-1",
        initialAmount: "100000",
        reason: "Initial allocation",
      });
    });
  });

  it("calls record change mutation", async () => {
    mockUseMRStatus.mockReturnValue({ data: mockStatus, isLoading: false });
    mockUseMRHistory.mockReturnValue({ data: mockHistory, isLoading: false });
    mockChangeMutateAsync.mockResolvedValue({});

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.change(screen.getByLabelText(/Release from MR/), {
      target: { value: "5000" },
    });
    fireEvent.change(screen.getByLabelText(/Reason/i), {
      target: { value: "Release to WP" },
    });
    fireEvent.click(screen.getByText("Record Change"));

    await waitFor(() => {
      expect(mockChangeMutateAsync).toHaveBeenCalledWith({
        programId: "prog-1",
        data: {
          changes_in: "0",
          changes_out: "5000",
          reason: "Release to WP",
        },
      });
    });
  });

  it("shows empty history message", () => {
    mockUseMRStatus.mockReturnValue({
      data: { ...mockStatus, change_count: 0 },
      isLoading: false,
    });
    mockUseMRHistory.mockReturnValue({
      data: { items: [], total: 0, program_id: "prog-1", current_balance: "0" },
      isLoading: false,
    });

    render(<ManagementReservePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No MR history records.")).toBeInTheDocument();
  });
});
