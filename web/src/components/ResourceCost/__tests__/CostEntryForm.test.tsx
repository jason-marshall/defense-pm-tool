import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CostEntryForm } from "../CostEntryForm";
import { ToastProvider } from "@/components/Toast";

const mockRecordMutateAsync = vi.fn();

vi.mock("@/hooks/useCost", () => ({
  useRecordCostEntry: () => ({
    mutateAsync: mockRecordMutateAsync,
    isPending: false,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

describe("CostEntryForm", () => {
  const onClose = vi.fn();
  const onSuccess = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders form fields", () => {
    render(
      <CostEntryForm
        assignmentId="assign-001"
        onClose={onClose}
        onSuccess={onSuccess}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Record Cost Entry")).toBeInTheDocument();
    expect(screen.getByLabelText("Date")).toBeInTheDocument();
    expect(screen.getByLabelText("Hours Worked")).toBeInTheDocument();
    expect(screen.getByLabelText("Quantity Used (optional)")).toBeInTheDocument();
    expect(screen.getByLabelText("Notes (optional)")).toBeInTheDocument();
  });

  it("calls onClose when Cancel clicked", () => {
    render(
      <CostEntryForm
        assignmentId="assign-001"
        onClose={onClose}
        onSuccess={onSuccess}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("submits form with required fields", async () => {
    mockRecordMutateAsync.mockResolvedValue({
      id: "entry-001",
      assignment_id: "assign-001",
    });

    render(
      <CostEntryForm
        assignmentId="assign-001"
        onClose={onClose}
        onSuccess={onSuccess}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Hours Worked"), {
      target: { value: "8" },
    });
    fireEvent.click(screen.getByText("Record Entry"));

    await waitFor(() => {
      expect(mockRecordMutateAsync).toHaveBeenCalled();
    });
  });

  it("calls onSuccess and onClose after successful submission", async () => {
    mockRecordMutateAsync.mockResolvedValue({
      id: "entry-001",
      assignment_id: "assign-001",
    });

    render(
      <CostEntryForm
        assignmentId="assign-001"
        onClose={onClose}
        onSuccess={onSuccess}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Hours Worked"), {
      target: { value: "4" },
    });
    fireEvent.click(screen.getByText("Record Entry"));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("renders submit button text", () => {
    render(
      <CostEntryForm
        assignmentId="assign-001"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Record Entry")).toBeInTheDocument();
  });
});
