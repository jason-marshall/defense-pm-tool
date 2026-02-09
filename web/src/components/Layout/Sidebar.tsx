/**
 * Sidebar navigation component with program sub-links.
 */

import { NavLink, useParams } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  Activity,
  GitBranch,
  Calendar,
  BarChart3,
  Users,
  FileText,
  FlaskConical,
  Bookmark,
  Zap,
  Settings,
} from "lucide-react";

const mainNavItems = [
  { to: "/", icon: LayoutDashboard, label: "Home" },
  { to: "/programs", icon: FolderKanban, label: "Programs" },
];

const programSubNav = [
  { to: "", icon: LayoutDashboard, label: "Overview" },
  { to: "/activities", icon: Activity, label: "Activities" },
  { to: "/dependencies", icon: GitBranch, label: "Dependencies" },
  { to: "/schedule", icon: Calendar, label: "Schedule" },
  { to: "/wbs", icon: FolderKanban, label: "WBS" },
  { to: "/evms", icon: BarChart3, label: "EVMS" },
  { to: "/resources", icon: Users, label: "Resources" },
  { to: "/reports", icon: FileText, label: "Reports" },
  { to: "/scenarios", icon: FlaskConical, label: "Scenarios" },
  { to: "/baselines", icon: Bookmark, label: "Baselines" },
  { to: "/monte-carlo", icon: Zap, label: "Monte Carlo" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const { id: programId } = useParams<{ id: string }>();

  return (
    <aside className="w-56 bg-white border-r border-gray-200 min-h-screen flex flex-col">
      <nav className="flex-1 py-4">
        <div className="px-3 mb-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Navigation
          </h3>
          {mainNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`
              }
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </div>

        {programId && (
          <div className="px-3 border-t border-gray-100 pt-4">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Program
            </h3>
            {programSubNav.map((item) => (
              <NavLink
                key={item.to}
                to={`/programs/${programId}${item.to}`}
                end={item.to === ""}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`
                }
              >
                <item.icon size={14} />
                {item.label}
              </NavLink>
            ))}
          </div>
        )}
      </nav>
    </aside>
  );
}
