/**
 * Unit tests for GanttResourceView component.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GanttResourceView } from "../GanttResourceView";

// Mock the API client
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

// Import the mocked client
import { apiClient } from "@/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockResources = {
  items: [
    {
      id: "res-1",
      code: "ENG-001",
      name: "Senior Engineer",
      resource_type: "LABOR",
      capacity_per_day: "8.0",
    },
    {
      id: "res-2",
      code: "EQP-001",
      name: "Crane A",
      resource_type: "EQUIPMENT",
      capacity_per_day: "10.0",
    },
  ],
};

const mockAssignments = {
  items: [
    {
      id: "assign-1",
      activity_id: "act-1",
      start_date: "2026-02-01",
      finish_date: "2026-02-10",
      units: "1.0",
      activity: {
        code: "ACT-001",
        name: "Design Review",
        early_start: "2026-02-01",
        early_finish: "2026-02-10",
        is_critical: false,
      },
    },
  ],
};

describe("GanttResourceView", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(apiClient.get).mockImplementation(() => new Promise(() => {}));

    render(<GanttResourceView programId="test-program" />, { wrapper });

    expect(screen.getByTestId("gantt-loading")).toBeInTheDocument();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders scale selector buttons", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("scale-day")).toBeInTheDocument();
    });

    expect(screen.getByTestId("scale-week")).toBeInTheDocument();
    expect(screen.getByTestId("scale-month")).toBeInTheDocument();
  });

  it("renders resource sidebar with resources", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("resource-sidebar")).toBeInTheDocument();
    });

    expect(screen.getByText("ENG-001")).toBeInTheDocument();
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText("EQP-001")).toBeInTheDocument();
    expect(screen.getByText("Crane A")).toBeInTheDocument();
  });

  it("toggles utilization display", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("toggle-utilization")).toBeInTheDocument();
    });

    const toggle = screen.getByTestId("toggle-utilization");
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
  });

  it("toggles overallocation highlight", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("toggle-overallocation")).toBeInTheDocument();
    });

    const toggle = screen.getByTestId("toggle-overallocation");
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();
  });

  it("changes scale when scale button is clicked", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("scale-day")).toBeInTheDocument();
    });

    // Default is week
    expect(screen.getByTestId("scale-week")).toHaveClass("active");

    // Click day
    fireEvent.click(screen.getByTestId("scale-day"));
    expect(screen.getByTestId("scale-day")).toHaveClass("active");
    expect(screen.getByTestId("scale-week")).not.toHaveClass("active");

    // Click month
    fireEvent.click(screen.getByTestId("scale-month"));
    expect(screen.getByTestId("scale-month")).toHaveClass("active");
    expect(screen.getByTestId("scale-day")).not.toHaveClass("active");
  });

  it("renders error state when API fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("API Error"));

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("gantt-error")).toBeInTheDocument();
    });

    expect(screen.getByText(/API Error/)).toBeInTheDocument();
  });

  it("renders timeline header", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("resource-timeline")).toBeInTheDocument();
    });
  });

  it("calls onAssignmentClick when assignment is clicked", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    // Only return assignments for the first resource
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockAssignments });
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { items: [] } });

    const handleClick = vi.fn();

    render(
      <GanttResourceView
        programId="test-program"
        onAssignmentClick={handleClick}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByTestId("assignment-bar-assign-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("assignment-bar-assign-1"));
    expect(handleClick).toHaveBeenCalledWith("assign-1");
  });

  it("filters resources when resourceFilter is provided", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(
      <GanttResourceView programId="test-program" resourceFilter={["res-1"]} />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByText("ENG-001")).toBeInTheDocument();
    });

    expect(screen.queryByText("EQP-001")).not.toBeInTheDocument();
  });
});

describe("ResourceSidebar", () => {
  it("displays resource type badges", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("resource-sidebar")).toBeInTheDocument();
    });

    // Check for type badges (L for Labor, E for Equipment)
    const laborBadge = screen.getByText("L");
    const equipmentBadge = screen.getByText("E");

    expect(laborBadge).toBeInTheDocument();
    expect(equipmentBadge).toBeInTheDocument();
  });

  it("displays resource capacity", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("8h/d")).toBeInTheDocument();
      expect(screen.getByText("10h/d")).toBeInTheDocument();
    });
  });
});

describe("AssignmentBars", () => {
  it("renders assignment bars with correct labels", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    // Only return assignments for the first resource
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockAssignments });
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { items: [] } });

    render(<GanttResourceView programId="test-program" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("assignment-bar-assign-1")).toBeInTheDocument();
    });

    expect(screen.getByText("ACT-001")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("handles keyboard delete on assignment", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockResources });
    // Only return assignments for the first resource
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockAssignments });
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { items: [] } });
    vi.mocked(apiClient.delete).mockResolvedValue({});

    const handleChange = vi.fn();

    render(
      <GanttResourceView
        programId="test-program"
        onAssignmentChange={handleChange}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByTestId("assignment-bar-assign-1")).toBeInTheDocument();
    });

    const assignmentBar = screen.getByTestId("assignment-bar-assign-1");
    fireEvent.keyDown(assignmentBar, { key: "Delete" });

    expect(handleChange).toHaveBeenCalledWith({
      assignmentId: "assign-1",
      type: "delete",
    });
  });
});
