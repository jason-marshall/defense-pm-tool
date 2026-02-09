/**
 * MaterialConsumeForm modal for consuming material from an assignment.
 */

import { useState } from "react";
import { useConsumeMaterial } from "@/hooks/useMaterial";
import { useToast } from "@/components/Toast";

interface MaterialConsumeFormProps {
  assignmentId: string;
  resourceName: string;
  maxQuantity: number;
  onClose: () => void;
  onSuccess?: () => void;
}

export function MaterialConsumeForm({
  assignmentId,
  resourceName,
  maxQuantity,
  onClose,
  onSuccess,
}: MaterialConsumeFormProps) {
  const [quantity, setQuantity] = useState("");
  const consumeMutation = useConsumeMaterial();
  const { success, error: showError } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      showError("Quantity must be a positive number");
      return;
    }
    if (qty > maxQuantity) {
      showError(`Quantity cannot exceed remaining ${maxQuantity}`);
      return;
    }

    try {
      await consumeMutation.mutateAsync({ assignmentId, quantity: qty });
      success(`Consumed ${qty} units of ${resourceName}`);
      onSuccess?.();
      onClose();
    } catch {
      showError("Failed to consume material");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">
          Consume Material - {resourceName}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="quantity"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Quantity
            </label>
            <input
              id="quantity"
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="0.01"
              max={maxQuantity}
              step="0.01"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Remaining: {maxQuantity}
            </p>
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
              disabled={consumeMutation.isPending}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {consumeMutation.isPending ? "Consuming..." : "Consume"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
