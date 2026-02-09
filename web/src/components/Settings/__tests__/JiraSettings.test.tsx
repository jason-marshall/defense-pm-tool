import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JiraSettings } from "../JiraSettings";
import { ToastProvider } from "@/components/Toast";

const mockUseJiraIntegration = vi.fn();
const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();
const mockTestMutateAsync = vi.fn();
const mockSyncMutateAsync = vi.fn();
const mockUseJiraMappings = vi.fn();
const mockUseJiraSyncLogs = vi.fn();

vi.mock("@/hooks/useJira", () => ({
  useJiraIntegration: (...args: unknown[]) => mockUseJiraIntegration(...args),
  useCreateJiraIntegration: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateJiraIntegration: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteJiraIntegration: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
  useTestJiraConnection: () => ({
    mutateAsync: mockTestMutateAsync,
    isPending: false,
  }),
  useSyncJira: () => ({
    mutateAsync: mockSyncMutateAsync,
    isPending: false,
  }),
  useJiraMappings: (...args: unknown[]) => mockUseJiraMappings(...args),
  useJiraSyncLogs: (...args: unknown[]) => mockUseJiraSyncLogs(...args),
  useCreateJiraMapping: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteJiraMapping: () => ({
    mutateAsync: vi.fn(),
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

const mockIntegration = {
  id: "jira-1",
  program_id: "prog-1",
  jira_url: "https://test.atlassian.net",
  email: "user@test.com",
  project_key: "PROJ",
  sync_enabled: true,
  sync_direction: "BIDIRECTIONAL",
  last_sync_at: "2026-02-01T12:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("JiraSettings", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.clearAllMocks();
    mockUseJiraMappings.mockReturnValue({ data: [], isLoading: false });
    mockUseJiraSyncLogs.mockReturnValue({ data: { items: [], total: 0 }, isLoading: false });
  });

  it("shows loading state", () => {
    mockUseJiraIntegration.mockReturnValue({ data: undefined, isLoading: true, error: null });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Loading Jira settings...")).toBeInTheDocument();
  });

  it("shows setup form when no integration exists", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Not found"),
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Connect to Jira Cloud")).toBeInTheDocument();
    expect(screen.getByLabelText("Jira URL")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("API Token")).toBeInTheDocument();
    expect(screen.getByLabelText("Project Key")).toBeInTheDocument();
  });

  it("submits setup form", async () => {
    mockUseJiraIntegration.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Not found"),
    });
    mockCreateMutateAsync.mockResolvedValue(mockIntegration);

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.change(screen.getByLabelText("Jira URL"), {
      target: { value: "https://test.atlassian.net" },
    });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@test.com" },
    });
    fireEvent.change(screen.getByLabelText("API Token"), {
      target: { value: "secret-token" },
    });
    fireEvent.change(screen.getByLabelText("Project Key"), {
      target: { value: "PROJ" },
    });
    fireEvent.click(screen.getByText("Save Configuration"));

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith({
        program_id: "prog-1",
        jira_url: "https://test.atlassian.net",
        email: "user@test.com",
        api_token: "secret-token",
        project_key: "PROJ",
      });
    });
  });

  it("shows connected view with integration details", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Jira Cloud Integration")).toBeInTheDocument();
    expect(screen.getByText("https://test.atlassian.net")).toBeInTheDocument();
    expect(screen.getByText("PROJ")).toBeInTheDocument();
    expect(screen.getByText("Sync Enabled")).toBeInTheDocument();
  });

  it("shows sync operation buttons when connected", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Sync WBS")).toBeInTheDocument();
    expect(screen.getByText("Sync Activities")).toBeInTheDocument();
    expect(screen.getByText("Sync Progress")).toBeInTheDocument();
  });

  it("shows test connection button", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("Test Connection")).toBeInTheDocument();
  });

  it("calls test connection", async () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });
    mockTestMutateAsync.mockResolvedValue({
      success: true,
      message: "Connected",
      project_name: "Test Project",
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    fireEvent.click(screen.getByText("Test Connection"));

    await waitFor(() => {
      expect(mockTestMutateAsync).toHaveBeenCalledWith("jira-1");
    });
  });

  it("shows empty mappings message", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText(/No mappings yet/)).toBeInTheDocument();
  });

  it("shows empty sync history message", () => {
    mockUseJiraIntegration.mockReturnValue({
      data: mockIntegration,
      isLoading: false,
      error: null,
    });

    render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

    expect(screen.getByText("No sync history.")).toBeInTheDocument();
  });
});
