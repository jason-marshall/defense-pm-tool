import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ToastProvider, useToast } from "../Toast";

function TestConsumer() {
  const toast = useToast();
  return (
    <div>
      <button onClick={() => toast.success("Success message")}>Success</button>
      <button onClick={() => toast.error("Error message")}>Error</button>
      <button onClick={() => toast.warning("Warning message")}>Warning</button>
      <button onClick={() => toast.info("Info message")}>Info</button>
      <button onClick={() => toast.showToast("success", "Custom", 0)}>
        No Auto Dismiss
      </button>
    </div>
  );
}

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("throws when useToast is used outside ToastProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow(
      "useToast must be used within ToastProvider"
    );
    spy.mockRestore();
  });

  it("shows success toast", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    expect(screen.getByText("Success message")).toBeInTheDocument();
  });

  it("shows error toast", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Error"));
    expect(screen.getByText("Error message")).toBeInTheDocument();
  });

  it("shows warning toast", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Warning"));
    expect(screen.getByText("Warning message")).toBeInTheDocument();
  });

  it("shows info toast", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Info"));
    expect(screen.getByText("Info message")).toBeInTheDocument();
  });

  it("auto-dismisses after duration", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    expect(screen.getByText("Success message")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.queryByText("Success message")).not.toBeInTheDocument();
  });

  it("does not auto-dismiss when duration is 0", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("No Auto Dismiss"));
    expect(screen.getByText("Custom")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("removes toast on close button click", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    expect(screen.getByText("Success message")).toBeInTheDocument();

    // Click the close button (X icon button)
    const closeButtons = screen.getAllByRole("button");
    const closeBtn = closeButtons.find(
      (btn) => btn.className.includes("text-gray-400")
    );
    if (closeBtn) fireEvent.click(closeBtn);

    expect(screen.queryByText("Success message")).not.toBeInTheDocument();
  });

  it("can show multiple toasts simultaneously", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    fireEvent.click(screen.getByText("Error"));
    fireEvent.click(screen.getByText("Info"));

    expect(screen.getByText("Success message")).toBeInTheDocument();
    expect(screen.getByText("Error message")).toBeInTheDocument();
    expect(screen.getByText("Info message")).toBeInTheDocument();
  });

  it("has aria-live and role on toast container", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    const container = screen.getByRole("status");
    expect(container).toHaveAttribute("aria-live", "polite");
  });

  it("has dismiss label on close button", () => {
    render(
      <ToastProvider>
        <TestConsumer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText("Success"));
    expect(screen.getByLabelText("Dismiss notification")).toBeInTheDocument();
  });
});
