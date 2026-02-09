import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProgramDetailPage } from "../ProgramDetailPage";
import { ToastProvider } from "@/components/Toast";
import type { Program } from "@/types/program";

// Mock the useProgram hook
const mockUseProgram = vi.fn();

vi.mock("@/hooks/usePrograms", () => ({
  useProgram: (...args: unknown[]) => mockUseProgram(...args),
}));

// Mock child components to avoid deep dependency trees
vi.mock("@/components/Programs/ProgramOverview", () => ({
  ProgramOverview: ({ program }: { program: Program }) => (
    <div data-testid="program-overview">Overview for {program.name}</div>
  ),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function renderWithRoute(programId: string) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/programs/${programId}`]}>
        <ToastProvider>
          <Routes>
            <Route path="/programs/:id/*" element={<ProgramDetailPage />} />
          </Routes>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockProgram: Program = {
  id: "prog-1",
  name: "F-35 Program",
  code: "F35-001",
  description: "Joint Strike Fighter",
  status: "ACTIVE",
  planned_start_date: "2026-01-01",
  planned_end_date: "2026-12-31",
  actual_start_date: null,
  actual_end_date: null,
  budget_at_completion: "5000000",
  contract_number: "FA-001",
  contract_type: "CPFF",
  owner_id: "user-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("ProgramDetailPage", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUseProgram.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderWithRoute("prog-1");

    expect(screen.getByText("Loading program...")).toBeInTheDocument();
  });

  it("renders error state when program not found", () => {
    mockUseProgram.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Not found"),
    });

    renderWithRoute("prog-1");

    expect(screen.getByText("Not found")).toBeInTheDocument();
  });

  it("renders program name and code when loaded", () => {
    mockUseProgram.mockReturnValue({
      data: mockProgram,
      isLoading: false,
      error: null,
    });

    renderWithRoute("prog-1");

    expect(screen.getByText("F-35 Program")).toBeInTheDocument();
    expect(screen.getByText("F35-001")).toBeInTheDocument();
  });

  it("renders all navigation tabs", () => {
    mockUseProgram.mockReturnValue({
      data: mockProgram,
      isLoading: false,
      error: null,
    });

    renderWithRoute("prog-1");

    expect(screen.getByRole("tab", { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /activities/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /dependencies/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /schedule/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /wbs/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /evms/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /resources/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /reports/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /scenarios/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /baselines/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /monte carlo/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /settings/i })).toBeInTheDocument();
  });

  it("shows overview content at root path", () => {
    mockUseProgram.mockReturnValue({
      data: mockProgram,
      isLoading: false,
      error: null,
    });

    renderWithRoute("prog-1");

    expect(screen.getByTestId("program-overview")).toBeInTheDocument();
    expect(screen.getByText("Overview for F-35 Program")).toBeInTheDocument();
  });

  it("shows 'Program not found' when data is null and no error", () => {
    mockUseProgram.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });

    renderWithRoute("prog-1");

    expect(screen.getByText("Program not found")).toBeInTheDocument();
  });
});
