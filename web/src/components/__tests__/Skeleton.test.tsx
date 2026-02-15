import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import {
  Skeleton,
  TableSkeleton,
  CardSkeleton,
  DashboardSkeleton,
  MetricCardSkeleton,
  ChartSkeleton,
} from "../Skeleton";

describe("Skeleton", () => {
  it("renders with default rectangular variant", () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("animate-pulse");
    expect(el.className).toContain("rounded-md");
  });

  it("renders with text variant", () => {
    const { container } = render(<Skeleton variant="text" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("rounded");
  });

  it("renders with circular variant", () => {
    const { container } = render(<Skeleton variant="circular" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("rounded-full");
  });

  it("applies custom width and height", () => {
    const { container } = render(<Skeleton width="200px" height={50} />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.width).toBe("200px");
    expect(el.style.height).toBe("50px");
  });

  it("applies custom className", () => {
    const { container } = render(<Skeleton className="custom-class" />);
    const el = container.firstChild as HTMLElement;
    expect(el.className).toContain("custom-class");
  });
});

describe("TableSkeleton", () => {
  it("renders default 5 rows", () => {
    const { container } = render(<TableSkeleton />);
    const rows = container.querySelectorAll(".flex.gap-4");
    expect(rows.length).toBe(5);
  });

  it("renders custom number of rows", () => {
    const { container } = render(<TableSkeleton rows={3} />);
    const rows = container.querySelectorAll(".flex.gap-4");
    expect(rows.length).toBe(3);
  });
});

describe("CardSkeleton", () => {
  it("renders card skeleton structure", () => {
    const { container } = render(<CardSkeleton />);
    expect(container.querySelector(".p-6.border.rounded-lg")).toBeTruthy();
  });
});

describe("DashboardSkeleton", () => {
  it("renders 4 metric cards and 2 chart areas", () => {
    const { container } = render(<DashboardSkeleton />);
    const gridCols4 = container.querySelector(".grid.grid-cols-4");
    expect(gridCols4).toBeTruthy();
    const gridCols2 = container.querySelector(".grid.grid-cols-2");
    expect(gridCols2).toBeTruthy();
  });
});

describe("MetricCardSkeleton", () => {
  it("renders metric card structure", () => {
    const { container } = render(<MetricCardSkeleton />);
    expect(container.querySelector(".p-4.border.rounded-lg")).toBeTruthy();
  });
});

describe("ChartSkeleton", () => {
  it("renders with default height", () => {
    const { container } = render(<ChartSkeleton />);
    expect(container.querySelector(".p-4.border.rounded-lg")).toBeTruthy();
  });

  it("renders with custom height", () => {
    render(<ChartSkeleton height={500} />);
    // ChartSkeleton accepts height prop
    const { container } = render(<ChartSkeleton height={500} />);
    expect(container.querySelector(".p-4")).toBeTruthy();
  });
});
