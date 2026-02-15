import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceForm } from "../ResourceForm";
import { ToastProvider } from "@/components/Toast";
import { ResourceType } from "@/types/resource";
import type { Resource } from "@/types/resource";

vi.mock("@/services/resourceApi", () => ({
  getResources: vi.fn(),
  getResource: vi.fn(),
  createResource: vi.fn(),
  updateResource: vi.fn(),
  deleteResource: vi.fn(),
}));

import { createResource, updateResource } from "@/services/resourceApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ToastProvider>{children}</ToastProvider>
  </QueryClientProvider>
);

const mockResource: Resource = {
  id: "res-1",
  program_id: "prog-1",
  name: "Senior Engineer",
  code: "ENG-001",
  resource_type: ResourceType.LABOR,
  capacity_per_day: 8,
  cost_rate: 150,
  effective_date: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockEquipmentResource: Resource = {
  id: "res-2",
  program_id: "prog-1",
  name: "CNC Machine",
  code: "EQP-001",
  resource_type: ResourceType.EQUIPMENT,
  capacity_per_day: 16,
  cost_rate: 250,
  effective_date: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

const mockMaterialResource: Resource = {
  id: "res-3",
  program_id: "prog-1",
  name: "Steel Plate",
  code: "MAT-001",
  resource_type: ResourceType.MATERIAL,
  capacity_per_day: 4,
  cost_rate: 75,
  effective_date: null,
  is_active: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("ResourceForm", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders create form when resource is null", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("New Resource")).toBeInTheDocument();
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("renders edit form when resource is provided", () => {
    render(
      <ResourceForm
        programId="prog-1"
        resource={mockResource}
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Edit Resource")).toBeInTheDocument();
    expect(screen.getByText("Update")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ENG-001")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Senior Engineer")).toBeInTheDocument();
  });

  it("calls onClose when cancel button is clicked", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when X button is clicked", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    // Find the X close button by its aria-label
    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when backdrop is clicked", () => {
    const { container } = render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    const backdrop = container.querySelector(".fixed.inset-0");
    if (backdrop) fireEvent.click(backdrop);

    expect(onClose).toHaveBeenCalled();
  });

  it("submits create form with correct data", async () => {
    vi.mocked(createResource).mockResolvedValue(mockResource);

    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
      target: { value: "ENG-002" },
    });
    fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
      target: { value: "Junior Engineer" },
    });

    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(createResource).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("submits update form with correct data", async () => {
    vi.mocked(updateResource).mockResolvedValue(mockResource);

    render(
      <ResourceForm
        programId="prog-1"
        resource={mockResource}
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByDisplayValue("Senior Engineer"), {
      target: { value: "Lead Engineer" },
    });

    fireEvent.click(screen.getByText("Update"));

    await waitFor(() => {
      expect(updateResource).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("converts code input to uppercase", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    const codeInput = screen.getByPlaceholderText("e.g., ENG-001");
    fireEvent.change(codeInput, { target: { value: "abc-123" } });

    expect(codeInput).toHaveValue("ABC-123");
  });

  it("has type selector with all options", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();

    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent("Labor");
    expect(options[1]).toHaveTextContent("Equipment");
    expect(options[2]).toHaveTextContent("Material");
  });

  it("has active checkbox checked by default for new resource", () => {
    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("shows error toast on create failure", async () => {
    vi.mocked(createResource).mockRejectedValue(new Error("Create failed"));

    render(
      <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
      target: { value: "ENG-002" },
    });
    fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
      target: { value: "Test" },
    });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(screen.getByText("Failed to create resource")).toBeInTheDocument();
    });
  });

  // === NEW TESTS BELOW ===

  describe("create resource - all 3 types", () => {
    it("creates a LABOR resource with default type", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "LAB-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Software Developer" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            program_id: "prog-1",
            name: "Software Developer",
            code: "LAB-001",
            resource_type: ResourceType.LABOR,
          })
        );
      });
    });

    it("creates an EQUIPMENT resource", async () => {
      vi.mocked(createResource).mockResolvedValue(mockEquipmentResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "EQP-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "CNC Machine" },
      });
      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.EQUIPMENT },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            program_id: "prog-1",
            name: "CNC Machine",
            code: "EQP-001",
            resource_type: ResourceType.EQUIPMENT,
          })
        );
      });
    });

    it("creates a MATERIAL resource", async () => {
      vi.mocked(createResource).mockResolvedValue(mockMaterialResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "MAT-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Steel Plate" },
      });
      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.MATERIAL },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            program_id: "prog-1",
            name: "Steel Plate",
            code: "MAT-001",
            resource_type: ResourceType.MATERIAL,
          })
        );
      });
    });

    it("creates resource with cost rate", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "LAB-002" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Test Engineer" },
      });
      fireEvent.change(screen.getByPlaceholderText("Optional"), {
        target: { value: "125.50" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            cost_rate: 125.5,
          })
        );
      });
    });

    it("creates resource without cost rate when left empty", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "LAB-003" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Intern" },
      });
      // Leave cost rate empty
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            cost_rate: undefined,
          })
        );
      });
    });

    it("creates resource with custom capacity per day", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "LAB-004" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Part Timer" },
      });
      fireEvent.change(screen.getByDisplayValue("8"), {
        target: { value: "4" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            capacity_per_day: 4,
          })
        );
      });
    });
  });

  describe("edit resource with pre-filled data", () => {
    it("pre-fills LABOR resource data in edit form", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByDisplayValue("ENG-001")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Senior Engineer")).toBeInTheDocument();
      expect(screen.getByDisplayValue("8")).toBeInTheDocument();
      expect(screen.getByDisplayValue("150")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.LABOR);
      expect(screen.getByRole("checkbox")).toBeChecked();
    });

    it("pre-fills EQUIPMENT resource data in edit form", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockEquipmentResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByDisplayValue("EQP-001")).toBeInTheDocument();
      expect(screen.getByDisplayValue("CNC Machine")).toBeInTheDocument();
      expect(screen.getByDisplayValue("16")).toBeInTheDocument();
      expect(screen.getByDisplayValue("250")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.EQUIPMENT);
    });

    it("pre-fills MATERIAL resource data in edit form", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockMaterialResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByDisplayValue("MAT-001")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Steel Plate")).toBeInTheDocument();
      expect(screen.getByDisplayValue("4")).toBeInTheDocument();
      expect(screen.getByDisplayValue("75")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.MATERIAL);
    });

    it("pre-fills inactive state for inactive resource", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockMaterialResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("pre-fills empty cost rate as empty string when resource has no cost rate", () => {
      const noCostResource: Resource = {
        ...mockResource,
        cost_rate: null,
      };

      render(
        <ResourceForm
          programId="prog-1"
          resource={noCostResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      const costRateInput = screen.getByPlaceholderText("Optional");
      expect(costRateInput).toHaveValue(null);
    });
  });

  describe("form validation - required fields", () => {
    it("code field is required", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const codeInput = screen.getByPlaceholderText("e.g., ENG-001");
      expect(codeInput).toBeRequired();
    });

    it("name field is required", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const nameInput = screen.getByPlaceholderText("e.g., Senior Engineer");
      expect(nameInput).toBeRequired();
    });

    it("code field has pattern for uppercase alphanumeric", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const codeInput = screen.getByPlaceholderText("e.g., ENG-001");
      expect(codeInput).toHaveAttribute("pattern", "[A-Z0-9\\-_]+");
    });

    it("shows required asterisk markers for code and name", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const labels = screen.getAllByText("*");
      expect(labels.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("submit success and error", () => {
    it("shows success toast on successful create", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "NEW-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "New Resource" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Resource created successfully")).toBeInTheDocument();
      });
    });

    it("shows success toast on successful update", async () => {
      vi.mocked(updateResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByDisplayValue("Senior Engineer"), {
        target: { value: "Staff Engineer" },
      });
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.getByText("Resource updated successfully")).toBeInTheDocument();
      });
    });

    it("shows error toast on update failure", async () => {
      vi.mocked(updateResource).mockRejectedValue(new Error("Update failed"));

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByDisplayValue("Senior Engineer"), {
        target: { value: "Staff Engineer" },
      });
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.getByText("Failed to update resource")).toBeInTheDocument();
      });
    });

    it("calls onClose after successful create", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "NEW-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "New Resource" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it("calls onClose after successful update", async () => {
      vi.mocked(updateResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it("does not call onClose on create failure", async () => {
      vi.mocked(createResource).mockRejectedValue(new Error("Create failed"));

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "NEW-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "New Resource" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(screen.getByText("Failed to create resource")).toBeInTheDocument();
      });

      expect(onClose).not.toHaveBeenCalled();
    });

    it("does not call onClose on update failure", async () => {
      vi.mocked(updateResource).mockRejectedValue(new Error("Update failed"));

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(screen.getByText("Failed to update resource")).toBeInTheDocument();
      });

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe("cancel callback", () => {
    it("calls onClose on cancel button click in create mode", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.click(screen.getByText("Cancel"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose on cancel button click in edit mode", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.click(screen.getByText("Cancel"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when Escape key is pressed", () => {
      const { container } = render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const backdrop = container.querySelector("[role='dialog']");
      if (backdrop) {
        fireEvent.keyDown(backdrop, { key: "Escape" });
      }

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose when non-Escape key is pressed", () => {
      const { container } = render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const backdrop = container.querySelector("[role='dialog']");
      if (backdrop) {
        fireEvent.keyDown(backdrop, { key: "Enter" });
      }

      expect(onClose).not.toHaveBeenCalled();
    });

    it("does not call onClose when clicking inside the form (not backdrop)", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      // Click on the form title - this is inside the modal, not the backdrop
      fireEvent.click(screen.getByText("New Resource"));

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe("type-specific behavior", () => {
    it("defaults to LABOR type for new resource", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.LABOR);
    });

    it("allows changing type to EQUIPMENT", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.EQUIPMENT },
      });

      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.EQUIPMENT);
    });

    it("allows changing type to MATERIAL", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.MATERIAL },
      });

      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.MATERIAL);
    });

    it("passes selected type to createResource", async () => {
      vi.mocked(createResource).mockResolvedValue(mockEquipmentResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "EQP-002" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Laser Cutter" },
      });
      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.EQUIPMENT },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            resource_type: ResourceType.EQUIPMENT,
          })
        );
      });
    });

    it("preserves resource type in edit mode", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockEquipmentResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("combobox")).toHaveValue(ResourceType.EQUIPMENT);
    });
  });

  describe("form field interactions", () => {
    it("capacity per day defaults to 8 for new resource", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByDisplayValue("8")).toBeInTheDocument();
    });

    it("shows helper text for capacity per day", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByText("Standard work day is 8 hours")).toBeInTheDocument();
    });

    it("allows toggling active checkbox off", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).not.toBeChecked();
    });

    it("allows toggling active checkbox back on", () => {
      render(
        <ResourceForm
          programId="prog-1"
          resource={mockMaterialResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      const checkbox = screen.getByRole("checkbox");
      expect(checkbox).not.toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();
    });

    it("sends is_active as false when checkbox unchecked during create", async () => {
      vi.mocked(createResource).mockResolvedValue(mockResource);

      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByPlaceholderText("e.g., ENG-001"), {
        target: { value: "RES-001" },
      });
      fireEvent.change(screen.getByPlaceholderText("e.g., Senior Engineer"), {
        target: { value: "Inactive Resource" },
      });
      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(createResource).toHaveBeenCalledWith(
          expect.objectContaining({
            is_active: false,
          })
        );
      });
    });

    it("updates capacity_per_day when input changes", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const capacityInput = screen.getByDisplayValue("8");
      fireEvent.change(capacityInput, { target: { value: "12" } });

      expect(capacityInput).toHaveValue(12);
    });

    it("updates cost_rate when input changes", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const costRateInput = screen.getByPlaceholderText("Optional");
      fireEvent.change(costRateInput, { target: { value: "200" } });

      expect(costRateInput).toHaveValue(200);
    });
  });

  describe("modal accessibility", () => {
    it("has role dialog", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has aria-modal attribute", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby pointing to title", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby", "resource-form-title");

      const title = document.getElementById("resource-form-title");
      expect(title).toHaveTextContent("New Resource");
    });

    it("close button has aria-label", () => {
      render(
        <ResourceForm programId="prog-1" resource={null} onClose={onClose} />,
        { wrapper: Wrapper }
      );

      expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    });
  });

  describe("update form sends correct payload", () => {
    it("sends updated name and code in update payload", async () => {
      vi.mocked(updateResource).mockResolvedValue({
        ...mockResource,
        name: "Lead Engineer",
        code: "ENG-100",
      });

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByDisplayValue("Senior Engineer"), {
        target: { value: "Lead Engineer" },
      });
      fireEvent.change(screen.getByDisplayValue("ENG-001"), {
        target: { value: "ENG-100" },
      });
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(updateResource).toHaveBeenCalledWith(
          "res-1",
          expect.objectContaining({
            name: "Lead Engineer",
            code: "ENG-100",
          })
        );
      });
    });

    it("sends updated resource_type in update payload", async () => {
      vi.mocked(updateResource).mockResolvedValue({
        ...mockResource,
        resource_type: ResourceType.EQUIPMENT,
      });

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: ResourceType.EQUIPMENT },
      });
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(updateResource).toHaveBeenCalledWith(
          "res-1",
          expect.objectContaining({
            resource_type: ResourceType.EQUIPMENT,
          })
        );
      });
    });

    it("sends updated is_active in update payload", async () => {
      vi.mocked(updateResource).mockResolvedValue({
        ...mockResource,
        is_active: false,
      });

      render(
        <ResourceForm
          programId="prog-1"
          resource={mockResource}
          onClose={onClose}
        />,
        { wrapper: Wrapper }
      );

      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(screen.getByText("Update"));

      await waitFor(() => {
        expect(updateResource).toHaveBeenCalledWith(
          "res-1",
          expect.objectContaining({
            is_active: false,
          })
        );
      });
    });
  });
});
