import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./components/Layout/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { ProgramsPage } from "./pages/ProgramsPage";
import { ProgramDetailPage } from "./pages/ProgramDetailPage";

// Lazy sub-tab components
import { ActivityList } from "./components/Activities/ActivityList";
import { DependencyList } from "./components/Dependencies/DependencyList";
import { ScheduleView } from "./components/Schedule/ScheduleView";
import { WBSTree } from "./components/WBSTree/WBSTree";
import { EVMSDashboard } from "./components/EVMSDashboard/EVMSDashboard";
import { ResourceTab } from "./components/Resources/ResourceTab";
import { ReportViewer } from "./components/Reports/ReportViewer";
import { ScenarioList } from "./components/Scenarios/ScenarioList";
import { BaselineList } from "./components/Baselines/BaselineList";
import { MonteCarloPanel } from "./components/MonteCarlo/MonteCarloPanel";
import { ProgramSettings } from "./components/Programs/ProgramSettings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Wrapper components that extract programId from the route
function ProgramActivityTab() {
  const id = useProgramId();
  return <ActivityList programId={id} />;
}

function ProgramDependencyTab() {
  const id = useProgramId();
  return <DependencyList programId={id} />;
}

function ProgramScheduleTab() {
  const id = useProgramId();
  return <ScheduleView programId={id} />;
}

function ProgramWBSTab() {
  const id = useProgramId();
  return <WBSTree programId={id} />;
}

function ProgramEVMSTab() {
  const id = useProgramId();
  return <EVMSDashboard programId={id} />;
}

function ProgramResourceTab() {
  const id = useProgramId();
  return <ResourceTab programId={id} />;
}

function ProgramReportTab() {
  const id = useProgramId();
  return <ReportViewer programId={id} />;
}

function ProgramScenarioTab() {
  const id = useProgramId();
  return <ScenarioList programId={id} />;
}

function ProgramBaselineTab() {
  const id = useProgramId();
  return <BaselineList programId={id} />;
}

function ProgramMonteCarloTab() {
  const id = useProgramId();
  return <MonteCarloPanel programId={id} />;
}

function ProgramSettingsTab() {
  const id = useProgramId();
  return <ProgramSettings programId={id} />;
}

import { useParams } from "react-router-dom";

function useProgramId(): string {
  const { id } = useParams<{ id: string }>();
  return id || "";
}

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<Home />} />
                  <Route path="/programs" element={<ProgramsPage />} />
                  <Route path="/programs/:id" element={<ProgramDetailPage />}>
                    <Route path="activities" element={<ProgramActivityTab />} />
                    <Route path="dependencies" element={<ProgramDependencyTab />} />
                    <Route path="schedule" element={<ProgramScheduleTab />} />
                    <Route path="wbs" element={<ProgramWBSTab />} />
                    <Route path="evms" element={<ProgramEVMSTab />} />
                    <Route path="resources" element={<ProgramResourceTab />} />
                    <Route path="reports" element={<ProgramReportTab />} />
                    <Route path="scenarios" element={<ProgramScenarioTab />} />
                    <Route path="baselines" element={<ProgramBaselineTab />} />
                    <Route path="monte-carlo" element={<ProgramMonteCarloTab />} />
                    <Route path="settings" element={<ProgramSettingsTab />} />
                  </Route>
                </Route>
              </Routes>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
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
