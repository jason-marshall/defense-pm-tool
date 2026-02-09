/**
 * Monte Carlo simulation panel with run form and results display.
 */

import { useState } from "react";
import { Zap } from "lucide-react";
import { useRunSimulation, useSimulationResults } from "@/hooks/useSimulations";
import { useToast } from "@/components/Toast";
import { DistributionHistogram } from "./DistributionHistogram";
import { TornadoChart } from "./TornadoChart";
import { SCurveChart } from "./SCurveChart";
import type { MonteCarloConfig, MonteCarloResult } from "@/types/simulation";

interface MonteCarloPanelProps {
  programId: string;
}

export function MonteCarloPanel({ programId }: MonteCarloPanelProps) {
  const [iterations, setIterations] = useState("1000");
  const [distribution, setDistribution] = useState<MonteCarloConfig["distribution_type"]>("pert");
  const { data: results, isLoading } = useSimulationResults(programId);
  const runMutation = useRunSimulation();
  const toast = useToast();

  const handleRun = async () => {
    try {
      await runMutation.mutateAsync({
        programId,
        config: {
          iterations: Number(iterations),
          distribution_type: distribution,
        },
      });
      toast.success("Simulation completed");
    } catch {
      toast.error("Simulation failed");
    }
  };

  const latestResult = results && results.length > 0 ? results[0] : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Zap size={20} /> Monte Carlo Simulation
        </h2>
      </div>

      {/* Run Form */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <h3 className="text-sm font-medium mb-3">Configuration</h3>
        <div className="flex items-end gap-4">
          <div>
            <label htmlFor="mcIter" className="block text-xs text-gray-500 mb-1">Iterations</label>
            <input
              id="mcIter"
              type="number"
              value={iterations}
              onChange={(e) => setIterations(e.target.value)}
              min="100"
              max="10000"
              step="100"
              className="border rounded px-3 py-2 text-sm w-32"
            />
          </div>
          <div>
            <label htmlFor="mcDist" className="block text-xs text-gray-500 mb-1">Distribution</label>
            <select
              id="mcDist"
              value={distribution}
              onChange={(e) => setDistribution(e.target.value as MonteCarloConfig["distribution_type"])}
              className="border rounded px-3 py-2 text-sm"
            >
              <option value="pert">PERT</option>
              <option value="triangular">Triangular</option>
              <option value="normal">Normal</option>
              <option value="uniform">Uniform</option>
            </select>
          </div>
          <button
            onClick={handleRun}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 text-sm disabled:opacity-50"
          >
            <Zap size={14} />
            {runMutation.isPending ? "Running..." : "Run Simulation"}
          </button>
        </div>
      </div>

      {/* Results */}
      {isLoading && <div className="p-4 text-gray-500">Loading results...</div>}

      {latestResult?.duration_results && (
        <ResultDisplay result={latestResult} />
      )}

      {!isLoading && !latestResult && (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
          No simulation results. Run a Monte Carlo simulation to see results.
        </div>
      )}
    </div>
  );
}

function ResultDisplay({ result }: { result: MonteCarloResult }) {
  const dr = result.duration_results;
  if (!dr) return null;

  const percentiles = [
    { label: "P10", value: dr.p10 },
    { label: "P25", value: dr.p25 },
    { label: "P50", value: dr.p50 },
    { label: "P75", value: dr.p75 },
    { label: "P80", value: dr.p80 },
    { label: "P90", value: dr.p90 },
    { label: "P95", value: dr.p95 },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">Mean Duration</div>
          <div className="text-2xl font-bold">{dr.mean.toFixed(1)} days</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">Std Deviation</div>
          <div className="text-2xl font-bold">{dr.std_dev.toFixed(1)} days</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">Min / Max</div>
          <div className="text-2xl font-bold">{dr.min} - {dr.max}</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-sm text-gray-500">P80 Duration</div>
          <div className="text-2xl font-bold text-purple-600">{dr.p80.toFixed(1)} days</div>
        </div>
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h3 className="text-sm font-medium mb-3">Percentile Distribution</h3>
        <div className="flex gap-4">
          {percentiles.map((p) => (
            <div key={p.label} className="text-center">
              <div className="text-xs text-gray-500">{p.label}</div>
              <div className="text-sm font-medium">{p.value.toFixed(1)}d</div>
            </div>
          ))}
        </div>
      </div>

      {result.sensitivity.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-medium mb-3">Sensitivity (Top Drivers)</h3>
          <div className="space-y-2">
            {result.sensitivity.slice(0, 10).map((item) => (
              <div key={item.activity_id} className="flex items-center gap-3">
                <span className="text-sm w-48 truncate">{item.activity_name}</span>
                <div className="flex-1 bg-gray-100 rounded h-4 overflow-hidden">
                  <div
                    className="bg-purple-500 h-full rounded"
                    style={{ width: `${Math.abs(item.correlation) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-12 text-right">
                  {(item.correlation * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {dr.histogram.length > 0 && (
        <DistributionHistogram
          histogram={dr.histogram}
          mean={dr.mean}
          p50={dr.p50}
          p80={dr.p80}
          p90={dr.p90}
        />
      )}

      {result.sensitivity.length > 0 && (
        <TornadoChart sensitivity={result.sensitivity} />
      )}

      {result.s_curve_data.length > 0 && (
        <SCurveChart data={result.s_curve_data} />
      )}
    </div>
  );
}
