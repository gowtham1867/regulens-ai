import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlusCircle, ArrowLeft, Building2, FileText, CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

export const CreateApplication: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState("Extension of Approval (EoA) 2025-2026");
  const [category, setCategory] = useState("EXTENSION_OF_APPROVAL");
  const [academicYear, setAcademicYear] = useState("2025-2026");
  const [declaredIntake, setDeclaredIntake] = useState(300);
  const [declaredLandAcres, setDeclaredLandAcres] = useState(10.5);
  const [declaredBuiltUp, setDeclaredBuiltUp] = useState(8500);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const created = await api.createApplication({
        title,
        category,
        academic_year: academicYear,
        declared_intake: declaredIntake,
        declared_land_acres: declaredLandAcres,
        declared_built_up_sqm: declaredBuiltUp,
        notes,
      });
      navigate(`/applications/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create application draft");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-1.5 rounded-lg border border-[#DCE4ED] bg-white text-slate-600 hover:bg-slate-50 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Initiate New Institutional Application</h1>
          <p className="text-xs text-slate-500">
            Stage 1: Application Intake for AICTE Approval Cycle 2025–2026
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#DCE4ED] p-6 shadow-xs">
        <div className="p-4 bg-blue-50/60 rounded-xl border border-blue-200 mb-6 flex items-start gap-3">
          <Building2 className="w-5 h-5 text-[#1677C8] shrink-0 mt-0.5" />
          <div className="text-xs text-slate-700">
            <div className="font-bold text-slate-900">
              Applying Institution: {user?.institution_name || "Apex Institute of Technology"}
            </div>
            <p className="mt-0.5 text-slate-500">
              This application will be linked to your institutional master record. Required document placeholders will be auto-populated according to the AICTE Approval Process Handbook (APH).
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 font-semibold">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-bold text-slate-700 block mb-1">Application Title / Reference Name</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Approval Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              >
                <option value="EXTENSION_OF_APPROVAL">Extension of Approval (EoA)</option>
                <option value="NEW_INSTITUTION">Setting up New Technical Institution</option>
                <option value="INCREASE_IN_INTAKE">Increase in Intake / Additional Course</option>
                <option value="CHANGE_OF_SITE">Change of Site / Location</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Academic Year</label>
              <input
                type="text"
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                required
                className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Declared Total Intake</label>
              <input
                type="number"
                value={declaredIntake}
                onChange={(e) => setDeclaredIntake(parseInt(e.target.value, 10))}
                required
                className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Total Land (Acres)</label>
              <input
                type="number"
                step="0.1"
                value={declaredLandAcres}
                onChange={(e) => setDeclaredLandAcres(parseFloat(e.target.value))}
                required
                className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Built-Up Area (Sq.m)</label>
              <input
                type="number"
                value={declaredBuiltUp}
                onChange={(e) => setDeclaredBuiltUp(parseFloat(e.target.value))}
                required
                className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              />
            </div>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">Institutional Notes (Optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Provide any institutional context or campus development remarks..."
              className="w-full p-2.5 border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
            />
          </div>

          <div className="pt-4 border-t border-[#DCE4ED] flex justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-[#0B2545] hover:bg-[#123B63] text-white rounded-lg font-bold transition-colors cursor-pointer disabled:opacity-50"
            >
              {loading ? "Creating Draft..." : "Create Draft & Proceed to Documents"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

