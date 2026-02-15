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

let mockCreateIsPending = false;
let mockTestIsPending = false;
let mockSyncIsPending = false;

vi.mock("@/hooks/useJira", () => ({
  useJiraIntegration: (...args: unknown[]) => mockUseJiraIntegration(...args),
  useCreateJiraIntegration: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: mockCreateIsPending,
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
    isPending: mockTestIsPending,
  }),
  useSyncJira: () => ({
    mutateAsync: mockSyncMutateAsync,
    isPending: mockSyncIsPending,
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
    mockCreateIsPending = false;
    mockTestIsPending = false;
    mockSyncIsPending = false;
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

  // --- New tests for improved coverage ---

  describe("form validation", () => {
    it("shows error toast when submitting with empty fields", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Save Configuration"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).not.toHaveBeenCalled();
      });

      expect(await screen.findByText("All fields are required")).toBeInTheDocument();
    });

    it("shows error toast when only some fields are filled", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.change(screen.getByLabelText("Jira URL"), {
        target: { value: "https://test.atlassian.net" },
      });
      fireEvent.change(screen.getByLabelText("Email"), {
        target: { value: "user@test.com" },
      });
      // Leave API Token and Project Key empty
      fireEvent.click(screen.getByText("Save Configuration"));

      await waitFor(() => {
        expect(mockCreateMutateAsync).not.toHaveBeenCalled();
      });

      expect(await screen.findByText("All fields are required")).toBeInTheDocument();
    });
  });

  describe("create integration error handling", () => {
    it("shows error toast when create fails", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
      });
      mockCreateMutateAsync.mockRejectedValue(new Error("Network error"));

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

      expect(await screen.findByText("Failed to create Jira integration")).toBeInTheDocument();
    });

    it("shows success toast when create succeeds", async () => {
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

      expect(await screen.findByText("Jira integration created")).toBeInTheDocument();
    });

    it("shows 'Connecting...' text when create is pending", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Not found"),
      });
      mockCreateIsPending = true;

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Connecting...")).toBeInTheDocument();
    });
  });

  describe("disconnect from Jira", () => {
    it("deletes integration when user confirms", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockDeleteMutateAsync.mockResolvedValue(undefined);
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Remove"));

      expect(window.confirm).toHaveBeenCalledWith(
        "Delete this Jira integration? This cannot be undone."
      );

      await waitFor(() => {
        expect(mockDeleteMutateAsync).toHaveBeenCalledWith("jira-1");
      });

      expect(await screen.findByText("Jira integration deleted")).toBeInTheDocument();
    });

    it("does not delete integration when user cancels confirmation", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      vi.spyOn(window, "confirm").mockReturnValue(false);

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Remove"));

      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteMutateAsync).not.toHaveBeenCalled();
    });

    it("shows error toast when delete fails", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockDeleteMutateAsync.mockRejectedValue(new Error("Network error"));
      vi.spyOn(window, "confirm").mockReturnValue(true);

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Remove"));

      expect(await screen.findByText("Failed to delete integration")).toBeInTheDocument();
    });
  });

  describe("sync buttons", () => {
    it("calls sync with 'wbs' type when Sync WBS clicked", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockSyncMutateAsync.mockResolvedValue({ synced: 5, total_items: 10 });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Sync WBS"));

      await waitFor(() => {
        expect(mockSyncMutateAsync).toHaveBeenCalledWith({
          integrationId: "jira-1",
          type: "wbs",
        });
      });

      expect(await screen.findByText("Synced 5/10 items")).toBeInTheDocument();
    });

    it("calls sync with 'activities' type when Sync Activities clicked", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockSyncMutateAsync.mockResolvedValue({ synced: 8, total_items: 8 });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Sync Activities"));

      await waitFor(() => {
        expect(mockSyncMutateAsync).toHaveBeenCalledWith({
          integrationId: "jira-1",
          type: "activities",
        });
      });

      expect(await screen.findByText("Synced 8/8 items")).toBeInTheDocument();
    });

    it("calls sync with 'progress' type when Sync Progress clicked", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockSyncMutateAsync.mockResolvedValue({ synced: 3, total_items: 5 });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Sync Progress"));

      await waitFor(() => {
        expect(mockSyncMutateAsync).toHaveBeenCalledWith({
          integrationId: "jira-1",
          type: "progress",
        });
      });

      expect(await screen.findByText("Synced 3/5 items")).toBeInTheDocument();
    });

    it("shows error toast when sync fails", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockSyncMutateAsync.mockRejectedValue(new Error("Sync error"));

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Sync WBS"));

      expect(await screen.findByText("Sync failed")).toBeInTheDocument();
    });

    it("disables sync buttons when sync is pending", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockSyncIsPending = true;

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Sync WBS")).toBeDisabled();
      expect(screen.getByText("Sync Activities")).toBeDisabled();
      expect(screen.getByText("Sync Progress")).toBeDisabled();
    });
  });

  describe("test connection", () => {
    it("shows success toast with project name when test succeeds", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestMutateAsync.mockResolvedValue({
        success: true,
        message: "Connected",
        project_name: "My Jira Project",
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Test Connection"));

      expect(await screen.findByText("Connected to My Jira Project")).toBeInTheDocument();
    });

    it("shows success toast with project key when project_name is missing", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestMutateAsync.mockResolvedValue({
        success: true,
        message: "Connected",
        project_name: null,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Test Connection"));

      expect(await screen.findByText("Connected to PROJ")).toBeInTheDocument();
    });

    it("shows error toast with message when test returns failure", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestMutateAsync.mockResolvedValue({
        success: false,
        message: "Invalid credentials",
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Test Connection"));

      expect(
        await screen.findByText("Connection failed: Invalid credentials")
      ).toBeInTheDocument();
    });

    it("shows error toast when test connection throws", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestMutateAsync.mockRejectedValue(new Error("Network error"));

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Test Connection"));

      expect(await screen.findByText("Connection test failed")).toBeInTheDocument();
    });

    it("shows 'Testing...' when test is pending", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestIsPending = true;

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Testing...")).toBeInTheDocument();
    });

    it("disables test connection button when pending", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockTestIsPending = true;

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Testing...")).toBeDisabled();
    });
  });

  describe("toggle sync", () => {
    it("toggles sync from enabled to disabled", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUpdateMutateAsync.mockResolvedValue(undefined);

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Disable Sync"));

      await waitFor(() => {
        expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
          integrationId: "jira-1",
          data: { sync_enabled: false },
        });
      });

      expect(await screen.findByText("Sync disabled")).toBeInTheDocument();
    });

    it("toggles sync from disabled to enabled", async () => {
      const disabledIntegration = { ...mockIntegration, sync_enabled: false };
      mockUseJiraIntegration.mockReturnValue({
        data: disabledIntegration,
        isLoading: false,
        error: null,
      });
      mockUpdateMutateAsync.mockResolvedValue(undefined);

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Sync Disabled")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Enable Sync"));

      await waitFor(() => {
        expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
          integrationId: "jira-1",
          data: { sync_enabled: true },
        });
      });

      expect(await screen.findByText("Sync enabled")).toBeInTheDocument();
    });

    it("shows error toast when toggle sync fails", async () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUpdateMutateAsync.mockRejectedValue(new Error("Update failed"));

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      fireEvent.click(screen.getByText("Disable Sync"));

      expect(await screen.findByText("Failed to update sync setting")).toBeInTheDocument();
    });
  });

  describe("integration status display", () => {
    it("shows last sync time when available", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Last Sync")).toBeInTheDocument();
      // The date is formatted via toLocaleString, just verify it's not "Never"
      expect(screen.queryByText("Never")).not.toBeInTheDocument();
    });

    it("shows 'Never' when last_sync_at is null", () => {
      const noSyncIntegration = { ...mockIntegration, last_sync_at: null };
      mockUseJiraIntegration.mockReturnValue({
        data: noSyncIntegration,
        isLoading: false,
        error: null,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Never")).toBeInTheDocument();
    });

    it("shows Sync Disabled status for disabled integration", () => {
      const disabledIntegration = { ...mockIntegration, sync_enabled: false };
      mockUseJiraIntegration.mockReturnValue({
        data: disabledIntegration,
        isLoading: false,
        error: null,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Sync Disabled")).toBeInTheDocument();
    });

    it("shows setup form when data is null and no error", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Connect to Jira Cloud")).toBeInTheDocument();
    });
  });

  describe("mappings section", () => {
    it("shows loading state for mappings", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUseJiraMappings.mockReturnValue({ data: undefined, isLoading: true });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Loading mappings...")).toBeInTheDocument();
    });

    it("shows mappings table when mappings exist", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUseJiraMappings.mockReturnValue({
        data: [
          {
            id: "map-1",
            entity_type: "wbs",
            local_id: "wbs-abc-123",
            jira_issue_key: "PROJ-1",
            last_synced_at: "2026-02-01T12:00:00Z",
          },
          {
            id: "map-2",
            entity_type: "activity",
            local_id: "act-def-456",
            jira_issue_key: "PROJ-2",
            last_synced_at: null,
          },
        ],
        isLoading: false,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("wbs")).toBeInTheDocument();
      expect(screen.getByText("PROJ-1")).toBeInTheDocument();
      expect(screen.getByText("activity")).toBeInTheDocument();
      expect(screen.getByText("PROJ-2")).toBeInTheDocument();
      expect(screen.getByText("wbs-abc-123")).toBeInTheDocument();
      expect(screen.getByText("act-def-456")).toBeInTheDocument();
      // mapping with null last_synced_at shows "-"
      expect(screen.getByText("-")).toBeInTheDocument();
    });
  });

  describe("sync logs section", () => {
    it("shows loading state for sync logs", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUseJiraSyncLogs.mockReturnValue({ data: undefined, isLoading: true });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("Loading logs...")).toBeInTheDocument();
    });

    it("shows sync logs table when logs exist", () => {
      mockUseJiraIntegration.mockReturnValue({
        data: mockIntegration,
        isLoading: false,
        error: null,
      });
      mockUseJiraSyncLogs.mockReturnValue({
        data: {
          items: [
            {
              id: "log-1",
              started_at: "2026-02-01T12:00:00Z",
              sync_type: "wbs",
              status: "SUCCESS",
              items_synced: 5,
              items_failed: 0,
            },
            {
              id: "log-2",
              started_at: "2026-02-01T10:00:00Z",
              sync_type: "activities",
              status: "FAILED",
              items_synced: 2,
              items_failed: 3,
            },
            {
              id: "log-3",
              started_at: "2026-02-01T08:00:00Z",
              sync_type: "progress",
              status: "IN_PROGRESS",
              items_synced: 1,
              items_failed: 0,
            },
          ],
          total: 3,
        },
        isLoading: false,
      });

      render(<JiraSettings programId="prog-1" />, { wrapper: Wrapper });

      expect(screen.getByText("SUCCESS")).toBeInTheDocument();
      expect(screen.getByText("FAILED")).toBeInTheDocument();
      expect(screen.getByText("IN_PROGRESS")).toBeInTheDocument();
      expect(screen.getByText("wbs")).toBeInTheDocument();
      expect(screen.getByText("activities")).toBeInTheDocument();
      expect(screen.getByText("progress")).toBeInTheDocument();
    });
  });
});
