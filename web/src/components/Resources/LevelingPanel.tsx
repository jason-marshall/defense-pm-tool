/**
 * LevelingPanel component for running and previewing resource leveling.
 * Allows users to configure options, run the algorithm, and apply changes.
 */

import { useState } from "react";
import {
  useRunLeveling,
  useApplyLeveling,
  useRunParallelLeveling,
  useCompareLevelingAlgorithms,
} from "@/hooks/useLeveling";
import type {
  LevelingResult,
  LevelingOptions,
  LevelingComparisonResponse,
} from "@/types/leveling";
import { useToast } from "@/components/Toast";
import { Play, Check, AlertTriangle, RotateCcw, GitCompare } from "lucide-react";
import { format, parseISO } from "date-fns";

interface LevelingPanelProps {
  programId: string;
  onComplete?: () => void;
}

export function LevelingPanel({ programId, onComplete }: LevelingPanelProps) {
  const [options, setOptions] = useState<LevelingOptions>({
    preserve_critical_path: true,
    max_iterations: 100,
    target_resources: null,
    level_within_float: true,
  });
  const [algorithm, setAlgorithm] = useState<"serial" | "parallel">("serial");
  const [result, setResult] = useState<LevelingResult | null>(null);
  const [selectedShifts, setSelectedShifts] = useState<Set<string>>(new Set());
  const [comparison, setComparison] =
    useState<LevelingComparisonResponse | null>(null);

  const runLeveling = useRunLeveling();
  const runParallel = useRunParallelLeveling();
  const compareMutation = useCompareLevelingAlgorithms();
  const applyLeveling = useApplyLeveling();
  const { success, error: showError, warning } = useToast();

  const handleRun = async () => {
    try {
      const mutation =
        algorithm === "parallel" ? runParallel : runLeveling;
      const data = await mutation.mutateAsync({ programId, options });
      setResult(data);
      // Select all shifts by default
      setSelectedShifts(new Set(data.shifts.map((s) => s.activity_id)));
      if (data.success) {
        success(
          `Leveling complete (${algorithm}): ${data.activities_shifted} activities shifted`
        );
      } else {
        warning("Leveling completed with warnings");
      }
    } catch {
      showError("Failed to run leveling");
    }
  };

  const handleCompare = async () => {
    try {
      const data = await compareMutation.mutateAsync({ programId, options });
      setComparison(data);
      success("Algorithm comparison complete");
    } catch {
      showError("Failed to compare algorithms");
    }
  };

  const handleApply = async () => {
    if (selectedShifts.size === 0) {
      warning("No shifts selected to apply");
      return;
    }

    try {
      await applyLeveling.mutateAsync({
        programId,
        shiftIds: Array.from(selectedShifts),
      });
      success("Leveling changes applied successfully");
      setResult(null);
      onComplete?.();
    } catch {
      showError("Failed to apply leveling changes");
    }
  };

  const handleReset = () => {
    setResult(null);
    setSelectedShifts(new Set());
    setComparison(null);
  };

  const toggleShift = (activityId: string) => {
    const newSelected = new Set(selectedShifts);
    if (newSelected.has(activityId)) {
      newSelected.delete(activityId);
    } else {
      newSelected.add(activityId);
    }
    setSelectedShifts(newSelected);
  };

  const toggleAllShifts = (checked: boolean) => {
    if (checked && result) {
      setSelectedShifts(new Set(result.shifts.map((s) => s.activity_id)));
    } else {
      setSelectedShifts(new Set());
    }
  };

  return (
    <div className="leveling-panel bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Resource Leveling</h3>
        {result && (
          <button
            onClick={handleReset}
            className="text-gray-500 hover:text-gray-700 flex items-center gap-1 text-sm"
          >
            <RotateCcw size={14} />
            Reset
          </button>
        )}
      </div>

      {/* Options */}
      {!result && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="preserve_cp"
                checked={options.preserve_critical_path}
                onChange={(e) =>
                  setOptions({ ...options, preserve_critical_path: e.target.checked })
                }
                className="mr-2 h-4 w-4"
              />
              <label htmlFor="preserve_cp" className="text-sm">
                Preserve Critical Path
              </label>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="level_float"
                checked={options.level_within_float}
                onChange={(e) =>
                  setOptions({ ...options, level_within_float: e.target.checked })
                }
                className="mr-2 h-4 w-4"
              />
              <label htmlFor="level_float" className="text-sm">
                Level Within Float Only
              </label>
            </div>
            <div>
              <label className="text-sm text-gray-600">Max Iterations</label>
              <input
                type="number"
                value={options.max_iterations}
                onChange={(e) =>
                  setOptions({ ...options, max_iterations: Number(e.target.value) })
                }
                className="w-full border rounded px-3 py-2 mt-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="1000"
              />
            </div>
          </div>

          {/* Algorithm Toggle */}
          <div className="mb-4">
            <label className="text-sm text-gray-600 block mb-1">Algorithm</label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setAlgorithm("serial")}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  algorithm === "serial"
                    ? "bg-blue-100 text-blue-700 border border-blue-300"
                    : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                }`}
              >
                Serial
              </button>
              <button
                type="button"
                onClick={() => setAlgorithm("parallel")}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  algorithm === "parallel"
                    ? "bg-blue-100 text-blue-700 border border-blue-300"
                    : "bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200"
                }`}
              >
                Parallel
              </button>
            </div>
          </div>

          {/* Run & Compare Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleRun}
              disabled={runLeveling.isPending || runParallel.isPending}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              <Play size={16} />
              {runLeveling.isPending || runParallel.isPending
                ? "Running..."
                : `Run ${algorithm === "parallel" ? "Parallel" : "Serial"} Leveling`}
            </button>
            <button
              onClick={handleCompare}
              disabled={compareMutation.isPending}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              <GitCompare size={16} />
              {compareMutation.isPending ? "Comparing..." : "Compare"}
            </button>
          </div>

          <p className="text-xs text-gray-500 mt-2">
            Leveling will delay non-critical activities to resolve resource
            overallocations.
          </p>

          {/* Comparison Results */}
          {comparison && (
            <div className="mt-4 border rounded p-4 bg-gray-50">
              <h4 className="font-medium mb-3">Algorithm Comparison</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="font-medium text-gray-700 mb-1">Serial</div>
                  <div>Shifted: {comparison.serial.activities_shifted}</div>
                  <div>Extension: {comparison.serial.schedule_extension_days}d</div>
                  <div>Time: {comparison.serial.execution_time_ms}ms</div>
                  <div>Remaining: {comparison.serial.remaining_overallocations}</div>
                </div>
                <div>
                  <div className="font-medium text-gray-700 mb-1">Parallel</div>
                  <div>Shifted: {comparison.parallel.activities_shifted}</div>
                  <div>Extension: {comparison.parallel.schedule_extension_days}d</div>
                  <div>Time: {comparison.parallel.execution_time_ms}ms</div>
                  <div>Remaining: {comparison.parallel.remaining_overallocations}</div>
                </div>
              </div>
              <p className="mt-2 text-sm text-blue-600 font-medium">
                {comparison.recommendation}
              </p>
            </div>
          )}
        </>
      )}

      {/* Results */}
      {result && (
        <div className="border-t pt-4">
          <h4 className="font-medium mb-3">Leveling Results</h4>

          {/* Summary */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Activities Shifted</div>
              <div className="text-lg font-semibold">{result.activities_shifted}</div>
            </div>
            <div className="bg-gray-50 p-3 rounded">
              <div className="text-xs text-gray-500">Iterations Used</div>
              <div className="text-lg font-semibold">{result.iterations_used}</div>
            </div>
            <div
              className={`p-3 rounded ${
                result.schedule_extension_days > 0 ? "bg-orange-50" : "bg-gray-50"
              }`}
            >
              <div className="text-xs text-gray-500">Schedule Extension</div>
              <div
                className={`text-lg font-semibold ${
                  result.schedule_extension_days > 0 ? "text-orange-600" : ""
                }`}
              >
                {result.schedule_extension_days} days
              </div>
            </div>
            <div
              className={`p-3 rounded ${
                result.remaining_overallocations > 0 ? "bg-yellow-50" : "bg-green-50"
              }`}
            >
              <div className="text-xs text-gray-500">Remaining Issues</div>
              <div
                className={`text-lg font-semibold ${
                  result.remaining_overallocations > 0
                    ? "text-yellow-600"
                    : "text-green-600"
                }`}
              >
                {result.remaining_overallocations}
              </div>
            </div>
          </div>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <div className="flex items-center gap-2 text-yellow-700 font-medium mb-2">
                <AlertTriangle size={16} />
                Warnings
              </div>
              <ul className="text-sm text-yellow-600 list-disc list-inside">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Shifts Table */}
          {result.shifts.length > 0 ? (
            <>
              <div className="border rounded overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="p-2 text-left w-8">
                        <input
                          type="checkbox"
                          checked={selectedShifts.size === result.shifts.length}
                          onChange={(e) => toggleAllShifts(e.target.checked)}
                          className="h-4 w-4"
                        />
                      </th>
                      <th className="p-2 text-left">Activity</th>
                      <th className="p-2 text-left">Original Dates</th>
                      <th className="p-2 text-left">New Dates</th>
                      <th className="p-2 text-right">Delay</th>
                      <th className="p-2 text-left">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.shifts.map((shift) => (
                      <tr
                        key={shift.activity_id}
                        className="border-t hover:bg-gray-50"
                      >
                        <td className="p-2">
                          <input
                            type="checkbox"
                            checked={selectedShifts.has(shift.activity_id)}
                            onChange={() => toggleShift(shift.activity_id)}
                            className="h-4 w-4"
                          />
                        </td>
                        <td className="p-2 font-mono text-xs">
                          {shift.activity_code}
                        </td>
                        <td className="p-2 text-gray-500">
                          {format(parseISO(shift.original_start), "MM/dd")} -{" "}
                          {format(parseISO(shift.original_finish), "MM/dd")}
                        </td>
                        <td className="p-2">
                          {format(parseISO(shift.new_start), "MM/dd")} -{" "}
                          {format(parseISO(shift.new_finish), "MM/dd")}
                        </td>
                        <td className="p-2 text-right text-orange-600 font-medium">
                          +{shift.delay_days}d
                        </td>
                        <td className="p-2 text-xs text-gray-500 max-w-[150px] truncate">
                          {shift.reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-between items-center mt-4">
                <span className="text-sm text-gray-500">
                  {selectedShifts.size} of {result.shifts.length} shifts selected
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={handleReset}
                    className="px-4 py-2 border rounded hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleApply}
                    disabled={selectedShifts.size === 0 || applyLeveling.isPending}
                    className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
                  >
                    <Check size={16} />
                    {applyLeveling.isPending
                      ? "Applying..."
                      : `Apply ${selectedShifts.size} Change${selectedShifts.size !== 1 ? "s" : ""}`}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-6 bg-green-50 rounded">
              <Check size={32} className="mx-auto text-green-500 mb-2" />
              <p className="text-green-700 font-medium">No changes needed</p>
              <p className="text-sm text-green-600">
                Resources are already optimally allocated
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
