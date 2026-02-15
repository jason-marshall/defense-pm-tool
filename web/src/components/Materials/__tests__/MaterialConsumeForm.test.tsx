import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MaterialConsumeForm } from "../MaterialConsumeForm";
import { ToastProvider } from "@/components/Toast";

const mockMutateAsync = vi.fn();

vi.mock("@/hooks/useMaterial", () => ({
  useConsumeMaterial: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{ui}</ToastProvider>
    </QueryClientProvider>
  );
}

describe("MaterialConsumeForm", () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  const defaultProps = {
    assignmentId: "assign-1",
    resourceName: "Steel Plates",
    maxQuantity: 100,
    onClose: mockOnClose,
    onSuccess: mockOnSuccess,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it("renders form with resource name", () => {
    renderWithProviders(<MaterialConsumeForm {...defaultProps} />);

    expect(
      screen.getByText("Consume Material - Steel Plates")
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
  });

  it("shows remaining quantity", () => {
    renderWithProviders(<MaterialConsumeForm {...defaultProps} />);

    expect(screen.getByText("Remaining: 100")).toBeInTheDocument();
  });

  it("submits and calls onSuccess", async () => {
    renderWithProviders(<MaterialConsumeForm {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/quantity/i), {
      target: { value: "25" },
    });
    fireEvent.submit(screen.getByRole("button", { name: /consume/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        assignmentId: "assign-1",
        quantity: 25,
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it("calls onClose on cancel", () => {
    renderWithProviders(<MaterialConsumeForm {...defaultProps} />);

    fireEvent.click(screen.getByText("Cancel"));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("has correct max quantity constraint on input", () => {
    renderWithProviders(<MaterialConsumeForm {...defaultProps} />);

    const input = screen.getByLabelText(/quantity/i);
    expect(input).toHaveAttribute("max", "100");
    expect(input).toHaveAttribute("min", "0.01");
  });
});
