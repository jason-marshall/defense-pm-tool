import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EVMSDashboard } from "./EVMSDashboard";

vi.mock("@/services/evmsApi", () => ({
  getEVMSSummary: vi.fn(),
  getEVMSPeriods: vi.fn(),
  getEVMSPeriodWithData: vi.fn(),
  createEVMSPeriod: vi.fn(),
  addPeriodData: vi.fn(),
  deleteEVMSPeriod: vi.fn(),
}));

import { getEVMSSummary } from "@/services/evmsApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockSummary = {
  programId: "prog-1",
  programName: "Test Program",
  budgetAtCompletion: "1000000.00",
  cumulativeBcws: "500000.00",
  cumulativeBcwp: "450000.00",
  cumulativeAcwp: "480000.00",
  costVariance: "-30000.00",
  scheduleVariance: "-50000.00",
  cpi: "0.94",
  spi: "0.90",
  estimateAtCompletion: "1063829.79",
  estimateToComplete: "583829.79",
  varianceAtCompletion: "-63829.79",
  tcpiEac: "0.94",
  tcpiBac: "1.06",
  percentComplete: "45.0",
  percentSpent: "48.0",
  latestPeriod: {
    periodName: "Jan 2026",
    periodStart: "2026-01-01",
    periodEnd: "2026-01-31",
    status: "approved",
  },
};

describe("EVMSDashboard", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(getEVMSSummary).mockImplementation(() => new Promise(() => {}));

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(screen.getByText("Loading EVMS metrics...")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    vi.mocked(getEVMSSummary).mockRejectedValue(new Error("API Error"));

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(await screen.findByText(/Error loading EVMS data/)).toBeInTheDocument();
    expect(screen.getByText(/API Error/)).toBeInTheDocument();
  });

  it("renders no data state when summary is null", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(null as any);

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/No EVMS data available/)
    ).toBeInTheDocument();
  });

  it("renders no data state when all values are zero", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue({
      ...mockSummary,
      cumulativeBcws: "0.00",
      cumulativeBcwp: "0.00",
      cumulativeAcwp: "0.00",
    });

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/No EVMS period data has been recorded/)
    ).toBeInTheDocument();
  });

  it("renders dashboard with data", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(await screen.findByText("EVMS Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Test Program")).toBeInTheDocument();
  });

  it("uses programName prop when provided", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    render(
      <EVMSDashboard programId="prog-1" programName="Custom Name" />,
      { wrapper }
    );

    expect(await screen.findByText("Custom Name")).toBeInTheDocument();
  });

  it("shows progress section with percentages", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(await screen.findByText("Progress Overview")).toBeInTheDocument();
    expect(
      screen.getByText(/45\.0% complete \/ 48\.0% spent/)
    ).toBeInTheDocument();
  });

  it("shows cost overrun warning when spent > complete", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/Cost overrun risk detected/)
    ).toBeInTheDocument();
  });

  it("shows latest period info", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue(mockSummary);

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText("Latest Reporting Period")
    ).toBeInTheDocument();
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
    expect(screen.getByText("approved")).toBeInTheDocument();
  });

  it("does not show overrun warning when spent < complete", async () => {
    vi.mocked(getEVMSSummary).mockResolvedValue({
      ...mockSummary,
      percentComplete: "50.0",
      percentSpent: "40.0",
    });

    render(<EVMSDashboard programId="prog-1" />, { wrapper });

    await screen.findByText("Progress Overview");
    expect(
      screen.queryByText(/Cost overrun risk detected/)
    ).not.toBeInTheDocument();
  });
});
