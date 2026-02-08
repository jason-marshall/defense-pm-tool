import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
              <div className="min-h-screen bg-gray-50">
                <Routes>
                  <Route path="/login" element={<LoginPage />} />
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Navigation />
                        <main className="container mx-auto px-4 py-8">
                          <Routes>
                            <Route path="/" element={<Home />} />
                            <Route path="/programs" element={<ProgramsPlaceholder />} />
                            <Route path="/programs/:id" element={<ProgramDetailPlaceholder />} />
                          </Routes>
                        </main>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </div>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function Navigation() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-white shadow-xs border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link to="/" className="text-xl font-bold text-gray-900">
              Defense PM Tool
            </Link>
            <div className="hidden md:flex items-center gap-6">
              <Link
                to="/programs"
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                Programs
              </Link>
            </div>
          </div>
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
            <span className="text-sm text-gray-500">v1.2.0</span>
          </div>
        </div>
      </div>
    </nav>
  );
}

function Home() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Defense Program Management Tool
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          EVMS/DFARS Compliant Project Management
        </p>
        <div className="flex justify-center gap-4">
          <Link
            to="/programs"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            View Programs
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mt-12">
        <FeatureCard
          title="EVMS Compliance"
          description="Full ANSI/EIA-748 Earned Value Management System compliance with automated metrics."
        />
        <FeatureCard
          title="CPM Scheduling"
          description="Critical Path Method scheduling with all dependency types and constraint support."
        />
        <FeatureCard
          title="Monte Carlo Analysis"
          description="Schedule risk analysis with probabilistic duration modeling and S-curve projections."
        />
      </div>
    </div>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6 bg-white rounded-lg shadow-xs border hover:shadow-md transition-shadow">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

function ProgramsPlaceholder() {
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Programs</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          New Program
        </button>
      </div>
      <div className="bg-white rounded-lg shadow-xs border p-8 text-center">
        <p className="text-gray-600">Program list will be implemented here.</p>
      </div>
    </div>
  );
}

function ProgramDetailPlaceholder() {
  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Program Details</h1>
      <div className="bg-white rounded-lg shadow-xs border p-8 text-center">
        <p className="text-gray-600">
          Program details, activities, and Gantt chart will be implemented here.
        </p>
      </div>
    </div>
  );
}
