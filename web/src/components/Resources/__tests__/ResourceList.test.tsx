import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceList } from "../ResourceList";
import { ToastProvider } from "@/components/Toast";
import type { ResourceListResponse } from "@/types/resource";
import { ResourceType } from "@/types/resource";

vi.mock("@/services/resourceApi", () => ({
  getResources: vi.fn(),
  getResource: vi.fn(),
  createResource: vi.fn(),
  updateResource: vi.fn(),
  deleteResource: vi.fn(),
}));

import { getResources, deleteResource } from "@/services/resourceApi";

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

const mockResourceList: ResourceListResponse = {
  items: [
    {
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
    },
    {
      id: "res-2",
      program_id: "prog-1",
      name: "Crane A",
      code: "EQP-001",
      resource_type: ResourceType.EQUIPMENT,
      capacity_per_day: 10,
      cost_rate: null,
      effective_date: null,
      is_active: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  pages: 1,
};

describe("ResourceList", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(getResources).mockImplementation(() => new Promise(() => {}));

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading resources...")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    vi.mocked(getResources).mockRejectedValue(new Error("Network error"));

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    expect(
      await screen.findByText(/Error loading resources/)
    ).toBeInTheDocument();
    expect(screen.getByText(/Network error/)).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.mocked(getResources).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      pages: 0,
    });

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    expect(await screen.findByText("No resources found.")).toBeInTheDocument();
    expect(screen.getByText("Create your first resource")).toBeInTheDocument();
  });

  it("renders resource table with data", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    expect(await screen.findByText("ENG-001")).toBeInTheDocument();
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText("EQP-001")).toBeInTheDocument();
    expect(screen.getByText("Crane A")).toBeInTheDocument();
  });

  it("shows active/inactive status", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");
    // "Active" appears as column header AND cell value, so check for both statuses in cells
    const activeCells = screen.getAllByText("Active");
    expect(activeCells.length).toBeGreaterThanOrEqual(2); // header + cell
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("shows cost rate or dash for missing", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    expect(await screen.findByText("$150/h")).toBeInTheDocument();
    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("opens create form when Add Resource is clicked", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");
    fireEvent.click(screen.getByText("Add Resource"));

    expect(screen.getByText("New Resource")).toBeInTheDocument();
  });

  it("opens edit form when edit button is clicked", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");
    const editButtons = screen.getAllByTitle("Edit resource");
    fireEvent.click(editButtons[0]);

    expect(screen.getByText("Edit Resource")).toBeInTheDocument();
  });

  it("has type filter dropdown", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();

    fireEvent.change(select, { target: { value: "LABOR" } });

    await waitFor(() => {
      expect(getResources).toHaveBeenCalledWith("prog-1", {
        resource_type: "LABOR",
      });
    });
  });

  it("deletes resource with confirmation", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);
    vi.mocked(deleteResource).mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");
    const deleteButtons = screen.getAllByTitle("Delete resource");
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith(
      "Are you sure you want to delete this resource?"
    );
  });

  it("does not delete when confirmation is cancelled", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResourceList);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<ResourceList programId="prog-1" />, { wrapper: Wrapper });

    await screen.findByText("ENG-001");
    const deleteButtons = screen.getAllByTitle("Delete resource");
    fireEvent.click(deleteButtons[0]);

    expect(deleteResource).not.toHaveBeenCalled();
  });
});
