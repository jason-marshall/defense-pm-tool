import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportViewer } from "../ReportViewer";
import { ToastProvider } from "@/components/Toast";

// Mock the sub-components to avoid deep dependency trees
vi.mock("../CPRFormat1", () => ({
  CPRFormat1: ({ programId }: { programId: string }) => (
    <div data-testid="cpr-format1">Format 1 for {programId}</div>
  ),
}));

vi.mock("../CPRFormat3", () => ({
  CPRFormat3: ({ programId }: { programId: string }) => (
    <div data-testid="cpr-format3">Format 3 for {programId}</div>
  ),
}));

vi.mock("../CPRFormat5", () => ({
  CPRFormat5: ({ programId }: { programId: string }) => (
    <div data-testid="cpr-format5">Format 5 for {programId}</div>
  ),
}));

vi.mock("../ReportAuditTrail", () => ({
  ReportAuditTrail: ({ programId }: { programId: string }) => (
    <div data-testid="audit-trail">Audit Trail for {programId}</div>
  ),
}));

vi.mock("@/services/reportApi", () => ({
  downloadReportPDF: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

describe("ReportViewer", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders the report viewer with heading", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("CPR Reports")).toBeInTheDocument();
  });

  it("renders all format tabs", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Format 1 (WBS)")).toBeInTheDocument();
    expect(screen.getByText("Format 3 (Baseline)")).toBeInTheDocument();
    expect(screen.getByText("Format 5 (Variance)")).toBeInTheDocument();
    expect(screen.getByText("Audit Trail")).toBeInTheDocument();
  });

  it("shows Format 1 content by default", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByTestId("cpr-format1")).toBeInTheDocument();
    expect(screen.queryByTestId("cpr-format3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cpr-format5")).not.toBeInTheDocument();
    expect(screen.queryByTestId("audit-trail")).not.toBeInTheDocument();
  });

  it("switches to Format 3 when clicked", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Format 3 (Baseline)"));

    expect(screen.queryByTestId("cpr-format1")).not.toBeInTheDocument();
    expect(screen.getByTestId("cpr-format3")).toBeInTheDocument();
  });

  it("switches to Format 5 when clicked", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Format 5 (Variance)"));

    expect(screen.queryByTestId("cpr-format1")).not.toBeInTheDocument();
    expect(screen.getByTestId("cpr-format5")).toBeInTheDocument();
  });

  it("switches to Audit Trail and hides PDF download button", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    // PDF button visible on Format 1
    expect(screen.getByText("Download PDF")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Audit Trail"));

    expect(screen.getByTestId("audit-trail")).toBeInTheDocument();
    expect(screen.queryByText("Download PDF")).not.toBeInTheDocument();
  });

  it("shows Download PDF button for format tabs", () => {
    render(<ReportViewer programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Download PDF")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Format 3 (Baseline)"));
    expect(screen.getByText("Download PDF")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Format 5 (Variance)"));
    expect(screen.getByText("Download PDF")).toBeInTheDocument();
  });
});
