import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SCurveChart } from "../SCurveChart";
import type { SCurveDataPoint } from "@/types/simulation";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: ({ name, stroke }: { name?: string; stroke?: string }) => (
    <div data-testid="line" data-name={name} data-stroke={stroke} />
  ),
  Area: ({ name }: { name?: string }) => (
    <div data-testid="area" data-name={name} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

const mockData: SCurveDataPoint[] = [
  { period: "2026-01", bcws: "10000", bcwp: "9500", acwp: "10200" },
  { period: "2026-02", bcws: "25000", bcwp: "22000", acwp: "24000" },
  { period: "2026-03", bcws: "45000", bcwp: "38000", acwp: "42000" },
];

const mockDataWithBand: SCurveDataPoint[] = [
  { period: "2026-01", bcws: "10000", bcwp: "9500", acwp: "10200", bcws_optimistic: "9000", bcws_pessimistic: "11000" },
  { period: "2026-02", bcws: "25000", bcwp: "22000", acwp: "24000", bcws_optimistic: "23000", bcws_pessimistic: "27000" },
];

describe("SCurveChart", () => {
  it("renders the chart with data", () => {
    render(<SCurveChart data={mockData} />);

    expect(screen.getByText("S-Curve")).toBeInTheDocument();
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders three data lines (BCWS, BCWP, ACWP)", () => {
    render(<SCurveChart data={mockData} />);

    const lines = screen.getAllByTestId("line");
    expect(lines).toHaveLength(3);

    const names = lines.map((l) => l.getAttribute("data-name"));
    expect(names).toContain("BCWS (PV)");
    expect(names).toContain("BCWP (EV)");
    expect(names).toContain("ACWP (AC)");
  });

  it("renders correct line colors", () => {
    render(<SCurveChart data={mockData} />);

    const lines = screen.getAllByTestId("line");
    const strokes = lines.map((l) => l.getAttribute("data-stroke"));
    expect(strokes).toContain("#3b82f6"); // blue for BCWS
    expect(strokes).toContain("#10b981"); // green for BCWP
    expect(strokes).toContain("#ef4444"); // red for ACWP
  });

  it("renders confidence band areas when data has optimistic/pessimistic", () => {
    render(<SCurveChart data={mockDataWithBand} />);

    const areas = screen.getAllByTestId("area");
    expect(areas.length).toBeGreaterThanOrEqual(1);
    expect(areas[0]).toHaveAttribute("data-name", "Confidence Band");
  });

  it("does not render confidence band without optimistic/pessimistic data", () => {
    render(<SCurveChart data={mockData} />);

    expect(screen.queryByTestId("area")).not.toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    render(<SCurveChart data={[]} />);

    expect(screen.getByText("No S-curve data available.")).toBeInTheDocument();
    expect(screen.queryByTestId("line-chart")).not.toBeInTheDocument();
  });

  it("renders legend", () => {
    render(<SCurveChart data={mockData} />);

    expect(screen.getByTestId("legend")).toBeInTheDocument();
  });
});
