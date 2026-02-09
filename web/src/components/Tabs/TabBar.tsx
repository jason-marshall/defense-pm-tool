/**
 * Reusable tab bar component.
 */

import { NavLink } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

export interface TabItem {
  to: string;
  label: string;
  icon?: LucideIcon;
  end?: boolean;
}

interface TabBarProps {
  tabs: TabItem[];
}

export function TabBar({ tabs }: TabBarProps) {
  return (
    <div className="border-b border-gray-200 mb-6">
      <nav className="flex gap-0 -mb-px overflow-x-auto" role="tablist">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            role="tab"
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`
            }
          >
            {tab.icon && <tab.icon size={14} />}
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
