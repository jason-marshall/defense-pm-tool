/**
 * Skills management panel with CRUD table and category filter.
 */

import { useState } from "react";
import { useSkills, useCreateSkill, useUpdateSkill, useDeleteSkill } from "@/hooks/useSkills";
import { useToast } from "@/components/Toast";
import { Plus, Edit2, Trash2 } from "lucide-react";
import type { SkillResponse } from "@/types/skill";

interface SkillsPanelProps {
  programId: string;
}

const CATEGORIES = ["Technical", "Management", "Certification", "Safety"];

export function SkillsPanel({ programId }: SkillsPanelProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SkillResponse | null>(null);

  const { data, isLoading } = useSkills({
    program_id: programId,
    category: categoryFilter || undefined,
  });
  const createMutation = useCreateSkill();
  const updateMutation = useUpdateSkill();
  const deleteMutation = useDeleteSkill();
  const toast = useToast();

  // Form state
  const [formName, setFormName] = useState("");
  const [formCode, setFormCode] = useState("");
  const [formCategory, setFormCategory] = useState("Technical");
  const [formDescription, setFormDescription] = useState("");
  const [formCertRequired, setFormCertRequired] = useState(false);

  const openCreateForm = () => {
    setEditing(null);
    setFormName("");
    setFormCode("");
    setFormCategory("Technical");
    setFormDescription("");
    setFormCertRequired(false);
    setShowForm(true);
  };

  const openEditForm = (skill: SkillResponse) => {
    setEditing(skill);
    setFormName(skill.name);
    setFormCode(skill.code);
    setFormCategory(skill.category);
    setFormDescription(skill.description || "");
    setFormCertRequired(skill.requires_certification);
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!formName || !formCode) {
      toast.error("Name and code are required");
      return;
    }
    try {
      if (editing) {
        await updateMutation.mutateAsync({
          id: editing.id,
          data: {
            name: formName,
            code: formCode.toUpperCase(),
            category: formCategory,
            description: formDescription || undefined,
            requires_certification: formCertRequired,
          },
        });
        toast.success("Skill updated");
      } else {
        await createMutation.mutateAsync({
          name: formName,
          code: formCode.toUpperCase(),
          category: formCategory,
          description: formDescription || undefined,
          requires_certification: formCertRequired,
          program_id: programId,
        });
        toast.success("Skill created");
      }
      setShowForm(false);
    } catch {
      toast.error("Failed to save skill");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this skill?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Skill deleted");
    } catch {
      toast.error("Failed to delete skill");
    }
  };

  if (isLoading) {
    return <div className="p-4 text-gray-500">Loading skills...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-medium">Resource Skills & Certifications</h3>
          <div className="flex gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="">All Categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <button
              onClick={openCreateForm}
              className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              <Plus size={14} /> Add Skill
            </button>
          </div>
        </div>

        {data && data.items.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">No skills defined.</p>
        )}

        {data && data.items.length > 0 && (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Code</th>
                <th className="border p-2 text-left">Name</th>
                <th className="border p-2 text-left">Category</th>
                <th className="border p-2 text-center">Certification</th>
                <th className="border p-2 text-center">Active</th>
                <th className="border p-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((skill) => (
                <tr key={skill.id} className="hover:bg-gray-50">
                  <td className="border p-2 font-mono">{skill.code}</td>
                  <td className="border p-2">{skill.name}</td>
                  <td className="border p-2">
                    <span className="inline-block px-2 py-0.5 rounded text-xs bg-gray-100">
                      {skill.category}
                    </span>
                  </td>
                  <td className="border p-2 text-center">
                    {skill.requires_certification ? "Required" : "-"}
                  </td>
                  <td className="border p-2 text-center">
                    <span className={skill.is_active ? "text-green-600" : "text-gray-400"}>
                      {skill.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="border p-2 text-center">
                    <button
                      onClick={() => openEditForm(skill)}
                      className="text-blue-500 hover:text-blue-700 mr-2"
                      title="Edit"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(skill.id)}
                      className="text-red-500 hover:text-red-700"
                      title="Delete"
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

      {showForm && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-medium mb-4">{editing ? "Edit Skill" : "New Skill"}</h3>
          <div className="space-y-3 max-w-lg">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="skillName" className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  id="skillName"
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label htmlFor="skillCode" className="block text-sm font-medium text-gray-700 mb-1">Code</label>
                <input
                  id="skillCode"
                  type="text"
                  value={formCode}
                  onChange={(e) => setFormCode(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm font-mono"
                  placeholder="SE-001"
                />
              </div>
            </div>
            <div>
              <label htmlFor="skillCategory" className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                id="skillCategory"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className="w-full border rounded-md px-3 py-2 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="skillDesc" className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                id="skillDesc"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
                className="w-full border rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="skillCert"
                type="checkbox"
                checked={formCertRequired}
                onChange={(e) => setFormCertRequired(e.target.checked)}
              />
              <label htmlFor="skillCert" className="text-sm text-gray-700">Requires Certification</label>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {editing ? "Update" : "Create"}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
