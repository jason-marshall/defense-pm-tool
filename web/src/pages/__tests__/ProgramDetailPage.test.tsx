import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, Outlet } from "react-router-dom";
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

function renderWithRoute(programId: string, initialPath?: string) {
  const entry = initialPath || `/programs/${programId}`;
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <ToastProvider>
          <Routes>
            <Route path="/programs/:id/*" element={<ProgramDetailPage />}>
              <Route path="activities" element={<div data-testid="activities-outlet">Activities Content</div>} />
              <Route path="dependencies" element={<div data-testid="dependencies-outlet">Dependencies Content</div>} />
              <Route path="schedule" element={<div data-testid="schedule-outlet">Schedule Content</div>} />
              <Route path="wbs" element={<div data-testid="wbs-outlet">WBS Content</div>} />
              <Route path="evms" element={<div data-testid="evms-outlet">EVMS Content</div>} />
              <Route path="resources" element={<div data-testid="resources-outlet">Resources Content</div>} />
              <Route path="reports" element={<div data-testid="reports-outlet">Reports Content</div>} />
              <Route path="scenarios" element={<div data-testid="scenarios-outlet">Scenarios Content</div>} />
              <Route path="baselines" element={<div data-testid="baselines-outlet">Baselines Content</div>} />
              <Route path="monte-carlo" element={<div data-testid="monte-carlo-outlet">Monte Carlo Content</div>} />
              <Route path="settings" element={<div data-testid="settings-outlet">Settings Content</div>} />
            </Route>
            <Route path="/programs" element={<div data-testid="programs-list">Programs List</div>} />
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

function mockLoadedProgram() {
  mockUseProgram.mockReturnValue({
    data: mockProgram,
    isLoading: false,
    error: null,
  });
}

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

  describe("loading state details", () => {
    it("does not render tabs during loading", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRoute("prog-1");

      expect(screen.getByText("Loading program...")).toBeInTheDocument();
      expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    });

    it("does not render program name during loading", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRoute("prog-1");

      expect(screen.queryByText("F-35 Program")).not.toBeInTheDocument();
    });

    it("renders loading message with appropriate styling", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRoute("prog-1");

      const loadingEl = screen.getByText("Loading program...");
      expect(loadingEl.className).toContain("text-gray-500");
    });
  });

  describe("error / not-found states", () => {
    it("renders generic error message for non-Error objects", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: "some string error",
      });

      renderWithRoute("prog-1");

      expect(screen.getByText("Program not found")).toBeInTheDocument();
    });

    it("renders custom error message from Error instance", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Server returned 500"),
      });

      renderWithRoute("prog-1");

      expect(screen.getByText("Server returned 500")).toBeInTheDocument();
    });

    it("renders error with red styling", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Access denied"),
      });

      renderWithRoute("prog-1");

      const errorEl = screen.getByText("Access denied");
      expect(errorEl.closest("div")?.className).toContain("text-red-500");
    });

    it("does not render tabs when error occurs", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Network error"),
      });

      renderWithRoute("prog-1");

      expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    });

    it("does not render tabs when program data is null", () => {
      mockUseProgram.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      renderWithRoute("prog-1");

      expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    });
  });

  describe("tab navigation to Activities", () => {
    it("navigates to activities tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const activitiesTab = screen.getByRole("tab", { name: /activities/i });
      await user.click(activitiesTab);

      expect(screen.getByTestId("activities-outlet")).toBeInTheDocument();
      expect(screen.getByText("Activities Content")).toBeInTheDocument();
      // Overview should no longer be visible
      expect(screen.queryByTestId("program-overview")).not.toBeInTheDocument();
    });
  });

  describe("tab navigation to Dependencies", () => {
    it("navigates to dependencies tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const dependenciesTab = screen.getByRole("tab", { name: /dependencies/i });
      await user.click(dependenciesTab);

      expect(screen.getByTestId("dependencies-outlet")).toBeInTheDocument();
      expect(screen.getByText("Dependencies Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Schedule", () => {
    it("navigates to schedule tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const scheduleTab = screen.getByRole("tab", { name: /schedule/i });
      await user.click(scheduleTab);

      expect(screen.getByTestId("schedule-outlet")).toBeInTheDocument();
      expect(screen.getByText("Schedule Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to WBS", () => {
    it("navigates to wbs tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const wbsTab = screen.getByRole("tab", { name: /wbs/i });
      await user.click(wbsTab);

      expect(screen.getByTestId("wbs-outlet")).toBeInTheDocument();
      expect(screen.getByText("WBS Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to EVMS", () => {
    it("navigates to evms tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const evmsTab = screen.getByRole("tab", { name: /evms/i });
      await user.click(evmsTab);

      expect(screen.getByTestId("evms-outlet")).toBeInTheDocument();
      expect(screen.getByText("EVMS Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Resources", () => {
    it("navigates to resources tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const resourcesTab = screen.getByRole("tab", { name: /resources/i });
      await user.click(resourcesTab);

      expect(screen.getByTestId("resources-outlet")).toBeInTheDocument();
      expect(screen.getByText("Resources Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Reports", () => {
    it("navigates to reports tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const reportsTab = screen.getByRole("tab", { name: /reports/i });
      await user.click(reportsTab);

      expect(screen.getByTestId("reports-outlet")).toBeInTheDocument();
      expect(screen.getByText("Reports Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Scenarios", () => {
    it("navigates to scenarios tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const scenariosTab = screen.getByRole("tab", { name: /scenarios/i });
      await user.click(scenariosTab);

      expect(screen.getByTestId("scenarios-outlet")).toBeInTheDocument();
      expect(screen.getByText("Scenarios Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Baselines", () => {
    it("navigates to baselines tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const baselinesTab = screen.getByRole("tab", { name: /baselines/i });
      await user.click(baselinesTab);

      expect(screen.getByTestId("baselines-outlet")).toBeInTheDocument();
      expect(screen.getByText("Baselines Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Monte Carlo", () => {
    it("navigates to monte-carlo tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const monteCarloTab = screen.getByRole("tab", { name: /monte carlo/i });
      await user.click(monteCarloTab);

      expect(screen.getByTestId("monte-carlo-outlet")).toBeInTheDocument();
      expect(screen.getByText("Monte Carlo Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation to Settings", () => {
    it("navigates to settings tab and renders outlet", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      const settingsTab = screen.getByRole("tab", { name: /settings/i });
      await user.click(settingsTab);

      expect(screen.getByTestId("settings-outlet")).toBeInTheDocument();
      expect(screen.getByText("Settings Content")).toBeInTheDocument();
    });
  });

  describe("tab navigation back to Overview", () => {
    it("returns to overview when clicking Overview tab from a sub-route", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1", "/programs/prog-1/activities");

      // Should be showing activities outlet initially
      expect(screen.getByTestId("activities-outlet")).toBeInTheDocument();
      expect(screen.queryByTestId("program-overview")).not.toBeInTheDocument();

      // Click Overview tab
      const overviewTab = screen.getByRole("tab", { name: /overview/i });
      await user.click(overviewTab);

      // Should now show overview
      expect(screen.getByTestId("program-overview")).toBeInTheDocument();
      expect(screen.queryByTestId("activities-outlet")).not.toBeInTheDocument();
    });
  });

  describe("direct sub-route rendering", () => {
    it("renders activities outlet when navigated directly to activities path", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/activities");

      expect(screen.getByTestId("activities-outlet")).toBeInTheDocument();
      expect(screen.queryByTestId("program-overview")).not.toBeInTheDocument();
    });

    it("renders dependencies outlet when navigated directly to dependencies path", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/dependencies");

      expect(screen.getByTestId("dependencies-outlet")).toBeInTheDocument();
    });

    it("renders schedule outlet when navigated directly to schedule path", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/schedule");

      expect(screen.getByTestId("schedule-outlet")).toBeInTheDocument();
    });

    it("renders monte-carlo outlet when navigated directly to monte-carlo path", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/monte-carlo");

      expect(screen.getByTestId("monte-carlo-outlet")).toBeInTheDocument();
    });

    it("renders settings outlet when navigated directly to settings path", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/settings");

      expect(screen.getByTestId("settings-outlet")).toBeInTheDocument();
    });
  });

  describe("sequential tab switching", () => {
    it("switches between multiple tabs correctly", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      // Start at overview
      expect(screen.getByTestId("program-overview")).toBeInTheDocument();

      // Go to activities
      await user.click(screen.getByRole("tab", { name: /activities/i }));
      expect(screen.getByTestId("activities-outlet")).toBeInTheDocument();
      expect(screen.queryByTestId("program-overview")).not.toBeInTheDocument();

      // Go to evms
      await user.click(screen.getByRole("tab", { name: /evms/i }));
      expect(screen.getByTestId("evms-outlet")).toBeInTheDocument();
      expect(screen.queryByTestId("activities-outlet")).not.toBeInTheDocument();

      // Go to settings
      await user.click(screen.getByRole("tab", { name: /settings/i }));
      expect(screen.getByTestId("settings-outlet")).toBeInTheDocument();
      expect(screen.queryByTestId("evms-outlet")).not.toBeInTheDocument();

      // Return to overview
      await user.click(screen.getByRole("tab", { name: /overview/i }));
      expect(screen.getByTestId("program-overview")).toBeInTheDocument();
      expect(screen.queryByTestId("settings-outlet")).not.toBeInTheDocument();
    });
  });

  describe("program header persistence", () => {
    it("keeps program name and code visible across tab navigations", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      // Verify header on overview
      expect(screen.getByText("F-35 Program")).toBeInTheDocument();
      expect(screen.getByText("F35-001")).toBeInTheDocument();

      // Navigate to activities
      await user.click(screen.getByRole("tab", { name: /activities/i }));

      // Header should still be visible
      expect(screen.getByText("F-35 Program")).toBeInTheDocument();
      expect(screen.getByText("F35-001")).toBeInTheDocument();

      // Navigate to settings
      await user.click(screen.getByRole("tab", { name: /settings/i }));

      // Header should still be visible
      expect(screen.getByText("F-35 Program")).toBeInTheDocument();
      expect(screen.getByText("F35-001")).toBeInTheDocument();
    });

    it("keeps all tabs visible when navigated to a sub-route", async () => {
      mockLoadedProgram();
      const user = userEvent.setup();

      renderWithRoute("prog-1");

      await user.click(screen.getByRole("tab", { name: /monte carlo/i }));

      // All 12 tabs should still be present
      const tablist = screen.getByRole("tablist");
      const tabs = within(tablist).getAllByRole("tab");
      expect(tabs).toHaveLength(12);
    });
  });

  describe("passes programId to useProgram", () => {
    it("calls useProgram with the route param id", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRoute("abc-123");

      expect(mockUseProgram).toHaveBeenCalledWith("abc-123");
    });

    it("calls useProgram with different program id", () => {
      mockUseProgram.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRoute("xyz-789");

      expect(mockUseProgram).toHaveBeenCalledWith("xyz-789");
    });
  });

  describe("tab link href values", () => {
    it("has correct href for each tab", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1");

      const expectedLinks: Record<string, string> = {
        "Overview": "/programs/prog-1",
        "Activities": "/programs/prog-1/activities",
        "Dependencies": "/programs/prog-1/dependencies",
        "Schedule": "/programs/prog-1/schedule",
        "WBS": "/programs/prog-1/wbs",
        "EVMS": "/programs/prog-1/evms",
        "Resources": "/programs/prog-1/resources",
        "Reports": "/programs/prog-1/reports",
        "Scenarios": "/programs/prog-1/scenarios",
        "Baselines": "/programs/prog-1/baselines",
        "Monte Carlo": "/programs/prog-1/monte-carlo",
        "Settings": "/programs/prog-1/settings",
      };

      for (const [label, href] of Object.entries(expectedLinks)) {
        const tab = screen.getByRole("tab", { name: new RegExp(label, "i") });
        expect(tab).toHaveAttribute("href", href);
      }
    });
  });

  describe("overview on trailing slash path", () => {
    it("renders overview when path has trailing slash", () => {
      mockLoadedProgram();

      renderWithRoute("prog-1", "/programs/prog-1/");

      expect(screen.getByTestId("program-overview")).toBeInTheDocument();
    });
  });
});
