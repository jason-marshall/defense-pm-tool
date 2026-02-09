/**
 * Management Reserve panel with status cards, initialize form,
 * record change form, and history table.
 */

import { useState } from "react";
import { useMRStatus, useMRHistory, useInitializeMR, useRecordMRChange } from "@/hooks/useMR";
import { useToast } from "@/components/Toast";

interface ManagementReservePanelProps {
  programId: string;
}

export function ManagementReservePanel({ programId }: ManagementReservePanelProps) {
  const { data: status, isLoading: statusLoading } = useMRStatus(programId);
  const { data: history, isLoading: historyLoading } = useMRHistory(programId);
  const initMutation = useInitializeMR();
  const changeMutation = useRecordMRChange();
  const toast = useToast();

  const [initAmount, setInitAmount] = useState("");
  const [initReason, setInitReason] = useState("");
  const [changeIn, setChangeIn] = useState("");
  const [changeOut, setChangeOut] = useState("");
  const [changeReason, setChangeReason] = useState("");

  const isInitialized = status && status.change_count > 0;

  const handleInitialize = async () => {
    if (!initAmount || Number(initAmount) <= 0) {
      toast.error("Initial amount must be greater than 0");
      return;
    }
    try {
      await initMutation.mutateAsync({
        programId,
        initialAmount: initAmount,
        reason: initReason || undefined,
      });
      toast.success("Management Reserve initialized");
      setInitAmount("");
      setInitReason("");
    } catch {
      toast.error("Failed to initialize Management Reserve");
    }
  };

  const handleRecordChange = async () => {
    const inVal = changeIn || "0";
    const outVal = changeOut || "0";
    if (inVal === "0" && outVal === "0") {
      toast.error("At least one of changes in or out must be non-zero");
      return;
    }
    try {
      await changeMutation.mutateAsync({
        programId,
        data: {
          changes_in: inVal,
          changes_out: outVal,
          reason: changeReason || undefined,
        },
      });
      toast.success("MR change recorded");
      setChangeIn("");
      setChangeOut("");
      setChangeReason("");
    } catch {
      toast.error("Failed to record MR change");
    }
  };

  if (statusLoading) {
    return <div className="p-4 text-gray-500">Loading Management Reserve...</div>;
  }

  const formatCurrency = (val: string) => {
    const num = Number(val);
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  return (
    <div className="space-y-6">
      {/* Status Cards */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="font-medium mb-4">Management Reserve (MR)</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-gray-50 rounded p-4 text-center">
            <div className="text-sm text-gray-500">Current Balance</div>
            <div className="text-xl font-bold text-green-600">
              {status ? formatCurrency(status.current_balance) : "$0"}
            </div>
          </div>
          <div className="bg-gray-50 rounded p-4 text-center">
            <div className="text-sm text-gray-500">Total In</div>
            <div className="text-xl font-bold">
              {status ? formatCurrency(status.total_changes_in) : "$0"}
            </div>
          </div>
          <div className="bg-gray-50 rounded p-4 text-center">
            <div className="text-sm text-gray-500">Total Out</div>
            <div className="text-xl font-bold">
              {status ? formatCurrency(status.total_changes_out) : "$0"}
            </div>
          </div>
        </div>
        {status?.last_change_at && (
          <p className="text-xs text-gray-400">
            Last change: {new Date(status.last_change_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Initialize Form (only shown when not initialized) */}
      {!isInitialized && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-medium mb-4">Initialize Management Reserve</h3>
          <div className="space-y-3 max-w-md">
            <div>
              <label htmlFor="mrInitAmount" className="block text-sm font-medium text-gray-700 mb-1">
                Initial Amount ($)
              </label>
              <input
                id="mrInitAmount"
                type="number"
                value={initAmount}
                onChange={(e) => setInitAmount(e.target.value)}
                min="1"
                step="1000"
                className="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="100000"
              />
            </div>
            <div>
              <label htmlFor="mrInitReason" className="block text-sm font-medium text-gray-700 mb-1">
                Reason
              </label>
              <input
                id="mrInitReason"
                type="text"
                value={initReason}
                onChange={(e) => setInitReason(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="Initial MR allocation"
              />
            </div>
            <button
              onClick={handleInitialize}
              disabled={initMutation.isPending}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {initMutation.isPending ? "Initializing..." : "Initialize MR"}
            </button>
          </div>
        </div>
      )}

      {/* Record Change Form (only shown when initialized) */}
      {isInitialized && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-medium mb-4">Record MR Change</h3>
          <div className="space-y-3 max-w-md">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="mrChangeIn" className="block text-sm font-medium text-gray-700 mb-1">
                  Add to MR ($)
                </label>
                <input
                  id="mrChangeIn"
                  type="number"
                  value={changeIn}
                  onChange={(e) => setChangeIn(e.target.value)}
                  min="0"
                  step="1000"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  placeholder="0"
                />
              </div>
              <div>
                <label htmlFor="mrChangeOut" className="block text-sm font-medium text-gray-700 mb-1">
                  Release from MR ($)
                </label>
                <input
                  id="mrChangeOut"
                  type="number"
                  value={changeOut}
                  onChange={(e) => setChangeOut(e.target.value)}
                  min="0"
                  step="1000"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  placeholder="0"
                />
              </div>
            </div>
            <div>
              <label htmlFor="mrChangeReason" className="block text-sm font-medium text-gray-700 mb-1">
                Reason
              </label>
              <input
                id="mrChangeReason"
                type="text"
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
                placeholder="Release to WP for design overrun"
              />
            </div>
            <button
              onClick={handleRecordChange}
              disabled={changeMutation.isPending}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {changeMutation.isPending ? "Recording..." : "Record Change"}
            </button>
          </div>
        </div>
      )}

      {/* History Table */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="font-medium mb-4">MR History</h3>
        {historyLoading && <p className="text-sm text-gray-500">Loading history...</p>}
        {history && history.items.length === 0 && (
          <p className="text-sm text-gray-500">No MR history records.</p>
        )}
        {history && history.items.length > 0 && (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Date</th>
                <th className="border p-2 text-right">Beginning</th>
                <th className="border p-2 text-right">In</th>
                <th className="border p-2 text-right">Out</th>
                <th className="border p-2 text-right">Ending</th>
                <th className="border p-2 text-left">Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.items.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="border p-2">{new Date(entry.created_at).toLocaleDateString()}</td>
                  <td className="border p-2 text-right">{formatCurrency(entry.beginning_mr)}</td>
                  <td className="border p-2 text-right text-green-600">
                    {Number(entry.changes_in) > 0 ? `+${formatCurrency(entry.changes_in)}` : "-"}
                  </td>
                  <td className="border p-2 text-right text-red-600">
                    {Number(entry.changes_out) > 0 ? `-${formatCurrency(entry.changes_out)}` : "-"}
                  </td>
                  <td className="border p-2 text-right font-medium">{formatCurrency(entry.ending_mr)}</td>
                  <td className="border p-2 text-gray-600">{entry.reason || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
