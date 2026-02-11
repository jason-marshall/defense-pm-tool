import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CPRFormat3 } from "../CPRFormat3";
import { ToastProvider } from "@/components/Toast";
import type { CPRFormat3Report } from "@/types/report";

const mockUseCPRFormat3 = vi.fn();

vi.mock("@/hooks/useReports", () => ({
  useCPRFormat3: (...args: unknown[]) => mockUseCPRFormat3(...args),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockReport: CPRFormat3Report = {
  program_id: "prog-1",
  program_name: "Test Program Beta",
  periods: [
    { period: "2026-01", bcws: "5000", bcwp: "4500", acwp: "4800" },
    { period: "2026-02", bcws: "8000", bcwp: "7500", acwp: "7200" },
  ],
  cumulative: [
    { period: "2026-01", bcws: "5000", bcwp: "4500", acwp: "4800" },
    { period: "2026-02", bcws: "13000", bcwp: "12000", acwp: "12000" },
  ],
};

describe("CPRFormat3", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseCPRFormat3.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<CPRFormat3 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading Format 3...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUseCPRFormat3.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Server error"),
    });

    render(<CPRFormat3 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading report")).toBeInTheDocument();
  });

  it("shows empty state when no periods", () => {
    mockUseCPRFormat3.mockReturnValue({
      data: { ...mockReport, periods: [] },
      isLoading: false,
      error: null,
    });

    render(<CPRFormat3 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No time-phased data")).toBeInTheDocument();
  });

  it("renders period table with data", () => {
    mockUseCPRFormat3.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    render(<CPRFormat3 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Test Program Beta")).toBeInTheDocument();
    expect(
      screen.getByText("Time-Phased Performance Measurement Baseline")
    ).toBeInTheDocument();

    // Column headers
    expect(screen.getByText("Period")).toBeInTheDocument();
    expect(screen.getByText("BCWS")).toBeInTheDocument();
    expect(screen.getByText("BCWP")).toBeInTheDocument();
    expect(screen.getByText("ACWP")).toBeInTheDocument();

    // Row data
    expect(screen.getByText("2026-01")).toBeInTheDocument();
    expect(screen.getByText("2026-02")).toBeInTheDocument();
  });
});
