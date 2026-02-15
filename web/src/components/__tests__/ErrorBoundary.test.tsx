import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>Child content</div>;
}

describe("ErrorBoundary", () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div>Hello World</div>
      </ErrorBoundary>
    );

    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("renders default error UI when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("has alert role on error container", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Custom fallback")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("recovers when retry button is clicked", () => {
    let shouldThrow = true;

    function ConditionalThrower() {
      if (shouldThrow) {
        throw new Error("Error");
      }
      return <div>Recovered</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Fix the error condition and click retry
    shouldThrow = false;
    fireEvent.click(screen.getByText("Try Again"));

    rerender(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    );

    expect(screen.getByText("Recovered")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });

  it("calls componentDidCatch with error info", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("shows generic message when error has no message", () => {
    function ThrowEmpty(): React.ReactElement {
      throw new Error();
    }

    render(
      <ErrorBoundary>
        <ThrowEmpty />
      </ErrorBoundary>
    );

    expect(screen.getByText("An unexpected error occurred")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });
});
