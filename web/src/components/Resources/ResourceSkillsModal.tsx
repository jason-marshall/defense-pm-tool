/**
 * Modal for managing resource skill assignments with proficiency and certification.
 */

import { useState } from "react";
import {
  useResourceSkills,
  useAddResourceSkill,
  useUpdateResourceSkill,
  useRemoveResourceSkill,
  useSkills,
} from "@/hooks/useSkills";
import { useToast } from "@/components/Toast";
import { Plus, Trash2, X } from "lucide-react";
import type { ResourceSkillResponse } from "@/types/skill";

interface ResourceSkillsModalProps {
  resourceId: string;
  resourceName: string;
  programId: string;
  onClose: () => void;
}

const PROFICIENCY_LABELS = ["", "Novice", "Beginner", "Intermediate", "Advanced", "Expert"];

export function ResourceSkillsModal({
  resourceId,
  resourceName,
  programId,
  onClose,
}: ResourceSkillsModalProps) {
  const { data: resourceSkills, isLoading } = useResourceSkills(resourceId);
  const { data: allSkills } = useSkills({ program_id: programId });
  const addMutation = useAddResourceSkill();
  const updateMutation = useUpdateResourceSkill();
  const removeMutation = useRemoveResourceSkill();
  const toast = useToast();

  const [selectedSkillId, setSelectedSkillId] = useState("");
  const [proficiency, setProficiency] = useState(1);
  const [isCertified, setIsCertified] = useState(false);

  const assignedSkillIds = new Set(resourceSkills?.map((rs) => rs.skill_id) ?? []);
  const availableSkills = allSkills?.items.filter((s) => !assignedSkillIds.has(s.id)) ?? [];

  const handleAdd = async () => {
    if (!selectedSkillId) return;
    try {
      await addMutation.mutateAsync({
        resourceId,
        data: {
          skill_id: selectedSkillId,
          proficiency_level: proficiency,
          is_certified: isCertified,
        },
      });
      toast.success("Skill added");
      setSelectedSkillId("");
      setProficiency(1);
      setIsCertified(false);
    } catch {
      toast.error("Failed to add skill");
    }
  };

  const handleUpdateProficiency = async (rs: ResourceSkillResponse, level: number) => {
    try {
      await updateMutation.mutateAsync({
        resourceId,
        skillId: rs.skill_id,
        data: { proficiency_level: level },
      });
    } catch {
      toast.error("Failed to update proficiency");
    }
  };

  const handleRemove = async (skillId: string) => {
    try {
      await removeMutation.mutateAsync({ resourceId, skillId });
      toast.success("Skill removed");
    } catch {
      toast.error("Failed to remove skill");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] overflow-auto">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-semibold">Skills - {resourceName}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Add Skill Form */}
          <div className="bg-gray-50 rounded p-3">
            <h3 className="text-sm font-medium mb-2">Assign Skill</h3>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <label htmlFor="rsSkill" className="block text-xs text-gray-500 mb-1">Skill</label>
                <select
                  id="rsSkill"
                  value={selectedSkillId}
                  onChange={(e) => setSelectedSkillId(e.target.value)}
                  className="w-full border rounded px-2 py-1 text-sm"
                >
                  <option value="">Select skill...</option>
                  {availableSkills.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="rsProficiency" className="block text-xs text-gray-500 mb-1">Level</label>
                <select
                  id="rsProficiency"
                  value={proficiency}
                  onChange={(e) => setProficiency(Number(e.target.value))}
                  className="border rounded px-2 py-1 text-sm"
                >
                  {[1, 2, 3, 4, 5].map((l) => (
                    <option key={l} value={l}>{l} - {PROFICIENCY_LABELS[l]}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-1">
                <input
                  id="rsCert"
                  type="checkbox"
                  checked={isCertified}
                  onChange={(e) => setIsCertified(e.target.checked)}
                />
                <label htmlFor="rsCert" className="text-xs">Certified</label>
              </div>
              <button
                onClick={handleAdd}
                disabled={!selectedSkillId || addMutation.isPending}
                className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                <Plus size={14} /> Add
              </button>
            </div>
          </div>

          {/* Current Skills */}
          {isLoading && <p className="text-sm text-gray-500">Loading skills...</p>}

          {resourceSkills && resourceSkills.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">No skills assigned.</p>
          )}

          {resourceSkills && resourceSkills.length > 0 && (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border p-2 text-left">Skill</th>
                  <th className="border p-2 text-center">Proficiency</th>
                  <th className="border p-2 text-center">Certified</th>
                  <th className="border p-2 text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {resourceSkills.map((rs) => (
                  <tr key={rs.id} className="hover:bg-gray-50">
                    <td className="border p-2">
                      {rs.skill?.name || rs.skill_id}
                      {rs.skill?.code && (
                        <span className="text-xs text-gray-400 ml-1">({rs.skill.code})</span>
                      )}
                    </td>
                    <td className="border p-2 text-center">
                      <select
                        value={rs.proficiency_level}
                        onChange={(e) => handleUpdateProficiency(rs, Number(e.target.value))}
                        className="border rounded px-1 py-0.5 text-xs"
                      >
                        {[1, 2, 3, 4, 5].map((l) => (
                          <option key={l} value={l}>{l} - {PROFICIENCY_LABELS[l]}</option>
                        ))}
                      </select>
                    </td>
                    <td className="border p-2 text-center">
                      {rs.is_certified ? (
                        <span className="text-green-600 text-xs font-medium">Certified</span>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="border p-2 text-center">
                      <button
                        onClick={() => handleRemove(rs.skill_id)}
                        className="text-red-500 hover:text-red-700"
                        title="Remove skill"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="p-4 border-t flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
