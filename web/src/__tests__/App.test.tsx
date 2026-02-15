import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock all lazy-loaded components BEFORE importing App
vi.mock("../pages/LoginPage", () => ({
  LoginPage: () => <div data-testid="login-page">Login Page</div>,
}));
vi.mock("../pages/ProgramsPage", () => ({
  ProgramsPage: () => <div data-testid="programs-page">Programs Page</div>,
}));
vi.mock("../pages/ProgramDetailPage", () => ({
  ProgramDetailPage: () => <div data-testid="program-detail">Program Detail</div>,
}));
vi.mock("../components/Activities/ActivityList", () => ({
  ActivityList: ({ programId }: { programId: string }) => (
    <div data-testid="activity-list">Activities for {programId}</div>
  ),
}));
vi.mock("../components/Dependencies/DependencyList", () => ({
  DependencyList: ({ programId }: { programId: string }) => (
    <div data-testid="dependency-list">Dependencies for {programId}</div>
  ),
}));
vi.mock("../components/Schedule/ScheduleView", () => ({
  ScheduleView: ({ programId }: { programId: string }) => (
    <div data-testid="schedule-view">Schedule for {programId}</div>
  ),
}));
vi.mock("../components/WBSTree/WBSTree", () => ({
  WBSTree: ({ programId }: { programId: string }) => (
    <div data-testid="wbs-tree">WBS for {programId}</div>
  ),
}));
vi.mock("../components/EVMSDashboard/EVMSDashboard", () => ({
  EVMSDashboard: ({ programId }: { programId: string }) => (
    <div data-testid="evms-dashboard">EVMS for {programId}</div>
  ),
}));
vi.mock("../components/Resources/ResourceTab", () => ({
  ResourceTab: ({ programId }: { programId: string }) => (
    <div data-testid="resource-tab">Resources for {programId}</div>
  ),
}));
vi.mock("../components/Reports/ReportViewer", () => ({
  ReportViewer: ({ programId }: { programId: string }) => (
    <div data-testid="report-viewer">Reports for {programId}</div>
  ),
}));
vi.mock("../components/Scenarios/ScenarioList", () => ({
  ScenarioList: ({ programId }: { programId: string }) => (
    <div data-testid="scenario-list">Scenarios for {programId}</div>
  ),
}));
vi.mock("../components/Baselines/BaselineList", () => ({
  BaselineList: ({ programId }: { programId: string }) => (
    <div data-testid="baseline-list">Baselines for {programId}</div>
  ),
}));
vi.mock("../components/MonteCarlo/MonteCarloPanel", () => ({
  MonteCarloPanel: ({ programId }: { programId: string }) => (
    <div data-testid="monte-carlo">Monte Carlo for {programId}</div>
  ),
}));
vi.mock("../components/Programs/ProgramSettings", () => ({
  ProgramSettings: ({ programId }: { programId: string }) => (
    <div data-testid="program-settings">Settings for {programId}</div>
  ),
}));

// Mock ErrorBoundary to just render children
vi.mock("../components/ErrorBoundary", () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="error-boundary">{children}</div>
  ),
}));

// Mock Toast
vi.mock("../components/Toast", () => ({
  ToastProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="toast-provider">{children}</div>
  ),
}));

// Mock Skeleton
vi.mock("../components/Skeleton", () => ({
  DashboardSkeleton: () => <div data-testid="skeleton">Loading...</div>,
}));

// Mock AppLayout to render Outlet
vi.mock("../components/Layout/AppLayout", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Outlet } = require("react-router-dom");
  return {
    AppLayout: () => (
      <div data-testid="app-layout">
        <Outlet />
      </div>
    ),
  };
});

// Mock ProtectedRoute
const mockUseAuth = vi.fn();
vi.mock("../contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="auth-provider">{children}</div>
  ),
  useAuth: () => mockUseAuth(),
}));

vi.mock("../components/ProtectedRoute", () => ({
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="protected-route">{children}</div>
  ),
}));

// Static import AFTER mocks
import { App } from "../App";

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { full_name: "Test User" },
      logout: vi.fn(),
    });
  });

  describe("App component", () => {
    it("renders without crashing", () => {
      render(<App />);
      expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
    });

    it("wraps content with AuthProvider", () => {
      render(<App />);
      expect(screen.getByTestId("auth-provider")).toBeInTheDocument();
    });

    it("wraps content with ToastProvider", () => {
      render(<App />);
      expect(screen.getByTestId("toast-provider")).toBeInTheDocument();
    });

    it("wraps content with ProtectedRoute for main routes", () => {
      render(<App />);
      expect(screen.getByTestId("protected-route")).toBeInTheDocument();
    });
  });

  describe("Home component", () => {
    it("renders the home page with title", () => {
      render(<App />);
      expect(
        screen.getByText("Defense Program Management Tool")
      ).toBeInTheDocument();
    });

    it("renders the subtitle", () => {
      render(<App />);
      expect(
        screen.getByText("EVMS/DFARS Compliant Project Management")
      ).toBeInTheDocument();
    });

    it("renders View Programs link pointing to /programs", () => {
      render(<App />);
      const link = screen.getByText("View Programs");
      expect(link).toBeInTheDocument();
      expect(link.closest("a")).toHaveAttribute("href", "/programs");
    });

    it("renders all three feature cards", () => {
      render(<App />);
      expect(screen.getByText("EVMS Compliance")).toBeInTheDocument();
      expect(screen.getByText("CPM Scheduling")).toBeInTheDocument();
      expect(screen.getByText("Monte Carlo Analysis")).toBeInTheDocument();
    });

    it("renders feature card descriptions", () => {
      render(<App />);
      expect(screen.getByText(/Full ANSI\/EIA-748/)).toBeInTheDocument();
      expect(screen.getByText(/Critical Path Method scheduling/)).toBeInTheDocument();
      expect(screen.getByText(/Schedule risk analysis/)).toBeInTheDocument();
    });
  });

  describe("Route configuration", () => {
    it("has an app-layout wrapper for protected routes", () => {
      render(<App />);
      expect(screen.getByTestId("app-layout")).toBeInTheDocument();
    });
  });
});
