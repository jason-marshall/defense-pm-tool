import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WBSTree } from "../WBSTree";

vi.mock("@/services/wbsApi", () => ({
  getWBSTree: vi.fn(),
  getWBSElements: vi.fn(),
  getWBSElement: vi.fn(),
  createWBSElement: vi.fn(),
  updateWBSElement: vi.fn(),
  deleteWBSElement: vi.fn(),
}));

import { getWBSTree, createWBSElement } from "@/services/wbsApi";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

const mockTree = [
  {
    id: "wbs-1",
    programId: "prog-1",
    parentId: null,
    code: "1.0",
    name: "Project Root",
    description: null,
    path: "1",
    level: 0,
    budgetedCost: "100000",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    isControlAccount: false,
    children: [
      {
        id: "wbs-2",
        programId: "prog-1",
        parentId: "wbs-1",
        code: "1.1",
        name: "Design Phase",
        description: "Design activities",
        path: "1.1",
        level: 1,
        budgetedCost: "50000",
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
        isControlAccount: true,
        children: [],
      },
      {
        id: "wbs-3",
        programId: "prog-1",
        parentId: "wbs-1",
        code: "1.2",
        name: "Build Phase",
        description: null,
        path: "1.2",
        level: 1,
        budgetedCost: "50000",
        createdAt: "2026-01-01T00:00:00Z",
        updatedAt: "2026-01-01T00:00:00Z",
        isControlAccount: false,
        children: [],
      },
    ],
  },
];

describe("WBSTree", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(getWBSTree).mockImplementation(() => new Promise(() => {}));

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(screen.getByText("Loading WBS hierarchy...")).toBeInTheDocument();
  });

  it("renders error state", async () => {
    vi.mocked(getWBSTree).mockRejectedValue(new Error("API Error"));

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/Error loading WBS/)
    ).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(
      await screen.findByText(/No WBS elements/)
    ).toBeInTheDocument();
  });

  it("renders tree with data", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);

    render(<WBSTree programId="prog-1" />, { wrapper });

    expect(await screen.findByText("Project Root")).toBeInTheDocument();
    expect(screen.getByText("1.0")).toBeInTheDocument();
  });

  it("calls onSelect when element is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);
    const onSelect = vi.fn();

    render(<WBSTree programId="prog-1" onSelect={onSelect} />, { wrapper });

    await screen.findByText("Project Root");
    fireEvent.click(screen.getByText("Project Root"));

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: "wbs-1", name: "Project Root" })
    );
  });

  it("opens add root modal when Add Root Element button is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue(mockTree);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText("Project Root");

    // Look for the "Add Root Element" button in toolbar
    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find(
      (btn) => btn.textContent?.includes("Add Root") || btn.textContent?.includes("Add")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();
    }
  });

  it("submits add form with correct data", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);
    vi.mocked(createWBSElement).mockResolvedValue({
      id: "new-1",
      programId: "prog-1",
      code: "1.0",
      name: "New Element",
      description: null,
      level: 0,
      budgetedCost: "0",
    } as any);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText(/No WBS elements/);

    // Click add root button
    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find((btn) =>
      btn.textContent?.includes("Add Root")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);

      // Fill form
      fireEvent.change(screen.getByLabelText(/WBS Code/), {
        target: { value: "1.0" },
      });
      fireEvent.change(screen.getByLabelText(/Name \*/), {
        target: { value: "New Root" },
      });

      fireEvent.click(screen.getByText("Add Element"));

      await waitFor(() => {
        expect(createWBSElement).toHaveBeenCalled();
      });
    }
  });

  it("closes modal when cancel is clicked", async () => {
    vi.mocked(getWBSTree).mockResolvedValue([]);

    render(<WBSTree programId="prog-1" />, { wrapper });

    await screen.findByText(/No WBS elements/);

    const addButtons = screen.getAllByRole("button");
    const addRootBtn = addButtons.find((btn) =>
      btn.textContent?.includes("Add Root")
    );
    if (addRootBtn) {
      fireEvent.click(addRootBtn);
      expect(screen.getByText("Add Root Element")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));
      await waitFor(() => {
        expect(screen.queryByText("Add Root Element")).not.toBeInTheDocument();
      });
    }
  });
});
