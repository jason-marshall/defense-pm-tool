/**
 * Unit tests for PerformanceIndices component.
 * Tests CPI/SPI display, index classes, descriptions, and OverallStatus badge.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PerformanceIndices } from "../PerformanceIndices";
import type { EVMSSummary } from "@/services/evmsApi";

function makeSummary(overrides: Partial<EVMSSummary> = {}): EVMSSummary {
  return {
    programId: "prog-1",
    programName: "Test Program",
    budgetAtCompletion: "1000000",
    cumulativeBcws: "500000",
    cumulativeBcwp: "450000",
    cumulativeAcwp: "480000",
    costVariance: "-30000",
    scheduleVariance: "-50000",
    cpi: "1.05",
    spi: "1.02",
    estimateAtCompletion: "952381",
    estimateToComplete: "472381",
    varianceAtCompletion: "47619",
    tcpiEac: "0.97",
    tcpiBac: "0.96",
    percentComplete: "45.0",
    percentSpent: "48.0",
    latestPeriod: null,
    ...overrides,
  };
}

describe("PerformanceIndices", () => {
  it("renders Performance Indices header", () => {
    render(<PerformanceIndices summary={makeSummary()} />);
    expect(screen.getByText("Performance Indices")).toBeInTheDocument();
  });

  it("shows CPI value formatted to 2 decimals", () => {
    render(<PerformanceIndices summary={makeSummary({ cpi: "1.05" })} />);
    expect(screen.getByText("1.05")).toBeInTheDocument();
  });

  it("shows SPI value formatted to 2 decimals", () => {
    render(<PerformanceIndices summary={makeSummary({ spi: "0.93" })} />);
    expect(screen.getByText("0.93")).toBeInTheDocument();
  });

  it("CPI >= 1.0 gets good class", () => {
    const { container } = render(
      <PerformanceIndices summary={makeSummary({ cpi: "1.05" })} />
    );
    const goodValues = container.querySelectorAll(".evms-index-value.good");
    expect(goodValues.length).toBeGreaterThanOrEqual(1);
  });

  it("CPI 0.9-0.99 gets warning class", () => {
    const { container } = render(
      <PerformanceIndices summary={makeSummary({ cpi: "0.95", spi: "1.05" })} />
    );
    const warningValues = container.querySelectorAll(".evms-index-value.warning");
    expect(warningValues.length).toBeGreaterThanOrEqual(1);
  });

  it("CPI < 0.9 gets bad class", () => {
    const { container } = render(
      <PerformanceIndices summary={makeSummary({ cpi: "0.85", spi: "1.05" })} />
    );
    const badValues = container.querySelectorAll(".evms-index-value.bad");
    expect(badValues.length).toBeGreaterThanOrEqual(1);
  });

  it("null CPI shows N/A", () => {
    render(<PerformanceIndices summary={makeSummary({ cpi: null })} />);
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(1);
  });

  it("shows CPI description based on value >= 1.0", () => {
    render(<PerformanceIndices summary={makeSummary({ cpi: "1.05" })} />);
    expect(
      screen.getByText("Under budget - efficient cost performance")
    ).toBeInTheDocument();
  });

  it("shows CPI description for warning range", () => {
    render(<PerformanceIndices summary={makeSummary({ cpi: "0.95" })} />);
    expect(
      screen.getByText("Slightly over budget - monitor closely")
    ).toBeInTheDocument();
  });

  it("shows CPI description for bad range", () => {
    render(<PerformanceIndices summary={makeSummary({ cpi: "0.80" })} />);
    expect(
      screen.getByText("Over budget - corrective action needed")
    ).toBeInTheDocument();
  });

  it("shows SPI description based on value >= 1.0", () => {
    render(<PerformanceIndices summary={makeSummary({ spi: "1.10" })} />);
    expect(
      screen.getByText("Ahead of schedule - good progress")
    ).toBeInTheDocument();
  });

  it("shows SPI description for warning range", () => {
    render(<PerformanceIndices summary={makeSummary({ spi: "0.92" })} />);
    expect(
      screen.getByText("Slightly behind schedule - monitor closely")
    ).toBeInTheDocument();
  });

  it("shows SPI description for bad range", () => {
    render(<PerformanceIndices summary={makeSummary({ spi: "0.80" })} />);
    expect(
      screen.getByText("Behind schedule - corrective action needed")
    ).toBeInTheDocument();
  });

  it("OverallStatus shows On Track when both >= 1.0", () => {
    render(
      <PerformanceIndices summary={makeSummary({ cpi: "1.05", spi: "1.02" })} />
    );
    expect(screen.getByText("On Track")).toBeInTheDocument();
  });

  it("OverallStatus shows At Risk when one is 0.9-0.99", () => {
    render(
      <PerformanceIndices summary={makeSummary({ cpi: "0.95", spi: "1.02" })} />
    );
    expect(screen.getByText("At Risk")).toBeInTheDocument();
  });

  it("OverallStatus shows Behind when one < 0.9", () => {
    render(
      <PerformanceIndices summary={makeSummary({ cpi: "0.85", spi: "1.02" })} />
    );
    expect(screen.getByText("Behind")).toBeInTheDocument();
  });

  it("OverallStatus shows No Data when CPI is null", () => {
    render(
      <PerformanceIndices summary={makeSummary({ cpi: null, spi: "1.02" })} />
    );
    expect(screen.getByText("No Data")).toBeInTheDocument();
  });

  it("OverallStatus shows No Data when SPI is null", () => {
    render(
      <PerformanceIndices summary={makeSummary({ cpi: "1.05", spi: null })} />
    );
    expect(screen.getByText("No Data")).toBeInTheDocument();
  });
});
