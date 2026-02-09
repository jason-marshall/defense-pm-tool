/**
 * Program detail page with tabbed navigation for all sub-features.
 */

import { useParams, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  GitBranch,
  Calendar,
  FolderKanban,
  BarChart3,
  Users,
  FileText,
  FlaskConical,
  Bookmark,
  Zap,
  Settings,
} from "lucide-react";
import { useProgram } from "@/hooks/usePrograms";
import { TabBar } from "@/components/Tabs/TabBar";
import type { TabItem } from "@/components/Tabs/TabBar";

export function ProgramDetailPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { data: program, isLoading, error } = useProgram(id || "");

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading program...</div>;
  }

  if (error || !program) {
    return (
      <div className="p-4 text-red-500">
        {error instanceof Error ? error.message : "Program not found"}
      </div>
    );
  }

  const basePath = `/programs/${id}`;
  const tabs: TabItem[] = [
    { to: basePath, label: "Overview", icon: LayoutDashboard, end: true },
    { to: `${basePath}/activities`, label: "Activities", icon: Activity },
    { to: `${basePath}/dependencies`, label: "Dependencies", icon: GitBranch },
    { to: `${basePath}/schedule`, label: "Schedule", icon: Calendar },
    { to: `${basePath}/wbs`, label: "WBS", icon: FolderKanban },
    { to: `${basePath}/evms`, label: "EVMS", icon: BarChart3 },
    { to: `${basePath}/resources`, label: "Resources", icon: Users },
    { to: `${basePath}/reports`, label: "Reports", icon: FileText },
    { to: `${basePath}/scenarios`, label: "Scenarios", icon: FlaskConical },
    { to: `${basePath}/baselines`, label: "Baselines", icon: Bookmark },
    { to: `${basePath}/monte-carlo`, label: "Monte Carlo", icon: Zap },
    { to: `${basePath}/settings`, label: "Settings", icon: Settings },
  ];

  // Detect if we are at the root detail page (no sub-route)
  const isRootPath = location.pathname === basePath || location.pathname === `${basePath}/`;

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">{program.name}</h1>
        <p className="text-sm text-gray-500 font-mono">{program.code}</p>
      </div>

      <TabBar tabs={tabs} />

      {isRootPath ? (
        <ProgramOverviewInline program={program} />
      ) : (
        <Outlet context={{ program, programId: id }} />
      )}
    </div>
  );
}

// Inline overview to avoid circular imports
import { ProgramOverview } from "@/components/Programs/ProgramOverview";

function ProgramOverviewInline({ program }: { program: Parameters<typeof ProgramOverview>[0]["program"] }) {
  return <ProgramOverview program={program} />;
}
