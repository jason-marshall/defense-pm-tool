import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssignmentModal } from "./AssignmentModal";
import { ToastProvider } from "@/components/Toast";
import { ResourceType } from "@/types/resource";

vi.mock("@/services/resourceApi", () => ({
  getResources: vi.fn(),
  getResource: vi.fn(),
  createResource: vi.fn(),
  updateResource: vi.fn(),
  deleteResource: vi.fn(),
}));

vi.mock("@/services/assignmentApi", () => ({
  getActivityAssignments: vi.fn(),
  getResourceAssignments: vi.fn(),
  createAssignment: vi.fn(),
  updateAssignment: vi.fn(),
  deleteAssignment: vi.fn(),
}));

import { getResources } from "@/services/resourceApi";
import {
  getActivityAssignments,
  createAssignment,
  deleteAssignment,
} from "@/services/assignmentApi";

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

const mockResources = {
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
      name: "Junior Engineer",
      code: "ENG-002",
      resource_type: ResourceType.LABOR,
      capacity_per_day: 8,
      cost_rate: 75,
      effective_date: null,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  pages: 1,
};

const mockAssignments = [
  {
    id: "assign-1",
    activity_id: "act-1",
    resource_id: "res-1",
    units: 1.0,
    start_date: null,
    finish_date: null,
    resource: {
      id: "res-1",
      code: "ENG-001",
      name: "Senior Engineer",
      resource_type: "LABOR",
    },
  },
];

describe("AssignmentModal", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders modal with activity name", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue(mockAssignments);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Assign Resources")).toBeInTheDocument();
    expect(screen.getByText("Design Review")).toBeInTheDocument();
  });

  it("shows current assignments", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue(mockAssignments);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(
      await screen.findByText("Current Assignments")
    ).toBeInTheDocument();
    // Wait for the assignments to load
    expect(await screen.findByText("100%")).toBeInTheDocument();
    expect(screen.getByText("ENG-001")).toBeInTheDocument();
  });

  it("shows empty state when no assignments", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue([]);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(
      await screen.findByText("No resources assigned yet")
    ).toBeInTheDocument();
  });

  it("only shows unassigned resources in dropdown", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue(mockAssignments);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    await screen.findByText("ENG-001");

    // The dropdown should only show res-2 (res-1 is already assigned)
    const select = screen.getByRole("combobox");
    const options = select.querySelectorAll("option");
    const optionTexts = Array.from(options).map((o) => o.textContent);
    expect(optionTexts).toContain("Select resource...");
    expect(optionTexts.some((t) => t?.includes("ENG-002"))).toBe(true);
    expect(optionTexts.some((t) => t?.includes("ENG-001"))).toBe(false);
  });

  it("creates assignment when assign button is clicked", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue([]);
    vi.mocked(createAssignment).mockResolvedValue({} as any);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    // Wait for "No resources assigned yet" text to confirm loading is done
    await screen.findByText("No resources assigned yet");
    // Wait for dropdown to be available
    await screen.findByText("Select resource...");

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "res-1" } });
    fireEvent.click(screen.getByText("Assign"));

    await waitFor(() => {
      expect(createAssignment).toHaveBeenCalledWith("res-1", {
        activity_id: "act-1",
        resource_id: "res-1",
        units: 1,
      });
    });
  });

  it("removes assignment when delete is clicked", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue(mockAssignments);
    vi.mocked(deleteAssignment).mockResolvedValue(undefined);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    await screen.findByText("ENG-001");

    const removeBtn = screen.getByTitle("Remove assignment");
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(deleteAssignment).toHaveBeenCalledWith("assign-1");
    });
  });

  it("calls onClose when Done button is clicked", async () => {
    vi.mocked(getResources).mockResolvedValue(mockResources);
    vi.mocked(getActivityAssignments).mockResolvedValue([]);

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    await screen.findByText("Add Assignment");
    fireEvent.click(screen.getByText("Done"));

    expect(onClose).toHaveBeenCalled();
  });

  it("shows message when all resources are assigned", async () => {
    vi.mocked(getResources).mockResolvedValue({
      ...mockResources,
      items: [mockResources.items[0]], // Only res-1
    });
    vi.mocked(getActivityAssignments).mockResolvedValue(mockAssignments); // res-1 assigned

    render(
      <AssignmentModal
        activityId="act-1"
        activityName="Design Review"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(
      await screen.findByText(
        "All active resources are already assigned to this activity."
      )
    ).toBeInTheDocument();
  });
});
