/**
 * Program settings tab with Jira integration, variance, and management reserve.
 */

import { useState } from "react";

interface ProgramSettingsProps {
  programId: string;
}

type SettingsTab = "jira" | "variance" | "reserve" | "skills";

export function ProgramSettings({ programId }: ProgramSettingsProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("jira");

  const tabs: { key: SettingsTab; label: string }[] = [
    { key: "jira", label: "Jira Integration" },
    { key: "variance", label: "Variance (VRID)" },
    { key: "reserve", label: "Management Reserve" },
    { key: "skills", label: "Skills" },
  ];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Settings</h2>

      <div className="border-b border-gray-200 mb-4">
        <nav className="flex gap-0 -mb-px">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "jira" && <JiraSettings programId={programId} />}
      {activeTab === "variance" && <VarianceSettings programId={programId} />}
      {activeTab === "reserve" && <ManagementReserveSettings programId={programId} />}
      {activeTab === "skills" && <SkillsSettings programId={programId} />}
    </div>
  );
}

function JiraSettings({ programId: _programId }: { programId: string }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Jira Cloud Integration</h3>
      <div className="space-y-4 max-w-md">
        <div>
          <label htmlFor="jiraUrl" className="block text-sm font-medium text-gray-700 mb-1">Jira URL</label>
          <input id="jiraUrl" type="url" placeholder="https://your-org.atlassian.net" className="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label htmlFor="jiraProject" className="block text-sm font-medium text-gray-700 mb-1">Project Key</label>
          <input id="jiraProject" type="text" placeholder="PROJ" className="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label htmlFor="jiraToken" className="block text-sm font-medium text-gray-700 mb-1">API Token</label>
          <input id="jiraToken" type="password" placeholder="Token" className="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          Save Configuration
        </button>
      </div>
    </div>
  );
}

function VarianceSettings({ programId: _programId }: { programId: string }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Variance Explanations (VRID)</h3>
      <p className="text-sm text-gray-500">
        Variance reports and explanations are managed through the Reports tab
        (CPR Format 5). Use this section to configure variance thresholds.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4 max-w-md">
        <div>
          <label htmlFor="cvThreshold" className="block text-sm font-medium text-gray-700 mb-1">CV Threshold (%)</label>
          <input id="cvThreshold" type="number" defaultValue="10" className="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
        <div>
          <label htmlFor="svThreshold" className="block text-sm font-medium text-gray-700 mb-1">SV Threshold (%)</label>
          <input id="svThreshold" type="number" defaultValue="10" className="w-full border rounded-md px-3 py-2 text-sm" />
        </div>
      </div>
    </div>
  );
}

function ManagementReserveSettings({ programId: _programId }: { programId: string }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Management Reserve (MR)</h3>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded p-4 text-center">
          <div className="text-sm text-gray-500">Total MR</div>
          <div className="text-xl font-bold">$0</div>
        </div>
        <div className="bg-gray-50 rounded p-4 text-center">
          <div className="text-sm text-gray-500">Used</div>
          <div className="text-xl font-bold">$0</div>
        </div>
        <div className="bg-gray-50 rounded p-4 text-center">
          <div className="text-sm text-gray-500">Remaining</div>
          <div className="text-xl font-bold text-green-600">$0</div>
        </div>
      </div>
      <p className="text-sm text-gray-500">Configure management reserve allocation per GL 28.</p>
    </div>
  );
}

function SkillsSettings({ programId: _programId }: { programId: string }) {
  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="font-medium mb-4">Resource Skills & Certifications</h3>
      <p className="text-sm text-gray-500 mb-4">
        Manage skill definitions and map them to resources for capability tracking.
      </p>
      <div className="bg-gray-50 rounded p-8 text-center text-gray-400">
        Skills management is available through the Resources tab.
      </div>
    </div>
  );
}
