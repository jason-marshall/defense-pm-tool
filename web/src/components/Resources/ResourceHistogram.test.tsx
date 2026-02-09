import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceHistogram } from "./ResourceHistogram";

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
  Legend: () => <div />,
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  Cell: () => <div />,
}));

vi.mock("@/services/histogramApi", () => ({
  getResourceHistogram: vi.fn(),
  getProgramHistogram: vi.fn(),
}));

import { getResourceHistogram } from "@/services/histogramApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockHistogramData = {
  resource_id: "res-1",
  resource_code: "ENG-001",
  resource_name: "Senior Engineer",
  resource_type: "LABOR",
  start_date: "2026-02-01",
  end_date: "2026-02-28",
  data_points: [
    {
      date: "2026-02-01",
      available_hours: 8,
      assigned_hours: 6,
      utilization_percent: 75,
      is_overallocated: false,
    },
    {
      date: "2026-02-02",
      available_hours: 8,
      assigned_hours: 10,
      utilization_percent: 125,
      is_overallocated: true,
    },
  ],
  peak_utilization: 125,
  peak_date: "2026-02-02",
  average_utilization: 100,
  total_available_hours: 160,
  total_assigned_hours: 16,
  overallocated_days: 1,
};

describe("ResourceHistogram", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(getResourceHistogram).mockImplementation(
      () => new Promise(() => {})
    );

    render(
      <ResourceHistogram resourceId="res-1" resourceName="Senior Engineer" />,
      { wrapper }
    );

    // Loading state shows animate-pulse skeleton
    const { container } = render(
      <ResourceHistogram resourceId="res-1" resourceName="Senior Engineer" />,
      { wrapper }
    );
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders error state", async () => {
    vi.mocked(getResourceHistogram).mockRejectedValue(new Error("API Error"));

    render(
      <ResourceHistogram resourceId="res-1" resourceName="Senior Engineer" />,
      { wrapper }
    );

    expect(
      await screen.findByText("Error loading histogram data")
    ).toBeInTheDocument();
  });

  it("renders histogram with data", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockHistogramData);

    render(
      <ResourceHistogram
        resourceId="res-1"
        resourceName="Senior Engineer"
        startDate="2026-02-01"
        endDate="2026-02-28"
      />,
      { wrapper }
    );

    expect(
      await screen.findByText(/Senior Engineer - Resource Loading/)
    ).toBeInTheDocument();
  });

  it("shows summary stats", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockHistogramData);

    render(
      <ResourceHistogram
        resourceId="res-1"
        resourceName="Senior Engineer"
        startDate="2026-02-01"
        endDate="2026-02-28"
      />,
      { wrapper }
    );

    expect(await screen.findByText("125%")).toBeInTheDocument(); // peak
    expect(screen.getByText("100%")).toBeInTheDocument(); // avg
    expect(screen.getByText("160h")).toBeInTheDocument(); // total available
    expect(screen.getByText("1 days")).toBeInTheDocument(); // overallocated
  });

  it("shows granularity selector", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockHistogramData);

    render(
      <ResourceHistogram
        resourceId="res-1"
        resourceName="Senior Engineer"
        startDate="2026-02-01"
        endDate="2026-02-28"
      />,
      { wrapper }
    );

    await screen.findByText(/Senior Engineer/);

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue("daily");

    fireEvent.change(select, { target: { value: "weekly" } });

    await waitFor(() => {
      expect(getResourceHistogram).toHaveBeenCalledWith(
        "res-1",
        expect.any(String),
        expect.any(String),
        "weekly"
      );
    });
  });

  it("shows no data message when empty", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue({
      ...mockHistogramData,
      data_points: [],
    });

    render(
      <ResourceHistogram
        resourceId="res-1"
        resourceName="Senior Engineer"
        startDate="2026-02-01"
        endDate="2026-02-28"
      />,
      { wrapper }
    );

    expect(
      await screen.findByText("No data available for the selected date range")
    ).toBeInTheDocument();
  });

  it("shows overallocation explanation", async () => {
    vi.mocked(getResourceHistogram).mockResolvedValue(mockHistogramData);

    render(
      <ResourceHistogram
        resourceId="res-1"
        resourceName="Senior Engineer"
        startDate="2026-02-01"
        endDate="2026-02-28"
      />,
      { wrapper }
    );

    expect(
      await screen.findByText(/Red bars indicate overallocation/)
    ).toBeInTheDocument();
  });
});
