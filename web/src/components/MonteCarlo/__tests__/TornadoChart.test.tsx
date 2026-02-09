import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TornadoChart } from "../TornadoChart";
import type { SensitivityItem } from "@/types/simulation";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children, layout }: { children: React.ReactNode; layout?: string }) => (
    <div data-testid="bar-chart" data-layout={layout}>{children}</div>
  ),
  Bar: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="bar">{children}</div>
  ),
  Cell: ({ fill }: { fill: string }) => <div data-testid="cell" data-fill={fill} />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

const mockSensitivity: SensitivityItem[] = [
  { activity_id: "a1", activity_name: "Design", correlation: 0.85, criticality_index: 0.95 },
  { activity_id: "a2", activity_name: "Testing", correlation: -0.42, criticality_index: 0.6 },
  { activity_id: "a3", activity_name: "Integration", correlation: 0.62, criticality_index: 0.78 },
];

describe("TornadoChart", () => {
  it("renders the chart with sensitivity data", () => {
    render(<TornadoChart sensitivity={mockSensitivity} />);

    expect(screen.getByText("Sensitivity Analysis (Tornado)")).toBeInTheDocument();
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders with vertical layout", () => {
    render(<TornadoChart sensitivity={mockSensitivity} />);

    const chart = screen.getByTestId("bar-chart");
    expect(chart).toHaveAttribute("data-layout", "vertical");
  });

  it("renders cells with correct colors (purple for positive, orange for negative)", () => {
    render(<TornadoChart sensitivity={mockSensitivity} />);

    const cells = screen.getAllByTestId("cell");
    // Sorted by |correlation|: Design (0.85), Integration (0.62), Testing (-0.42)
    expect(cells[0]).toHaveAttribute("data-fill", "#8b5cf6"); // positive
    expect(cells[1]).toHaveAttribute("data-fill", "#8b5cf6"); // positive
    expect(cells[2]).toHaveAttribute("data-fill", "#f97316"); // negative
  });

  it("limits items to maxItems", () => {
    const manyItems: SensitivityItem[] = Array.from({ length: 15 }, (_, i) => ({
      activity_id: `a${i}`,
      activity_name: `Activity ${i}`,
      correlation: 0.9 - i * 0.05,
      criticality_index: 0.9,
    }));

    render(<TornadoChart sensitivity={manyItems} maxItems={5} />);

    const cells = screen.getAllByTestId("cell");
    expect(cells).toHaveLength(5);
  });

  it("shows empty state when no sensitivity data", () => {
    render(<TornadoChart sensitivity={[]} />);

    expect(screen.getByText("No sensitivity data available.")).toBeInTheDocument();
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument();
  });

  it("uses default maxItems of 10", () => {
    const items: SensitivityItem[] = Array.from({ length: 12 }, (_, i) => ({
      activity_id: `a${i}`,
      activity_name: `Activity ${i}`,
      correlation: 0.9 - i * 0.05,
      criticality_index: 0.9,
    }));

    render(<TornadoChart sensitivity={items} />);

    const cells = screen.getAllByTestId("cell");
    expect(cells).toHaveLength(10);
  });
});
