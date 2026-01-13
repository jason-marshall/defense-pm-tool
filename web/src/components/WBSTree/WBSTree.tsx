/**
 * WBS Tree component for displaying and managing Work Breakdown Structure hierarchy.
 */

import { useState, useCallback, useMemo } from "react";
import type { WBSElementTree } from "@/types";
import {
  useWBSTree,
  useCreateWBSElement,
  useUpdateWBSElement,
  useDeleteWBSElement,
} from "@/hooks/useWBSTree";
import { WBSTreeItem } from "./WBSTreeItem";
import { WBSToolbar } from "./WBSToolbar";
import "./WBSTree.css";

export interface WBSTreeProps {
  programId: string;
  onSelect?: (element: WBSElementTree | null) => void;
}

interface FormData {
  wbsCode: string;
  name: string;
  description: string;
  budgetedCost: string;
  isControlAccount: boolean;
}

const initialFormData: FormData = {
  wbsCode: "",
  name: "",
  description: "",
  budgetedCost: "0",
  isControlAccount: false,
};

export function WBSTree({ programId, onSelect }: WBSTreeProps) {
  const { data: tree, isLoading, isError, error } = useWBSTree(programId);
  const createMutation = useCreateWBSElement();
  const updateMutation = useUpdateWBSElement(programId);
  const deleteMutation = useDeleteWBSElement(programId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [modalMode, setModalMode] = useState<"add" | "edit" | null>(null);
  const [parentElement, setParentElement] = useState<WBSElementTree | null>(null);
  const [editingElement, setEditingElement] = useState<WBSElementTree | null>(
    null
  );
  const [formData, setFormData] = useState<FormData>(initialFormData);

  // Collect all IDs for expand/collapse all
  const allIds = useMemo(() => {
    const ids: string[] = [];
    const collectIds = (elements: WBSElementTree[]) => {
      for (const el of elements) {
        ids.push(el.id);
        if (el.children) collectIds(el.children);
      }
    };
    if (tree) collectIds(tree);
    return ids;
  }, [tree]);

  const handleSelect = useCallback(
    (element: WBSElementTree) => {
      setSelectedId(element.id);
      onSelect?.(element);
    },
    [onSelect]
  );

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleExpandAll = useCallback(() => {
    setExpandedIds(new Set(allIds));
  }, [allIds]);

  const handleCollapseAll = useCallback(() => {
    setExpandedIds(new Set());
  }, []);

  const handleAddRoot = useCallback(() => {
    setParentElement(null);
    setFormData(initialFormData);
    setModalMode("add");
  }, []);

  const handleAddChild = useCallback((parent: WBSElementTree) => {
    setParentElement(parent);
    setFormData(initialFormData);
    setModalMode("add");
  }, []);

  const handleEdit = useCallback((element: WBSElementTree) => {
    setEditingElement(element);
    setFormData({
      wbsCode: element.code,
      name: element.name,
      description: element.description || "",
      budgetedCost: element.budgetedCost || "0",
      isControlAccount:
        (element as WBSElementTree & { isControlAccount?: boolean })
          .isControlAccount || false,
    });
    setModalMode("edit");
  }, []);

  const handleDelete = useCallback(
    (element: WBSElementTree) => {
      if (
        window.confirm(
          `Delete "${element.name}" and all its children? This action cannot be undone.`
        )
      ) {
        deleteMutation.mutate(element.id);
      }
    },
    [deleteMutation]
  );

  const handleCloseModal = useCallback(() => {
    setModalMode(null);
    setParentElement(null);
    setEditingElement(null);
    setFormData(initialFormData);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (modalMode === "add") {
        await createMutation.mutateAsync({
          programId,
          parentId: parentElement?.id || null,
          wbsCode: formData.wbsCode,
          name: formData.name,
          description: formData.description || null,
          budgetedCost: formData.budgetedCost,
          isControlAccount: formData.isControlAccount,
        });
      } else if (modalMode === "edit" && editingElement) {
        await updateMutation.mutateAsync({
          elementId: editingElement.id,
          data: {
            name: formData.name,
            description: formData.description || null,
            budgetedCost: formData.budgetedCost,
            isControlAccount: formData.isControlAccount,
          },
        });
      }

      handleCloseModal();
    },
    [
      modalMode,
      formData,
      programId,
      parentElement,
      editingElement,
      createMutation,
      updateMutation,
      handleCloseModal,
    ]
  );

  const handleFormChange = useCallback(
    (field: keyof FormData, value: string | boolean) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  if (isLoading) {
    return (
      <div className="wbs-tree">
        <div className="wbs-tree-loading">Loading WBS hierarchy...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="wbs-tree">
        <div className="wbs-tree-error">
          Error loading WBS: {(error as Error)?.message || "Unknown error"}
        </div>
      </div>
    );
  }

  return (
    <div className="wbs-tree">
      <WBSToolbar
        onExpandAll={handleExpandAll}
        onCollapseAll={handleCollapseAll}
        onAddRoot={handleAddRoot}
        hasElements={Boolean(tree && tree.length > 0)}
      />

      <div className="wbs-tree-container">
        {!tree || tree.length === 0 ? (
          <div className="wbs-tree-empty">
            No WBS elements. Click "Add Root Element" to create one.
          </div>
        ) : (
          tree.map((element) => (
            <WBSTreeItem
              key={element.id}
              element={element}
              level={0}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={handleSelect}
              onToggle={handleToggle}
              onAddChild={handleAddChild}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))
        )}
      </div>

      {/* Add/Edit Modal */}
      {modalMode && (
        <div className="wbs-modal-overlay" onClick={handleCloseModal}>
          <div className="wbs-modal" onClick={(e) => e.stopPropagation()}>
            <h3>
              {modalMode === "add"
                ? parentElement
                  ? `Add Child to "${parentElement.name}"`
                  : "Add Root Element"
                : `Edit "${editingElement?.name}"`}
            </h3>

            <form className="wbs-modal-form" onSubmit={handleSubmit}>
              {modalMode === "add" && (
                <div className="wbs-modal-field">
                  <label htmlFor="wbsCode">WBS Code *</label>
                  <input
                    id="wbsCode"
                    type="text"
                    value={formData.wbsCode}
                    onChange={(e) => handleFormChange("wbsCode", e.target.value)}
                    placeholder="e.g., 1.1"
                    required
                  />
                </div>
              )}

              <div className="wbs-modal-field">
                <label htmlFor="name">Name *</label>
                <input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleFormChange("name", e.target.value)}
                  placeholder="Element name"
                  required
                />
              </div>

              <div className="wbs-modal-field">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleFormChange("description", e.target.value)}
                  placeholder="Optional description"
                  rows={3}
                />
              </div>

              <div className="wbs-modal-field">
                <label htmlFor="budgetedCost">Budgeted Cost ($)</label>
                <input
                  id="budgetedCost"
                  type="number"
                  value={formData.budgetedCost}
                  onChange={(e) => handleFormChange("budgetedCost", e.target.value)}
                  step="0.01"
                  min="0"
                />
              </div>

              <div className="wbs-modal-field checkbox">
                <input
                  id="isControlAccount"
                  type="checkbox"
                  checked={formData.isControlAccount}
                  onChange={(e) =>
                    handleFormChange("isControlAccount", e.target.checked)
                  }
                />
                <label htmlFor="isControlAccount">Control Account</label>
              </div>

              <div className="wbs-modal-actions">
                <button
                  type="button"
                  className="cancel"
                  onClick={handleCloseModal}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="submit"
                  disabled={
                    createMutation.isPending || updateMutation.isPending
                  }
                >
                  {createMutation.isPending || updateMutation.isPending
                    ? "Saving..."
                    : modalMode === "add"
                    ? "Add Element"
                    : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
