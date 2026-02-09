/**
 * Scenario list with simulate, compare, and promote actions.
 */

import { Play, ArrowUpCircle, Trash2 } from "lucide-react";
import { useScenarios, useSimulateScenario, usePromoteScenario, useDeleteScenario } from "@/hooks/useScenarios";
import { useToast } from "@/components/Toast";

interface ScenarioListProps {
  programId: string;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  simulated: "bg-blue-100 text-blue-700",
  promoted: "bg-green-100 text-green-700",
  archived: "bg-gray-100 text-gray-400",
};

export function ScenarioList({ programId }: ScenarioListProps) {
  const { data, isLoading, error } = useScenarios(programId);
  const simulateMutation = useSimulateScenario();
  const promoteMutation = usePromoteScenario();
  const deleteMutation = useDeleteScenario();
  const toast = useToast();

  if (isLoading) return <div className="p-4 text-gray-500">Loading scenarios...</div>;
  if (error) return <div className="p-4 text-red-500">Error loading scenarios</div>;

  const scenarios = data?.items ?? [];

  const handleSimulate = async (id: string) => {
    try {
      await simulateMutation.mutateAsync(id);
      toast.success("Simulation complete");
    } catch { toast.error("Simulation failed"); }
  };

  const handlePromote = async (id: string) => {
    if (!confirm("Promote this scenario to baseline?")) return;
    try {
      await promoteMutation.mutateAsync(id);
      toast.success("Scenario promoted to baseline");
    } catch { toast.error("Promotion failed"); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this scenario?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Scenario deleted");
    } catch { toast.error("Delete failed"); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Scenarios</h2>
      </div>

      {scenarios.length === 0 ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          No scenarios created yet.
        </div>
      ) : (
        <div className="space-y-3">
          {scenarios.map((scenario) => (
            <div key={scenario.id} className="bg-white rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{scenario.name}</h3>
                  {scenario.description && (
                    <p className="text-sm text-gray-500 mt-1">{scenario.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[scenario.status]}`}>
                      {scenario.status}
                    </span>
                    <span className="text-xs text-gray-400">
                      {scenario.changes.length} changes
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {scenario.status === "draft" && (
                    <button
                      onClick={() => handleSimulate(scenario.id)}
                      disabled={simulateMutation.isPending}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      title="Simulate"
                    >
                      <Play size={12} /> Simulate
                    </button>
                  )}
                  {scenario.status === "simulated" && (
                    <button
                      onClick={() => handlePromote(scenario.id)}
                      disabled={promoteMutation.isPending}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                      title="Promote"
                    >
                      <ArrowUpCircle size={12} /> Promote
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(scenario.id)}
                    className="text-red-500 hover:text-red-700"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              {scenario.simulation_results && (
                <div className="mt-3 grid grid-cols-4 gap-4 text-sm bg-gray-50 rounded p-3">
                  <div><span className="text-gray-500">P10:</span> {scenario.simulation_results.duration_p10}d</div>
                  <div><span className="text-gray-500">P50:</span> {scenario.simulation_results.duration_p50}d</div>
                  <div><span className="text-gray-500">P80:</span> {scenario.simulation_results.duration_p80}d</div>
                  <div><span className="text-gray-500">P90:</span> {scenario.simulation_results.duration_p90}d</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
