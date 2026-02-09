/**
 * Resource tab container with sub-tabs for Resources, Histogram, Leveling, Skills.
 */

import { useState } from "react";
import { ResourceList } from "./ResourceList";
import { LevelingPanel } from "./LevelingPanel";
import { SkillsPanel } from "@/components/Settings/SkillsPanel";

interface ResourceTabProps {
  programId: string;
}

type SubTab = "resources" | "histogram" | "leveling" | "skills";

export function ResourceTab({ programId }: ResourceTabProps) {
  const [activeTab, setActiveTab] = useState<SubTab>("resources");

  const tabs: { key: SubTab; label: string }[] = [
    { key: "resources", label: "Resources" },
    { key: "histogram", label: "Histogram" },
    { key: "leveling", label: "Leveling" },
    { key: "skills", label: "Skills" },
  ];

  return (
    <div>
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

      {activeTab === "resources" && <ResourceList programId={programId} />}
      {activeTab === "histogram" && (
        <div className="bg-white rounded-lg border p-6 text-center text-gray-500">
          <p>Select a resource from the Resources tab to view its histogram.</p>
          <p className="text-sm mt-2">Resource histograms show loading over time for individual resources.</p>
        </div>
      )}
      {activeTab === "leveling" && <LevelingPanel programId={programId} />}
      {activeTab === "skills" && <SkillsPanel programId={programId} />}
    </div>
  );
}
