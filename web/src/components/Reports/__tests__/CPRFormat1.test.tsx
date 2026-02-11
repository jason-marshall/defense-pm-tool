import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CPRFormat1 } from "../CPRFormat1";
import { ToastProvider } from "@/components/Toast";
import type { CPRFormat1Report } from "@/types/report";

const mockUseCPRFormat1 = vi.fn();

vi.mock("@/hooks/useReports", () => ({
  useCPRFormat1: (...args: unknown[]) => mockUseCPRFormat1(...args),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockReport: CPRFormat1Report = {
  program_id: "prog-1",
  program_name: "Test Program Alpha",
  reporting_period: "2026-01",
  rows: [
    {
      wbs_code: "1.1",
      wbs_name: "Design Phase",
      bcws: "10000",
      bcwp: "9000",
      acwp: "11000",
      cv: "-2000",
      sv: "-1000",
      cv_percent: "-18.18",
      sv_percent: "-10.00",
    },
    {
      wbs_code: "1.2",
      wbs_name: "Build Phase",
      bcws: "20000",
      bcwp: "22000",
      acwp: "19000",
      cv: "3000",
      sv: "2000",
      cv_percent: "15.79",
      sv_percent: "10.00",
    },
  ],
  totals: {
    wbs_code: "",
    wbs_name: "Total",
    bcws: "30000",
    bcwp: "31000",
    acwp: "30000",
    cv: "1000",
    sv: "1000",
    cv_percent: "3.33",
    sv_percent: "3.33",
  },
};

describe("CPRFormat1", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseCPRFormat1.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<CPRFormat1 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading Format 1...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUseCPRFormat1.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    });

    render(<CPRFormat1 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading report")).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    mockUseCPRFormat1.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    render(<CPRFormat1 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No report data")).toBeInTheDocument();
  });

  it("renders WBS table with data rows and totals", () => {
    mockUseCPRFormat1.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    render(<CPRFormat1 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Test Program Alpha")).toBeInTheDocument();
    expect(screen.getByText("Period: 2026-01")).toBeInTheDocument();

    // Column headers
    expect(screen.getByText("WBS")).toBeInTheDocument();
    expect(screen.getByText("BCWS")).toBeInTheDocument();
    expect(screen.getByText("BCWP")).toBeInTheDocument();
    expect(screen.getByText("ACWP")).toBeInTheDocument();
    expect(screen.getByText("CV")).toBeInTheDocument();
    expect(screen.getByText("SV")).toBeInTheDocument();

    // Row data
    expect(screen.getByText("1.1")).toBeInTheDocument();
    expect(screen.getByText("Design Phase")).toBeInTheDocument();
    expect(screen.getByText("1.2")).toBeInTheDocument();
    expect(screen.getByText("Build Phase")).toBeInTheDocument();

    // Totals footer
    expect(screen.getByText("Total")).toBeInTheDocument();
  });

  it("applies red color for negative variance and green for positive", () => {
    mockUseCPRFormat1.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    const { container } = render(<CPRFormat1 programId="prog-1" />, {
      wrapper: Wrapper,
    });

    // Negative CV (-2000) on first row should have text-red-600
    const redCells = container.querySelectorAll(".text-red-600");
    expect(redCells.length).toBeGreaterThan(0);

    // Positive CV (3000) on second row should have text-green-600
    const greenCells = container.querySelectorAll(".text-green-600");
    expect(greenCells.length).toBeGreaterThan(0);
  });
});
