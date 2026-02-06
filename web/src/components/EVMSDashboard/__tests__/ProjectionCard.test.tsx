/**
 * Unit tests for ProjectionCard component.
 * Tests EAC, ETC, VAC, TCPI display and TCPI interpretation messages.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectionCard } from "../ProjectionCard";
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

describe("ProjectionCard", () => {
  it("renders Projections & Estimates header", () => {
    render(<ProjectionCard summary={makeSummary()} />);
    expect(screen.getByText("Projections & Estimates")).toBeInTheDocument();
  });

  it("shows EAC formatted as currency", () => {
    render(
      <ProjectionCard summary={makeSummary({ estimateAtCompletion: "1063830" })} />
    );
    expect(screen.getByText("$1,063,830")).toBeInTheDocument();
  });

  it("shows ETC formatted as currency", () => {
    render(
      <ProjectionCard summary={makeSummary({ estimateToComplete: "583830" })} />
    );
    expect(screen.getByText("$583,830")).toBeInTheDocument();
  });

  it("shows VAC with positive class when positive", () => {
    const { container } = render(
      <ProjectionCard summary={makeSummary({ varianceAtCompletion: "50000" })} />
    );
    const positiveValues = container.querySelectorAll(
      ".evms-projection-value.positive"
    );
    expect(positiveValues.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("$50,000")).toBeInTheDocument();
  });

  it("shows VAC with negative class when negative", () => {
    const { container } = render(
      <ProjectionCard summary={makeSummary({ varianceAtCompletion: "-63830" })} />
    );
    const negativeValues = container.querySelectorAll(
      ".evms-projection-value.negative"
    );
    expect(negativeValues.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("-$63,830")).toBeInTheDocument();
  });

  it("shows TCPI (BAC) formatted to 2 decimals", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiBac: "1.06" })} />);
    expect(screen.getByText("1.06")).toBeInTheDocument();
  });

  it("shows TCPI (EAC) formatted to 2 decimals", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiEac: "0.97" })} />);
    expect(screen.getByText("0.97")).toBeInTheDocument();
  });

  it("shows N/A when EAC is null", () => {
    render(
      <ProjectionCard summary={makeSummary({ estimateAtCompletion: null })} />
    );
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(1);
  });

  it("shows TCPI interpretation for > 1.1 (very difficult)", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiBac: "1.20" })} />);
    expect(screen.getByText(/very difficult/)).toBeInTheDocument();
    expect(
      screen.getByText(/Consider EAC-based target/)
    ).toBeInTheDocument();
  });

  it("shows TCPI interpretation for > 1.0 but <= 1.1 (improved efficiency)", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiBac: "1.06" })} />);
    expect(screen.getByText(/improved efficiency/)).toBeInTheDocument();
  });

  it("shows TCPI interpretation for <= 1.0 (on track)", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiBac: "0.95" })} />);
    expect(
      screen.getByText(/On track to meet or beat original budget/)
    ).toBeInTheDocument();
  });

  it("does not render TCPI interpretation when tcpiBac is null", () => {
    render(<ProjectionCard summary={makeSummary({ tcpiBac: null })} />);
    expect(screen.queryByText(/Interpretation:/)).not.toBeInTheDocument();
  });
});
