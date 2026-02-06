/**
 * Unit tests for MetricsCards component.
 * Tests rendering of 8 EVMS metric cards with currency/percent formatting.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricsCards } from "../MetricsCards";
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
    cpi: "0.94",
    spi: "0.90",
    estimateAtCompletion: "1063830",
    estimateToComplete: "583830",
    varianceAtCompletion: "-63830",
    tcpiEac: "0.97",
    tcpiBac: "1.06",
    percentComplete: "45.0",
    percentSpent: "48.0",
    latestPeriod: null,
    ...overrides,
  };
}

describe("MetricsCards", () => {
  it("renders all 8 metric labels", () => {
    render(<MetricsCards summary={makeSummary()} />);

    expect(screen.getByText("Budget at Completion (BAC)")).toBeInTheDocument();
    expect(screen.getByText("Planned Value (BCWS)")).toBeInTheDocument();
    expect(screen.getByText("Earned Value (BCWP)")).toBeInTheDocument();
    expect(screen.getByText("Actual Cost (ACWP)")).toBeInTheDocument();
    expect(screen.getByText("Cost Variance (CV)")).toBeInTheDocument();
    expect(screen.getByText("Schedule Variance (SV)")).toBeInTheDocument();
    expect(screen.getByText("% Complete")).toBeInTheDocument();
    expect(screen.getByText("% Spent")).toBeInTheDocument();
  });

  it("formats BAC as currency", () => {
    render(<MetricsCards summary={makeSummary({ budgetAtCompletion: "1000000" })} />);
    expect(screen.getByText("$1,000,000")).toBeInTheDocument();
  });

  it("formats BCWS, BCWP, ACWP as currency", () => {
    render(
      <MetricsCards
        summary={makeSummary({
          cumulativeBcws: "500000",
          cumulativeBcwp: "450000",
          cumulativeAcwp: "480000",
        })}
      />
    );
    expect(screen.getByText("$500,000")).toBeInTheDocument();
    expect(screen.getByText("$450,000")).toBeInTheDocument();
    expect(screen.getByText("$480,000")).toBeInTheDocument();
  });

  it("shows CV with positive class when positive", () => {
    const { container } = render(
      <MetricsCards summary={makeSummary({ costVariance: "25000" })} />
    );
    const cvValues = container.querySelectorAll(".evms-metric-value.positive");
    expect(cvValues.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("$25,000")).toBeInTheDocument();
  });

  it("shows CV with negative class when negative", () => {
    const { container } = render(
      <MetricsCards summary={makeSummary({ costVariance: "-30000" })} />
    );
    const cvValues = container.querySelectorAll(".evms-metric-value.negative");
    expect(cvValues.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("-$30,000")).toBeInTheDocument();
  });

  it("shows SV with correct variance class", () => {
    const { container } = render(
      <MetricsCards
        summary={makeSummary({ costVariance: "0", scheduleVariance: "-50000" })}
      />
    );
    // SV card should get "negative" class
    const negativeValues = container.querySelectorAll(".evms-metric-value.negative");
    expect(negativeValues.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("-$50,000")).toBeInTheDocument();
  });

  it("shows N/A when CV is null", () => {
    render(
      <MetricsCards summary={makeSummary({ costVariance: null })} />
    );
    // There should be an N/A for cost variance
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(1);
  });

  it("formats percentComplete as X.Y%", () => {
    render(<MetricsCards summary={makeSummary({ percentComplete: "45.0" })} />);
    expect(screen.getByText("45.0%")).toBeInTheDocument();
  });

  it("formats percentSpent as X.Y%", () => {
    render(<MetricsCards summary={makeSummary({ percentSpent: "48.0" })} />);
    expect(screen.getByText("48.0%")).toBeInTheDocument();
  });

  it("shows sublabels for metric cards", () => {
    render(<MetricsCards summary={makeSummary()} />);
    expect(screen.getByText("Total authorized budget")).toBeInTheDocument();
    expect(screen.getByText("Budgeted Cost of Work Scheduled")).toBeInTheDocument();
    expect(screen.getByText("Budgeted Cost of Work Performed")).toBeInTheDocument();
    expect(screen.getByText("Actual Cost of Work Performed")).toBeInTheDocument();
    expect(screen.getByText("BCWP - ACWP")).toBeInTheDocument();
    expect(screen.getByText("BCWP - BCWS")).toBeInTheDocument();
    expect(screen.getByText("Work completed")).toBeInTheDocument();
    expect(screen.getByText("Budget consumed")).toBeInTheDocument();
  });
});
