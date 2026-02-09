import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DistributionHistogram } from "../DistributionHistogram";
import type { HistogramBin } from "@/types/simulation";

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ReferenceLine: ({ label }: { label?: { value: string } }) => (
    <div data-testid="reference-line" data-label={label?.value} />
  ),
}));

const mockHistogram: HistogramBin[] = [
  { bin_start: 30, bin_end: 35, count: 100, frequency: 0.1 },
  { bin_start: 35, bin_end: 40, count: 250, frequency: 0.25 },
  { bin_start: 40, bin_end: 45, count: 350, frequency: 0.35 },
  { bin_start: 45, bin_end: 50, count: 200, frequency: 0.2 },
  { bin_start: 50, bin_end: 55, count: 80, frequency: 0.08 },
  { bin_start: 55, bin_end: 60, count: 20, frequency: 0.02 },
];

describe("DistributionHistogram", () => {
  it("renders the chart with data", () => {
    render(
      <DistributionHistogram
        histogram={mockHistogram}
        mean={42.5}
        p50={42.0}
        p80={47.5}
        p90={50.0}
      />
    );

    expect(screen.getByText("Duration Distribution")).toBeInTheDocument();
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders reference lines for percentiles", () => {
    render(
      <DistributionHistogram
        histogram={mockHistogram}
        mean={42.5}
        p50={42.0}
        p80={47.5}
        p90={50.0}
      />
    );

    const refLines = screen.getAllByTestId("reference-line");
    expect(refLines).toHaveLength(4);

    const labels = refLines.map((el) => el.getAttribute("data-label"));
    expect(labels).toContain("Mean");
    expect(labels).toContain("P50");
    expect(labels).toContain("P80");
    expect(labels).toContain("P90");
  });

  it("shows empty state when histogram is empty", () => {
    render(
      <DistributionHistogram
        histogram={[]}
        mean={0}
        p50={0}
        p80={0}
        p90={0}
      />
    );

    expect(screen.getByText("No histogram data available.")).toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
  });

  it("renders responsive container", () => {
    render(
      <DistributionHistogram
        histogram={mockHistogram}
        mean={42.5}
        p50={42.0}
        p80={47.5}
        p90={50.0}
      />
    );

    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders bar element", () => {
    render(
      <DistributionHistogram
        histogram={mockHistogram}
        mean={42.5}
        p50={42.0}
        p80={47.5}
        p90={50.0}
      />
    );

    expect(screen.getByTestId("bar")).toBeInTheDocument();
  });
});
