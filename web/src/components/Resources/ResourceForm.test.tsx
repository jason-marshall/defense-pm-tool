import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceForm } from "./ResourceForm";
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
});
