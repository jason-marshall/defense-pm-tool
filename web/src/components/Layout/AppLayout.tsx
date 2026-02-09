/**
 * Main application layout with sidebar and top nav bar.
 */

import { Outlet, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top Nav */}
      <header className="bg-white shadow-xs border-b h-14 flex items-center justify-between px-4 shrink-0">
        <Link to="/" className="text-lg font-bold text-gray-900">
          Defense PM Tool
        </Link>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-gray-600">{user.full_name}</span>
          )}
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Logout
          </button>
          <span className="text-xs text-gray-400">v1.3.0</span>
        </div>
      </header>

      {/* Main Area */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
