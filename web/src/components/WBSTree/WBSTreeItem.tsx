/**
 * Individual WBS tree node component.
 */

import { useCallback } from "react";
import type { WBSElementTree } from "@/types";

export interface WBSTreeItemProps {
  element: WBSElementTree;
  level: number;
  selectedId: string | null;
  expandedIds: Set<string>;
  onSelect: (element: WBSElementTree) => void;
  onToggle: (id: string) => void;
  onAddChild: (parent: WBSElementTree) => void;
  onEdit: (element: WBSElementTree) => void;
  onDelete: (element: WBSElementTree) => void;
}

export function WBSTreeItem({
  element,
  level,
  selectedId,
  expandedIds,
  onSelect,
  onToggle,
  onAddChild,
  onEdit,
  onDelete,
}: WBSTreeItemProps) {
  const hasChildren = element.children && element.children.length > 0;
  const isExpanded = expandedIds.has(element.id);
  const isSelected = selectedId === element.id;

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggle(element.id);
    },
    [element.id, onToggle]
  );

  const handleSelect = useCallback(() => {
    onSelect(element);
  }, [element, onSelect]);

  const handleAddChild = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onAddChild(element);
    },
    [element, onAddChild]
  );

  const handleEdit = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onEdit(element);
    },
    [element, onEdit]
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDelete(element);
    },
    [element, onDelete]
  );

  const formatBudget = (budget: string): string => {
    const num = parseFloat(budget);
    if (isNaN(num)) return budget;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  };

  return (
    <div className="wbs-tree-item">
      <div
        className={`wbs-tree-item-row ${isSelected ? "selected" : ""}`}
        onClick={handleSelect}
        style={{ paddingLeft: `${level * 8}px` }}
      >
        {/* Expand/Collapse Toggle */}
        <span
          className={`wbs-tree-toggle ${hasChildren ? "has-children" : ""}`}
          onClick={hasChildren ? handleToggle : undefined}
        >
          {hasChildren ? (isExpanded ? "▼" : "▶") : ""}
        </span>

        {/* Folder/File Icon */}
        <span className={`wbs-tree-icon ${hasChildren ? "folder" : "file"}`}>
          {hasChildren ? "📁" : "📄"}
        </span>

        {/* Content */}
        <div className="wbs-tree-content">
          <span className="wbs-tree-code">{element.code}</span>
          <span className="wbs-tree-name" title={element.name}>
            {element.name}
          </span>

          {/* Badges */}
          <div className="wbs-tree-badges">
            {(element as WBSElementTree & { isControlAccount?: boolean })
              .isControlAccount && (
              <span className="wbs-tree-badge control-account">CA</span>
            )}
            <span className="wbs-tree-badge level">L{element.level}</span>
          </div>

          {/* Budget */}
          {element.budgetedCost && parseFloat(element.budgetedCost) > 0 && (
            <span className="wbs-tree-budget">
              {formatBudget(element.budgetedCost)}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="wbs-tree-actions">
          <button onClick={handleAddChild} title="Add child element">
            +
          </button>
          <button onClick={handleEdit} title="Edit element">
            ✎
          </button>
          <button className="delete" onClick={handleDelete} title="Delete element">
            ×
          </button>
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="wbs-tree-children">
          {element.children.map((child) => (
            <WBSTreeItem
              key={child.id}
              element={child}
              level={level + 1}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggle={onToggle}
              onAddChild={onAddChild}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
