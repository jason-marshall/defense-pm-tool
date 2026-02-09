/**
 * Program settings tab with Jira integration, variance, management reserve, and skills.
 */

import { useState } from "react";
import { JiraSettings } from "@/components/Settings/JiraSettings";
import { VariancePanel } from "@/components/Settings/VariancePanel";
import { ManagementReservePanel } from "@/components/Settings/ManagementReservePanel";
import { SkillsPanel } from "@/components/Settings/SkillsPanel";

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
      {activeTab === "variance" && <VariancePanel programId={programId} />}
      {activeTab === "reserve" && <ManagementReservePanel programId={programId} />}
      {activeTab === "skills" && <SkillsPanel programId={programId} />}
    </div>
  );
}
