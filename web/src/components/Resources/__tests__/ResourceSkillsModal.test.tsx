import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResourceSkillsModal } from "../ResourceSkillsModal";
import { ToastProvider } from "@/components/Toast";

const mockUseResourceSkills = vi.fn();
const mockUseSkills = vi.fn();
const mockAddMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockRemoveMutateAsync = vi.fn();

vi.mock("@/hooks/useSkills", () => ({
  useResourceSkills: (...args: unknown[]) => mockUseResourceSkills(...args),
  useSkills: (...args: unknown[]) => mockUseSkills(...args),
  useAddResourceSkill: () => ({
    mutateAsync: mockAddMutateAsync,
    isPending: false,
  }),
  useUpdateResourceSkill: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useRemoveResourceSkill: () => ({
    mutateAsync: mockRemoveMutateAsync,
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

const mockSkillsList = {
  items: [
    {
      id: "skill-1",
      name: "Systems Engineering",
      code: "SE",
      category: "Technical",
      description: null,
      is_active: true,
      requires_certification: false,
      certification_expiry_months: null,
      program_id: "prog-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "skill-2",
      name: "PMP",
      code: "PMP",
      category: "Certification",
      description: null,
      is_active: true,
      requires_certification: true,
      certification_expiry_months: 36,
      program_id: "prog-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

const mockResourceSkills = [
  {
    id: "rs-1",
    resource_id: "res-1",
    skill_id: "skill-1",
    proficiency_level: 3,
    is_certified: false,
    certification_date: null,
    certification_expires_at: null,
    verified_by: null,
    verified_at: null,
    notes: null,
    skill: mockSkillsList.items[0],
  },
];

describe("ResourceSkillsModal", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("renders modal with resource name", () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Skills - John Smith")).toBeInTheDocument();
  });

  it("shows assigned skills in table", () => {
    mockUseResourceSkills.mockReturnValue({ data: mockResourceSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Systems Engineering")).toBeInTheDocument();
  });

  it("shows empty state when no skills assigned", () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("No skills assigned.")).toBeInTheDocument();
  });

  it("calls onClose when Close button clicked", () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls add mutation when adding a skill", async () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockAddMutateAsync.mockResolvedValue({});

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Skill"), { target: { value: "skill-1" } });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(mockAddMutateAsync).toHaveBeenCalledWith({
        resourceId: "res-1",
        data: {
          skill_id: "skill-1",
          proficiency_level: 1,
          is_certified: false,
        },
      });
    });
  });

  it("renders assign skill form", () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Assign Skill")).toBeInTheDocument();
    expect(screen.getByLabelText("Skill")).toBeInTheDocument();
    expect(screen.getByLabelText("Level")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockUseResourceSkills.mockReturnValue({ data: undefined, isLoading: true });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    expect(screen.getByText("Loading skills...")).toBeInTheDocument();
  });

  it("only shows unassigned skills in dropdown", () => {
    mockUseResourceSkills.mockReturnValue({ data: mockResourceSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    const skillSelect = screen.getByLabelText("Skill");
    const options = Array.from((skillSelect as HTMLSelectElement).options);
    const optionTexts = options.map((o) => o.text);
    expect(optionTexts).toContain("PMP (PMP)");
    expect(optionTexts).not.toContain("Systems Engineering (SE)");
  });

  it("updates proficiency when select changes", async () => {
    mockUseResourceSkills.mockReturnValue({ data: mockResourceSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockUpdateMutateAsync.mockResolvedValue({});

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    // Find the proficiency select in the table (value=3 initially)
    const profSelects = screen.getAllByRole("combobox");
    const tableSelect = profSelects.find(
      (s) => (s as HTMLSelectElement).value === "3"
    );
    expect(tableSelect).toBeTruthy();
    fireEvent.change(tableSelect!, { target: { value: "5" } });

    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
        resourceId: "res-1",
        skillId: "skill-1",
        data: { proficiency_level: 5 },
      });
    });
  });

  it("removes skill when remove button clicked", async () => {
    mockUseResourceSkills.mockReturnValue({ data: mockResourceSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockRemoveMutateAsync.mockResolvedValue({});

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByLabelText("Remove skill"));

    await waitFor(() => {
      expect(mockRemoveMutateAsync).toHaveBeenCalledWith({
        resourceId: "res-1",
        skillId: "skill-1",
      });
    });
  });

  it("shows certified status", () => {
    const certifiedSkills = [
      { ...mockResourceSkills[0], is_certified: true },
    ];
    mockUseResourceSkills.mockReturnValue({ data: certifiedSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    const certifiedElements = screen.getAllByText("Certified");
    const certifiedSpan = certifiedElements.find(
      (el) => el.tagName === "SPAN" && el.classList.contains("text-green-600")
    );
    expect(certifiedSpan).toBeInTheDocument();
  });

  it("resets form after adding skill", async () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockAddMutateAsync.mockResolvedValue({});

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Skill"), { target: { value: "skill-1" } });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(mockAddMutateAsync).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect((screen.getByLabelText("Skill") as HTMLSelectElement).value).toBe("");
    });
  });

  it("shows error toast on add failure", async () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockAddMutateAsync.mockRejectedValue(new Error("Server error"));

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.change(screen.getByLabelText("Skill"), { target: { value: "skill-1" } });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(screen.getByText("Failed to add skill")).toBeInTheDocument();
    });
  });

  it("shows error toast on remove failure", async () => {
    mockUseResourceSkills.mockReturnValue({ data: mockResourceSkills, isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });
    mockRemoveMutateAsync.mockRejectedValue(new Error("Server error"));

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    fireEvent.click(screen.getByLabelText("Remove skill"));

    await waitFor(() => {
      expect(screen.getByText("Failed to remove skill")).toBeInTheDocument();
    });
  });

  it("disables Add button when no skill selected", () => {
    mockUseResourceSkills.mockReturnValue({ data: [], isLoading: false });
    mockUseSkills.mockReturnValue({ data: mockSkillsList });

    render(
      <ResourceSkillsModal
        resourceId="res-1"
        resourceName="John Smith"
        programId="prog-1"
        onClose={onClose}
      />,
      { wrapper: Wrapper }
    );

    const addBtn = screen.getByText("Add").closest("button");
    expect(addBtn).toBeDisabled();
  });
});
