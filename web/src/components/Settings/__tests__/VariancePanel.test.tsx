import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VariancePanel } from "../VariancePanel";
import { ToastProvider } from "@/components/Toast";

const mockUseVariancesByProgram = vi.fn();
const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

let mockCreateIsPending = false;
let mockUpdateIsPending = false;

vi.mock("@/hooks/useVariance", () => ({
  useVariancesByProgram: (...args: unknown[]) => mockUseVariancesByProgram(...args),
  useCreateVariance: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: mockCreateIsPending,
  }),
  useUpdateVariance: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: mockUpdateIsPending,
  }),
  useDeleteVariance: () => ({
    mutateAsync: mockDeleteMutateAsync,
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

const mockVariances = {
  items: [
    {
      id: "var-1",
      program_id: "prog-1",
      wbs_id: null,
      period_id: null,
      created_by: "user-1",
      variance_type: "cost",
      variance_amount: "-5000",
      variance_percent: "-12.5",
      explanation: "Material cost overrun due to supply chain delays requiring renegotiation",
      corrective_action: "Renegotiate supplier contract",
      expected_resolution: "2026-06-01",
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-01T00:00:00Z",
      deleted_at: null,
    },
    {
      id: "var-2",
      program_id: "prog-1",
      wbs_id: null,
      period_id: null,
      created_by: "user-1",
      variance_type: "schedule",
      variance_amount: "-3000",
      variance_percent: "-8.0",
      explanation: "Integration testing delayed due to resource availability",
      corrective_action: null,
      expected_resolution: null,
      created_at: "2026-02-05T00:00:00Z",
      updated_at: "2026-02-05T00:00:00Z",
      deleted_at: null,
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
  pages: 1,
};

describe("VariancePanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
    mockCreateIsPending = false;
    mockUpdateIsPending = false;
  });

  it("shows loading state", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: undefined, isLoading: true });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading variance explanations...")).toBeInTheDocument();
  });

  it("shows empty state when no variances exist", () => {
    mockUseVariancesByProgram.mockReturnValue({
      data: { items: [], total: 0, page: 1, per_page: 20, pages: 1 },
      isLoading: false,
    });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No variance explanations found.")).toBeInTheDocument();
  });

  it("displays variance explanations in table", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("cost")).toBeInTheDocument();
    expect(screen.getByText("schedule")).toBeInTheDocument();
    expect(screen.getByText("-12.5%")).toBeInTheDocument();
  });

  it("renders type filter", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    const select = screen.getAllByRole("combobox")[0];
    expect(select).toBeInTheDocument();
  });

  it("opens create form when Add is clicked", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));

    expect(screen.getByText("New Variance Explanation")).toBeInTheDocument();
    expect(screen.getByLabelText("Explanation")).toBeInTheDocument();
  });

  it("submits create form", async () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
    mockCreateMutateAsync.mockResolvedValue({});

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));
    fireEvent.change(screen.getByLabelText("Amount ($)"), { target: { value: "-5000" } });
    fireEvent.change(screen.getByLabelText("Percent (%)"), { target: { value: "-12.5" } });
    fireEvent.change(screen.getByLabelText("Explanation"), {
      target: { value: "A valid explanation that is at least 10 characters" },
    });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          program_id: "prog-1",
          variance_type: "cost",
          explanation: "A valid explanation that is at least 10 characters",
        })
      );
    });
  });

  it("cancels form", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add"));
    expect(screen.getByText("New Variance Explanation")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("New Variance Explanation")).not.toBeInTheDocument();
  });

  it("has Add button", () => {
    mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

    render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Add")).toBeInTheDocument();
  });

  // === NEW TESTS BELOW ===

  describe("create variance explanation", () => {
    it("creates a schedule variance explanation", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));

      // Change type to schedule
      fireEvent.change(screen.getByLabelText("Type"), { target: { value: "schedule" } });
      fireEvent.change(screen.getByLabelText("Amount ($)"), { target: { value: "-3000" } });
      fireEvent.change(screen.getByLabelText("Percent (%)"), { target: { value: "-8.0" } });
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "Schedule delay due to resource constraints" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            program_id: "prog-1",
            variance_type: "schedule",
            variance_amount: "-3000",
            variance_percent: "-8.0",
            explanation: "Schedule delay due to resource constraints",
          })
        );
      });
    });

    it("creates variance with corrective action and resolution date", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Amount ($)"), { target: { value: "-10000" } });
      fireEvent.change(screen.getByLabelText("Percent (%)"), { target: { value: "-15.0" } });
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "Significant cost overrun on materials procurement" },
      });
      fireEvent.change(screen.getByLabelText("Corrective Action"), {
        target: { value: "Renegotiate vendor contracts and switch suppliers" },
      });
      fireEvent.change(screen.getByLabelText("Expected Resolution"), {
        target: { value: "2026-07-15" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            corrective_action: "Renegotiate vendor contracts and switch suppliers",
            expected_resolution: "2026-07-15",
          })
        );
      });
    });

    it("hides form after successful creation", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      expect(screen.getByText("New Variance Explanation")).toBeInTheDocument();

      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "A valid explanation that is long enough" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.queryByText("New Variance Explanation")).not.toBeInTheDocument();
      });
    });

    it("shows success toast after creation", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "A valid explanation that is long enough" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Variance explanation created")).toBeInTheDocument();
      });
    });

    it("sends undefined for empty optional fields", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "A valid explanation that is long enough" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            corrective_action: undefined,
            expected_resolution: undefined,
          })
        );
      });
    });
  });

  describe("edit variance explanation", () => {
    it("opens edit form with pre-filled data when edit button is clicked", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      // Click edit on the first variance (cost type)
      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Edit Variance Explanation")).toBeInTheDocument();
      expect(screen.getByLabelText("Explanation")).toHaveValue(
        "Material cost overrun due to supply chain delays requiring renegotiation"
      );
      expect(screen.getByLabelText("Corrective Action")).toHaveValue(
        "Renegotiate supplier contract"
      );
      expect(screen.getByLabelText("Expected Resolution")).toHaveValue("2026-06-01");
    });

    it("disables type selector when editing", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByLabelText("Type")).toBeDisabled();
    });

    it("shows Update button text instead of Create when editing", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Update")).toBeInTheDocument();
      expect(screen.queryByText("Create")).not.toBeInTheDocument();
    });

    it("submits update with correct data", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockUpdateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);

      // Change the explanation text
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "Updated explanation for the cost overrun variance" },
      });
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
          id: "var-1",
          data: expect.objectContaining({
            explanation: "Updated explanation for the cost overrun variance",
            variance_amount: "-5000",
            variance_percent: "-12.5",
          }),
        });
      });
    });

    it("shows success toast after update", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockUpdateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.getByText("Variance explanation updated")).toBeInTheDocument();
      });
    });

    it("hides form after successful update", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockUpdateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);
      expect(screen.getByText("Edit Variance Explanation")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.queryByText("Edit Variance Explanation")).not.toBeInTheDocument();
      });
    });

    it("opens edit form for the second variance with correct pre-filled data", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[1]);

      expect(screen.getByText("Edit Variance Explanation")).toBeInTheDocument();
      expect(screen.getByLabelText("Explanation")).toHaveValue(
        "Integration testing delayed due to resource availability"
      );
      // Corrective action and resolution are null, should be empty strings
      expect(screen.getByLabelText("Corrective Action")).toHaveValue("");
      expect(screen.getByLabelText("Expected Resolution")).toHaveValue("");
    });
  });

  describe("delete with confirmation", () => {
    it("calls delete when user confirms the dialog", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockDeleteMutateAsync.mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith("Delete this variance explanation?");
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("var-1");
      });
    });

    it("does not delete when user cancels the confirmation dialog", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      expect(window.confirm).toHaveBeenCalledWith("Delete this variance explanation?");
      expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
    });

    it("shows success toast after deletion", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockDeleteMutateAsync.mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText("Variance explanation deleted")).toBeInTheDocument();
      });
    });

    it("shows error toast when deletion fails", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockDeleteMutateAsync.mockRejectedValue(new Error("Server error"));
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText("Failed to delete variance explanation")).toBeInTheDocument();
      });
    });

    it("deletes the second variance correctly", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockDeleteMutateAsync.mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const deleteButtons = screen.getAllByTitle("Delete");
      fireEvent.click(deleteButtons[1]);

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("var-2");
      });
    });
  });

  describe("filter by type", () => {
    it("passes type filter to useVariancesByProgram when changed to schedule", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const filterSelect = screen.getAllByRole("combobox")[0];
      fireEvent.change(filterSelect, { target: { value: "schedule" } });

      // The hook should be called with the schedule filter
      expect(mockUseVariancesByProgram).toHaveBeenCalledWith(
        "prog-1",
        expect.objectContaining({
          variance_type: "schedule",
          include_resolved: true,
        })
      );
    });

    it("passes type filter to useVariancesByProgram when changed to cost", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const filterSelect = screen.getAllByRole("combobox")[0];
      fireEvent.change(filterSelect, { target: { value: "cost" } });

      expect(mockUseVariancesByProgram).toHaveBeenCalledWith(
        "prog-1",
        expect.objectContaining({
          variance_type: "cost",
          include_resolved: true,
        })
      );
    });

    it("passes undefined type when filter is set back to all", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const filterSelect = screen.getAllByRole("combobox")[0];
      // First set to schedule
      fireEvent.change(filterSelect, { target: { value: "schedule" } });
      // Then reset to all
      fireEvent.change(filterSelect, { target: { value: "" } });

      // Last call should have undefined type
      const lastCall = mockUseVariancesByProgram.mock.calls[
        mockUseVariancesByProgram.mock.calls.length - 1
      ];
      expect(lastCall[1]).toEqual(
        expect.objectContaining({
          variance_type: undefined,
          include_resolved: true,
        })
      );
    });

    it("filter dropdown has correct options", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("All Types")).toBeInTheDocument();
      expect(screen.getByText("Schedule")).toBeInTheDocument();
      expect(screen.getByText("Cost")).toBeInTheDocument();
    });
  });

  describe("loading and error states", () => {
    it("does not render table or empty state while loading", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: undefined, isLoading: true });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.queryByText("No variance explanations found.")).not.toBeInTheDocument();
      expect(screen.queryByText("Type")).not.toBeInTheDocument();
      expect(screen.queryByText("Add")).not.toBeInTheDocument();
    });

    it("does not render Add button while loading", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: undefined, isLoading: true });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.queryByText("Add")).not.toBeInTheDocument();
    });

    it("renders table headers when data is available with items", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Type")).toBeInTheDocument();
      expect(screen.getByText("Amount")).toBeInTheDocument();
      expect(screen.getByText("Percent")).toBeInTheDocument();
      expect(screen.getByText("Explanation")).toBeInTheDocument();
      expect(screen.getByText("Resolution")).toBeInTheDocument();
      expect(screen.getByText("Actions")).toBeInTheDocument();
    });
  });

  describe("form submission validation", () => {
    it("shows error toast when explanation is empty", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      // Leave explanation empty and click Create
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Explanation must be at least 10 characters")).toBeInTheDocument();
      });

      expect(mockCreateMutateAsync).not.toHaveBeenCalled();
    });

    it("shows error toast when explanation is too short", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "Too short" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Explanation must be at least 10 characters")).toBeInTheDocument();
      });

      expect(mockCreateMutateAsync).not.toHaveBeenCalled();
    });

    it("does not show validation error when explanation is exactly 10 characters", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockResolvedValue({});

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "1234567890" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).toHaveBeenCalled();
      });
    });

    it("shows error toast when create mutation fails", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockCreateMutateAsync.mockRejectedValue(new Error("Network error"));

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Explanation"), {
        target: { value: "A valid explanation that is long enough" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Failed to save variance explanation")).toBeInTheDocument();
      });
    });

    it("shows error toast when update mutation fails", async () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });
      mockUpdateMutateAsync.mockRejectedValue(new Error("Network error"));

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.getByText("Failed to save variance explanation")).toBeInTheDocument();
      });
    });
  });

  describe("form field interactions", () => {
    it("resets form fields when opening create form after editing", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      // First open edit form
      const editButtons = screen.getAllByTitle("Edit");
      fireEvent.click(editButtons[0]);
      expect(screen.getByLabelText("Explanation")).toHaveValue(
        "Material cost overrun due to supply chain delays requiring renegotiation"
      );

      // Cancel the edit form
      fireEvent.click(screen.getByText("Cancel"));

      // Then open create form
      fireEvent.click(screen.getByText("Add"));

      // Fields should be reset
      expect(screen.getByLabelText("Explanation")).toHaveValue("");
      expect(screen.getByLabelText("Amount ($)")).toHaveValue(null);
      expect(screen.getByLabelText("Percent (%)")).toHaveValue(null);
      expect(screen.getByLabelText("Corrective Action")).toHaveValue("");
      expect(screen.getByLabelText("Expected Resolution")).toHaveValue("");
    });

    it("type selector is not disabled in create mode", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));

      expect(screen.getByLabelText("Type")).not.toBeDisabled();
    });

    it("updates form amount field on change", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Amount ($)"), { target: { value: "12345" } });

      expect(screen.getByLabelText("Amount ($)")).toHaveValue(12345);
    });

    it("updates form percent field on change", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Add"));
      fireEvent.change(screen.getByLabelText("Percent (%)"), { target: { value: "5.5" } });

      expect(screen.getByLabelText("Percent (%)")).toHaveValue(5.5);
    });
  });

  describe("table display", () => {
    it("displays variance amounts formatted with dollar sign", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      // Check that dollar amounts are displayed
      expect(screen.getByText("$-5,000")).toBeInTheDocument();
      expect(screen.getByText("$-3,000")).toBeInTheDocument();
    });

    it("displays variance percents formatted with percent sign", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("-12.5%")).toBeInTheDocument();
      expect(screen.getByText("-8.0%")).toBeInTheDocument();
    });

    it("displays dash for null resolution date", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      // var-2 has null expected_resolution, should show "-"
      expect(screen.getByText("-")).toBeInTheDocument();
    });

    it("displays resolution date when present", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("2026-06-01")).toBeInTheDocument();
    });

    it("renders edit and delete buttons for each row", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const editButtons = screen.getAllByTitle("Edit");
      const deleteButtons = screen.getAllByTitle("Delete");

      expect(editButtons).toHaveLength(2);
      expect(deleteButtons).toHaveLength(2);
    });

    it("applies cost badge styling for cost variance type", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const costBadge = screen.getByText("cost");
      expect(costBadge).toHaveClass("bg-red-100", "text-red-700");
    });

    it("applies schedule badge styling for schedule variance type", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      const scheduleBadge = screen.getByText("schedule");
      expect(scheduleBadge).toHaveClass("bg-yellow-100", "text-yellow-700");
    });

    it("displays the VRID heading", () => {
      mockUseVariancesByProgram.mockReturnValue({ data: mockVariances, isLoading: false });

      render(<VariancePanel programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Variance Explanations (VRID)")).toBeInTheDocument();
    });
  });
});
