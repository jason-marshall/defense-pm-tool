/**
 * WBS Tree toolbar with expand/collapse and add controls.
 */

export interface WBSToolbarProps {
  onExpandAll: () => void;
  onCollapseAll: () => void;
  onAddRoot: () => void;
  hasElements: boolean;
}

export function WBSToolbar({
  onExpandAll,
  onCollapseAll,
  onAddRoot,
  hasElements,
}: WBSToolbarProps) {
  return (
    <div className="wbs-tree-toolbar">
      <button onClick={onAddRoot}>+ Add Root Element</button>
      <button onClick={onExpandAll} disabled={!hasElements}>
        Expand All
      </button>
      <button onClick={onCollapseAll} disabled={!hasElements}>
        Collapse All
      </button>
    </div>
  );
}
