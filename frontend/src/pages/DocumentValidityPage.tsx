import React, { useState, useEffect } from "react";
import {
  CalendarClock,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Upload,
  HelpCircle,
  Search,
  ShieldCheck,
  Building,
  FileText
} from "lucide-react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";
import { WhyExplanationModal } from "../components/common/WhyExplanationModal";

export const DocumentValidityPage: React.FC = () => {
  const { user } = useAuth();
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Renewal Modal
  const [renewalModalOpen, setRenewalModalOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any>(null);
  const [newExpiryDate, setNewExpiryDate] = useState("");
  const [renewLoading, setRenewLoading] = useState(false);

  // Why Modal
  const [whyModalOpen, setWhyModalOpen] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const res = await api.get("/document-validity");
      setRecords(res.data);
    } catch (err) {
      console.error("Failed to load validity records:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const openRenewalModal = (rec: any) => {
    setSelectedRecord(rec);
    const d = new Date();
    d.setFullYear(d.getFullYear() + 1);
    setNewExpiryDate(d.toISOString().slice(0, 10));
    setRenewalModalOpen(true);
  };

  const handleRenew = async () => {
    if (!selectedRecord || !newExpiryDate) return;
    try {
      setRenewLoading(true);
      await api.post(`/document-validity/${selectedRecord.id}/renew`, {
        renewal_document_id: 1, // Simulated uploaded doc ID
        new_expiry_date: new Date(newExpiryDate).toISOString(),
      });
      setRenewalModalOpen(false);
      fetchRecords();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to renew document");
    } finally {
      setRenewLoading(false);
    }
  };

  const filtered = records.filter((r) => {
    if (search) {
      const q = search.toLowerCase();
      return (
        r.document_type.toLowerCase().includes(q) ||
        r.document_name.toLowerCase().includes(q) ||
        r.institution_name.toLowerCase().includes(q) ||
        r.issuing_authority.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#1677C8]/10 text-[#1677C8]">
              Phase 9 & 14
            </span>
            <span className="text-xs text-slate-500 font-medium">Continuous Statutory Compliance</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <CalendarClock className="w-6 h-6 text-[#1677C8]" />
            Document Expiry & Lease Monitoring Tracker
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Automated monitoring of 30-year land lease deeds, fire safety NOCs, building safety certificates, and statutory university affiliation orders.
          </p>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="text-xs font-bold text-slate-700">
            Tracked Statutory Documents ({filtered.length})
          </div>
          <div className="relative w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search document type, authority..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="py-3 px-4">Document Type</th>
                <th className="py-3 px-4">Institution</th>
                <th className="py-3 px-4">Issuing Authority</th>
                <th className="py-3 px-4">Expiry Date</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-medium">
                    Loading statutory document records...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No document records found.
                  </td>
                </tr>
              ) : (
                filtered.map((r) => {
                  const isExpiringSoon = r.status === "EXPIRING_SOON";
                  const isExpired = r.status === "EXPIRED";
                  return (
                    <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">{r.document_name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{r.document_type}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">{r.institution_name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-medium">{r.issuing_authority}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">
                          {new Date(r.expiry_date).toLocaleDateString()}
                        </div>
                        <div
                          className={`text-[10px] font-bold ${
                            isExpired
                              ? "text-rose-600"
                              : isExpiringSoon
                              ? "text-amber-600"
                              : "text-emerald-600"
                          }`}
                        >
                          {isExpired
                            ? `Expired ${Math.abs(r.days_remaining)}d ago`
                            : `${r.days_remaining}d remaining`}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {r.status === "VALID" && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                            Valid Active
                          </span>
                        )}
                        {r.status === "EXPIRING_SOON" && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300 animate-pulse">
                            Expiring Soon ({r.days_remaining}d)
                          </span>
                        )}
                        {r.status === "EXPIRED" && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                            Expired (Non-Compliant)
                          </span>
                        )}
                        {r.status === "RENEWAL_SUBMITTED" && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
                            Renewal Submitted
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => openRenewalModal(r)}
                            className="px-2.5 py-1 bg-[#1677C8] hover:bg-[#123B63] text-white text-[11px] font-bold rounded-lg transition-colors flex items-center gap-1"
                          >
                            <Upload className="w-3 h-3" />
                            Submit Renewal
                          </button>

                          <button
                            onClick={() => {
                              setSelectedRecordId(r.id);
                              setWhyModalOpen(true);
                            }}
                            className="px-2 py-1 rounded bg-[#1677C8]/10 text-[#1677C8] text-[11px] font-bold hover:bg-[#1677C8]/20"
                          >
                            Why?
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Renewal Modal */}
      {renewalModalOpen && selectedRecord && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Submit Renewed Certificate / NOC
            </h3>
            <p className="text-xs text-slate-600">
              Upload renewed statutory document for: {selectedRecord.document_name}. This will automatically satisfy the Promise Ledger obligation and update validity status.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">New Expiration Date:</label>
                <input
                  type="date"
                  value={newExpiryDate}
                  onChange={(e) => setNewExpiryDate(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Upload Certified PDF:</label>
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-4 text-center text-slate-500 cursor-pointer hover:border-[#1677C8]">
                  <Upload className="w-6 h-6 mx-auto mb-1 text-slate-400" />
                  <span className="text-[11px] font-semibold text-[#1677C8]">Click to select PDF certificate</span>
                  <p className="text-[10px] text-slate-400 mt-1">PDF up to 10MB (Digitally signed / QR code verified)</p>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setRenewalModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleRenew}
                disabled={renewLoading || !newExpiryDate}
                className="px-4 py-1.5 text-xs font-bold bg-[#1677C8] hover:bg-[#123B63] text-white rounded-lg disabled:opacity-50"
              >
                {renewLoading ? "Updating..." : "Submit & Update Validity"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Why Modal */}
      {selectedRecordId && (
        <WhyExplanationModal
          isOpen={whyModalOpen}
          onClose={() => setWhyModalOpen(false)}
          entityType="validity"
          entityId={selectedRecordId}
        />
      )}
    </div>
  );
};
