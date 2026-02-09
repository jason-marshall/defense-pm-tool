/**
 * CostEntryForm modal for recording cost entries on resource assignments.
 */

import { useState } from "react";
import { useRecordCostEntry } from "@/hooks/useCost";
import { useToast } from "@/components/Toast";

interface CostEntryFormProps {
  assignmentId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CostEntryForm({
  assignmentId,
  onClose,
  onSuccess,
}: CostEntryFormProps) {
  const [entryDate, setEntryDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [hoursWorked, setHoursWorked] = useState("0");
  const [quantityUsed, setQuantityUsed] = useState("");
  const [notes, setNotes] = useState("");

  const recordEntry = useRecordCostEntry();
  const { success, error: showError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const hours = parseFloat(hoursWorked);
    if (isNaN(hours) || hours < 0) {
      showError("Hours worked must be a non-negative number");
      return;
    }

    try {
      await recordEntry.mutateAsync({
        assignmentId,
        data: {
          entry_date: entryDate,
          hours_worked: hours,
          quantity_used: quantityUsed ? parseFloat(quantityUsed) : undefined,
          notes: notes || undefined,
        },
      });
      success("Cost entry recorded");
      onSuccess?.();
      onClose();
    } catch {
      showError("Failed to record cost entry");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Record Cost Entry</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="entry_date"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Date
            </label>
            <input
              id="entry_date"
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label
              htmlFor="hours_worked"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Hours Worked
            </label>
            <input
              id="hours_worked"
              type="number"
              value={hoursWorked}
              onChange={(e) => setHoursWorked(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="0"
              step="0.25"
              required
            />
          </div>

          <div>
            <label
              htmlFor="quantity_used"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Quantity Used (optional)
            </label>
            <input
              id="quantity_used"
              type="number"
              value={quantityUsed}
              onChange={(e) => setQuantityUsed(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="0"
              step="0.01"
            />
          </div>

          <div>
            <label
              htmlFor="notes"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Notes (optional)
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={recordEntry.isPending}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {recordEntry.isPending ? "Recording..." : "Record Entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
