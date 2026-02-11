import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CPRFormat5 } from "../CPRFormat5";
import { ToastProvider } from "@/components/Toast";
import type { CPRFormat5Report } from "@/types/report";

const mockUseCPRFormat5 = vi.fn();

vi.mock("@/hooks/useReports", () => ({
  useCPRFormat5: (...args: unknown[]) => mockUseCPRFormat5(...args),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockReport: CPRFormat5Report = {
  program_id: "prog-1",
  program_name: "Test Program Gamma",
  items: [
    {
      wbs_code: "1.1",
      wbs_name: "Design Phase",
      variance_type: "cost",
      variance_amount: "-5000",
      explanation: "Material costs exceeded estimates",
      corrective_action: "Renegotiate supplier contracts",
    },
    {
      wbs_code: "1.2",
      wbs_name: "Build Phase",
      variance_type: "schedule",
      variance_amount: "-3000",
      explanation: "Late delivery of components",
      corrective_action: null,
    },
  ],
};

describe("CPRFormat5", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(<CPRFormat5 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading Format 5...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Server error"),
    });

    render(<CPRFormat5 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Error loading report")).toBeInTheDocument();
  });

  it("shows empty state when no items", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: { ...mockReport, items: [] },
      isLoading: false,
      error: null,
    });

    render(<CPRFormat5 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No variance explanations")).toBeInTheDocument();
  });

  it("renders variance items with explanations", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    render(<CPRFormat5 programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Test Program Gamma")).toBeInTheDocument();
    expect(screen.getByText("Variance Analysis Report")).toBeInTheDocument();

    // Item data
    expect(screen.getByText("1.1")).toBeInTheDocument();
    expect(screen.getByText("Design Phase")).toBeInTheDocument();
    expect(screen.getByText("Material costs exceeded estimates")).toBeInTheDocument();
    expect(screen.getByText("1.2")).toBeInTheDocument();
    expect(screen.getByText("Build Phase")).toBeInTheDocument();
    expect(screen.getByText("Late delivery of components")).toBeInTheDocument();
  });

  it("shows corrective action only when present", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    render(<CPRFormat5 programId="prog-1" />, { wrapper: Wrapper });

    // First item has corrective action
    expect(
      screen.getByText("Renegotiate supplier contracts")
    ).toBeInTheDocument();

    // "Corrective Action:" label appears once (only for the item that has one)
    const labels = screen.getAllByText("Corrective Action:");
    expect(labels).toHaveLength(1);
  });

  it("applies correct color for cost vs schedule variance types", () => {
    mockUseCPRFormat5.mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
    });

    const { container } = render(<CPRFormat5 programId="prog-1" />, {
      wrapper: Wrapper,
    });

    // Cost variance should have text-red-600
    const redElements = container.querySelectorAll(".text-red-600");
    expect(redElements.length).toBeGreaterThan(0);

    // Schedule variance should have text-amber-600
    const amberElements = container.querySelectorAll(".text-amber-600");
    expect(amberElements.length).toBeGreaterThan(0);
  });
});
