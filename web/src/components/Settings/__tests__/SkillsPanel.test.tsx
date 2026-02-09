import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SkillsPanel } from "../SkillsPanel";
import { ToastProvider } from "@/components/Toast";

const mockUseSkills = vi.fn();
const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/hooks/useSkills", () => ({
  useSkills: (...args: unknown[]) => mockUseSkills(...args),
  useCreateSkill: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateSkill: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteSkill: () => ({
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

const mockSkillsData = {
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
      name: "PMP Certification",
      code: "PMP",
      category: "Certification",
      description: "Project Management Professional",
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

describe("SkillsPanel", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
  });

  it("shows loading state", () => {
    mockUseSkills.mockReturnValue({ data: undefined, isLoading: true });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading skills...")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    mockUseSkills.mockReturnValue({
      data: { items: [], total: 0, page: 1, page_size: 20 },
      isLoading: false,
    });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No skills defined.")).toBeInTheDocument();
  });

  it("displays skills in table", () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Systems Engineering")).toBeInTheDocument();
    expect(screen.getByText("SE")).toBeInTheDocument();
    expect(screen.getByText("PMP Certification")).toBeInTheDocument();
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("renders category filter", () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    const selects = screen.getAllByRole("combobox");
    expect(selects[0]).toBeInTheDocument();
  });

  it("opens create form", () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Skill"));

    expect(screen.getByText("New Skill")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Code")).toBeInTheDocument();
  });

  it("submits create form", async () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });
    mockCreateMutateAsync.mockResolvedValue({});

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Skill"));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New Skill" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "NS-001" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "New Skill",
          code: "NS-001",
          program_id: "prog-1",
        })
      );
    });
  });

  it("cancels form", () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Add Skill"));
    expect(screen.getByText("New Skill")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("New Skill")).not.toBeInTheDocument();
  });

  it("has Add Skill button", () => {
    mockUseSkills.mockReturnValue({ data: mockSkillsData, isLoading: false });

    render(<SkillsPanel programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Add Skill")).toBeInTheDocument();
  });
});
