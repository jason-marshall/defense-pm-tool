import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DependencyFormModal } from "../DependencyFormModal";
import { ToastProvider } from "@/components/Toast";

const mockMutateAsync = vi.fn();

vi.mock("@/hooks/useActivities", () => ({
  useActivities: () => ({
    data: {
      items: [
        { id: "act-1", code: "A-001", name: "Design" },
        { id: "act-2", code: "A-002", name: "Build" },
        { id: "act-3", code: "A-003", name: "Test" },
      ],
    },
  }),
}));

vi.mock("@/hooks/useDependencies", () => ({
  useCreateDependency: () => ({
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

describe("DependencyFormModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({});
  });

  it("renders form with title and activity dropdowns", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    expect(screen.getByText("Add Dependency")).toBeInTheDocument();
    expect(screen.getByLabelText(/predecessor/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/successor/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/lag/i)).toBeInTheDocument();
  });

  it("populates predecessor and successor options from activities", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    const predecessorSelect = screen.getByLabelText(/predecessor/i);
    const options = predecessorSelect.querySelectorAll("option");

    // 3 activities + "Select activity..." placeholder
    expect(options).toHaveLength(4);
    expect(options[1]).toHaveTextContent("A-001 - Design");
    expect(options[2]).toHaveTextContent("A-002 - Build");
  });

  it("submits with FS type and lag", async () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.change(screen.getByLabelText(/predecessor/i), {
      target: { value: "act-1" },
    });
    fireEvent.change(screen.getByLabelText(/successor/i), {
      target: { value: "act-2" },
    });
    fireEvent.change(screen.getByLabelText(/lag/i), {
      target: { value: "3" },
    });

    fireEvent.submit(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        predecessor_id: "act-1",
        successor_id: "act-2",
        dependency_type: "FS",
        lag: 3,
      });
    });
  });

  it("calls onClose on cancel", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    fireEvent.click(screen.getByText("Cancel"));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("shows all 4 dependency type options", () => {
    renderWithProviders(
      <DependencyFormModal programId="prog-1" onClose={mockOnClose} />
    );

    const typeSelect = screen.getByLabelText(/type/i);
    const options = typeSelect.querySelectorAll("option");

    expect(options).toHaveLength(4);
    expect(options[0]).toHaveTextContent("Finish-to-Start");
    expect(options[1]).toHaveTextContent("Start-to-Start");
    expect(options[2]).toHaveTextContent("Finish-to-Finish");
    expect(options[3]).toHaveTextContent("Start-to-Finish");
  });
});
