/**
 * Jira integration settings panel.
 * Shows setup form when no integration exists, or status/sync/mappings/logs when configured.
 */

import { useState } from "react";
import {
  useJiraIntegration,
  useCreateJiraIntegration,
  useUpdateJiraIntegration,
  useDeleteJiraIntegration,
  useTestJiraConnection,
  useSyncJira,
  useJiraMappings,
  useJiraSyncLogs,
} from "@/hooks/useJira";
import { useToast } from "@/components/Toast";
import { Trash2 } from "lucide-react";

interface JiraSettingsProps {
  programId: string;
}

export function JiraSettings({ programId }: JiraSettingsProps) {
  const { data: integration, isLoading, error } = useJiraIntegration(programId);
  const createMutation = useCreateJiraIntegration();
  const updateMutation = useUpdateJiraIntegration();
  const deleteMutation = useDeleteJiraIntegration();
  const testMutation = useTestJiraConnection();
  const syncMutation = useSyncJira();
  const toast = useToast();

  // Setup form state
  const [jiraUrl, setJiraUrl] = useState("");
  const [email, setEmail] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [projectKey, setProjectKey] = useState("");

  const hasIntegration = !!integration && !error;

  const handleCreate = async () => {
    if (!jiraUrl || !email || !apiToken || !projectKey) {
      toast.error("All fields are required");
      return;
    }
    try {
      await createMutation.mutateAsync({
        program_id: programId,
        jira_url: jiraUrl,
        email,
        api_token: apiToken,
        project_key: projectKey,
      });
      toast.success("Jira integration created");
    } catch {
      toast.error("Failed to create Jira integration");
    }
  };

  const handleTest = async () => {
    if (!integration) return;
    try {
      const result = await testMutation.mutateAsync(integration.id);
      if (result.success) {
        toast.success(`Connected to ${result.project_name || integration.project_key}`);
      } else {
        toast.error(`Connection failed: ${result.message}`);
      }
    } catch {
      toast.error("Connection test failed");
    }
  };

  const handleSync = async (type: "wbs" | "activities" | "progress") => {
    if (!integration) return;
    try {
      const result = await syncMutation.mutateAsync({
        integrationId: integration.id,
        type,
      });
      toast.success(`Synced ${result.synced}/${result.total_items} items`);
    } catch {
      toast.error("Sync failed");
    }
  };

  const handleToggleSync = async () => {
    if (!integration) return;
    try {
      await updateMutation.mutateAsync({
        integrationId: integration.id,
        data: { sync_enabled: !integration.sync_enabled },
      });
      toast.success(integration.sync_enabled ? "Sync disabled" : "Sync enabled");
    } catch {
      toast.error("Failed to update sync setting");
    }
  };

  const handleDelete = async () => {
    if (!integration) return;
    if (!confirm("Delete this Jira integration? This cannot be undone.")) return;
    try {
      await deleteMutation.mutateAsync(integration.id);
      toast.success("Jira integration deleted");
    } catch {
      toast.error("Failed to delete integration");
    }
  };

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading Jira settings...</div>;
  }

  // Setup form (no integration)
  if (!hasIntegration) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="font-medium mb-4">Connect to Jira Cloud</h3>
        <div className="space-y-3 max-w-md">
          <div>
            <label htmlFor="jiraUrl" className="block text-sm font-medium text-gray-700 mb-1">Jira URL</label>
            <input
              id="jiraUrl"
              type="url"
              value={jiraUrl}
              onChange={(e) => setJiraUrl(e.target.value)}
              placeholder="https://your-org.atlassian.net"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="jiraEmail" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              id="jiraEmail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="jiraToken" className="block text-sm font-medium text-gray-700 mb-1">API Token</label>
            <input
              id="jiraToken"
              type="password"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="jiraProject" className="block text-sm font-medium text-gray-700 mb-1">Project Key</label>
            <input
              id="jiraProject"
              type="text"
              value={projectKey}
              onChange={(e) => setProjectKey(e.target.value)}
              placeholder="PROJ"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={createMutation.isPending}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {createMutation.isPending ? "Connecting..." : "Save Configuration"}
          </button>
        </div>
      </div>
    );
  }

  // Connected view
  return (
    <div className="space-y-4">
      {/* Status */}
      <div className="bg-white rounded-lg border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-medium">Jira Cloud Integration</h3>
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2 h-2 rounded-full ${integration.sync_enabled ? "bg-green-500" : "bg-gray-400"}`} />
            <span className="text-sm text-gray-600">
              {integration.sync_enabled ? "Sync Enabled" : "Sync Disabled"}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-500">Jira URL</div>
            <div className="text-sm font-medium">{integration.jira_url}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Project Key</div>
            <div className="text-sm font-medium">{integration.project_key}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Last Sync</div>
            <div className="text-sm">
              {integration.last_sync_at
                ? new Date(integration.last_sync_at).toLocaleString()
                : "Never"}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleTest}
            disabled={testMutation.isPending}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            {testMutation.isPending ? "Testing..." : "Test Connection"}
          </button>
          <button
            onClick={handleToggleSync}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
          >
            {integration.sync_enabled ? "Disable Sync" : "Enable Sync"}
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-1 text-sm text-red-600 border border-red-200 rounded hover:bg-red-50"
          >
            <Trash2 size={14} className="inline mr-1" />
            Remove
          </button>
        </div>
      </div>

      {/* Sync Actions */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="font-medium mb-4">Sync Operations</h3>
        <div className="flex gap-2">
          <button
            onClick={() => handleSync("wbs")}
            disabled={syncMutation.isPending}
            className="px-4 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            Sync WBS
          </button>
          <button
            onClick={() => handleSync("activities")}
            disabled={syncMutation.isPending}
            className="px-4 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            Sync Activities
          </button>
          <button
            onClick={() => handleSync("progress")}
            disabled={syncMutation.isPending}
            className="px-4 py-2 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
          >
            Sync Progress
          </button>
        </div>
      </div>

      {/* Mappings */}
      <JiraMappingsSection integrationId={integration.id} />

      {/* Sync Logs */}
      <JiraSyncLogsSection integrationId={integration.id} />
    </div>
  );
}

function JiraMappingsSection({ integrationId }: { integrationId: string }) {
  const { data: mappings, isLoading } = useJiraMappings(integrationId);

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Mappings</h3>
      {isLoading && <p className="text-sm text-gray-500">Loading mappings...</p>}
      {mappings && mappings.length === 0 && (
        <p className="text-sm text-gray-500">No mappings yet. Sync to create mappings automatically.</p>
      )}
      {mappings && mappings.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border p-2 text-left">Type</th>
              <th className="border p-2 text-left">Local ID</th>
              <th className="border p-2 text-left">Jira Key</th>
              <th className="border p-2 text-left">Last Synced</th>
            </tr>
          </thead>
          <tbody>
            {mappings.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <td className="border p-2">{m.entity_type}</td>
                <td className="border p-2 font-mono text-xs">{m.local_id}</td>
                <td className="border p-2">{m.jira_issue_key}</td>
                <td className="border p-2 text-xs">
                  {m.last_synced_at ? new Date(m.last_synced_at).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function JiraSyncLogsSection({ integrationId }: { integrationId: string }) {
  const { data: logs, isLoading } = useJiraSyncLogs(integrationId, 10);

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Sync History</h3>
      {isLoading && <p className="text-sm text-gray-500">Loading logs...</p>}
      {logs && logs.items.length === 0 && (
        <p className="text-sm text-gray-500">No sync history.</p>
      )}
      {logs && logs.items.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="border p-2 text-left">Date</th>
              <th className="border p-2 text-left">Type</th>
              <th className="border p-2 text-center">Status</th>
              <th className="border p-2 text-right">Synced</th>
              <th className="border p-2 text-right">Failed</th>
            </tr>
          </thead>
          <tbody>
            {logs.items.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="border p-2 text-xs">{new Date(log.started_at).toLocaleString()}</td>
                <td className="border p-2">{log.sync_type}</td>
                <td className="border p-2 text-center">
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    log.status === "SUCCESS" ? "bg-green-100 text-green-700" :
                    log.status === "FAILED" ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
                    {log.status}
                  </span>
                </td>
                <td className="border p-2 text-right">{log.items_synced}</td>
                <td className="border p-2 text-right">{log.items_failed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
