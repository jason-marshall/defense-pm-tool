/**
 * Modal form for creating and editing programs.
 */

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import type { Program, ProgramCreate, ProgramStatus } from "@/types/program";

interface ProgramFormModalProps {
  program?: Program | null;
  onSubmit: (data: ProgramCreate) => void;
  onClose: () => void;
  isSubmitting?: boolean;
}

const STATUS_OPTIONS: ProgramStatus[] = [
  "PLANNING",
  "ACTIVE",
  "ON_HOLD",
  "COMPLETED",
  "CANCELLED",
];

export function ProgramFormModal({
  program,
  onSubmit,
  onClose,
  isSubmitting,
}: ProgramFormModalProps) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<ProgramStatus>("PLANNING");
  const [plannedStartDate, setPlannedStartDate] = useState("");
  const [plannedEndDate, setPlannedEndDate] = useState("");
  const [budgetAtCompletion, setBudgetAtCompletion] = useState("");
  const [contractNumber, setContractNumber] = useState("");
  const [contractType, setContractType] = useState("");

  useEffect(() => {
    if (program) {
      setName(program.name);
      setCode(program.code);
      setDescription(program.description || "");
      setStatus(program.status);
      setPlannedStartDate(program.planned_start_date.split("T")[0]);
      setPlannedEndDate(program.planned_end_date.split("T")[0]);
      setBudgetAtCompletion(program.budget_at_completion || "");
      setContractNumber(program.contract_number || "");
      setContractType(program.contract_type || "");
    }
  }, [program]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      code,
      description: description || undefined,
      status,
      planned_start_date: plannedStartDate,
      planned_end_date: plannedEndDate,
      budget_at_completion: budgetAtCompletion || undefined,
      contract_number: contractNumber || undefined,
      contract_type: contractType || undefined,
    });
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">
            {program ? "Edit Program" : "Create Program"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Name *
              </label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="code" className="block text-sm font-medium text-gray-700 mb-1">
                Code *
              </label>
              <input
                id="code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              id="status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ProgramStatus)}
              className="w-full border rounded-md px-3 py-2 text-sm"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
                Start Date *
              </label>
              <input
                id="startDate"
                type="date"
                value={plannedStartDate}
                onChange={(e) => setPlannedStartDate(e.target.value)}
                required
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
                End Date *
              </label>
              <input
                id="endDate"
                type="date"
                value={plannedEndDate}
                onChange={(e) => setPlannedEndDate(e.target.value)}
                required
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label htmlFor="bac" className="block text-sm font-medium text-gray-700 mb-1">
              Budget at Completion ($)
            </label>
            <input
              id="bac"
              type="number"
              value={budgetAtCompletion}
              onChange={(e) => setBudgetAtCompletion(e.target.value)}
              step="0.01"
              min="0"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="contractNumber" className="block text-sm font-medium text-gray-700 mb-1">
                Contract Number
              </label>
              <input
                id="contractNumber"
                type="text"
                value={contractNumber}
                onChange={(e) => setContractNumber(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="contractType" className="block text-sm font-medium text-gray-700 mb-1">
                Contract Type
              </label>
              <input
                id="contractType"
                type="text"
                value={contractType}
                onChange={(e) => setContractType(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-700 border rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Saving..." : program ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
