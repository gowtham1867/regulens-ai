import sys

path = 'frontend/src/pages/ApplicationDetail.tsx'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Normalize CRLF to LF temporarily for matching
c_normalized = c.replace('\r\n', '\n')

# 1. State for modal
old_state = '''  // Export progress states
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);'''

new_state = '''  // Export progress states
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);

  // Authority Verification Modal states
  const [verifDoc, setVerifDoc] = useState<any>(null);
  const [verifVersion, setVerifVersion] = useState<any>(null);
  const [showVerifModal, setShowVerifModal] = useState(false);

  const handleOpenVerifyModal = (doc: any, v?: any) => {
    setVerifDoc(doc);
    const chosenV = v || (doc.versions && doc.versions.length > 0 ? doc.versions[doc.versions.length - 1] : null);
    setVerifVersion(chosenV);
    setShowVerifModal(true);
  };'''

assert old_state in c_normalized, 'old_state not found'
c_normalized = c_normalized.replace(old_state, new_state, 1)

# 2. handleVerifyIssuer
old_handler = '''  const handleVerifyIssuer = async (docId: number) => {
    setActionLoading(true);
    try {
      const res = await api.verifyDocument(docId, "STATE_FIRE_SERVICES_PORTAL", false);
      alert(`Issuer Verification Result: ${res.outcome}\\nReused: ${res.is_reused ? "Yes" : "No"}`);
      await loadAllData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };'''

new_handler = '''  const handleVerifyIssuer = async (docId: number) => {
    const doc = documents.find((d: any) => d.id === docId) || documents[0];
    if (doc) {
      handleOpenVerifyModal(doc);
    }
  };'''

assert old_handler in c_normalized, 'old_handler not found'
c_normalized = c_normalized.replace(old_handler, new_handler, 1)

# 3. Document row verify button
old_btn = '''                      {isOfficerOrAdmin && (
                        <button
                          onClick={() => handleVerifyIssuer(doc.id)}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-[#1677C8] text-white hover:bg-[#1264a8] flex items-center gap-1 cursor-pointer"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Verify Authority</span>
                        </button>
                      )}'''

new_btn = '''                      <button
                        onClick={() => handleOpenVerifyModal(doc, v)}
                        className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#0B2545] hover:bg-[#123B63] text-white flex items-center gap-1.5 cursor-pointer shadow-xs transition-colors"
                        title="Inspect issuing authority & run official verification"
                      >
                        <ShieldCheck className="w-3.5 h-3.5 text-[#16A6C8]" />
                        <span>Verify Authority</span>
                      </button>'''

assert old_btn in c_normalized, 'old_btn not found'
c_normalized = c_normalized.replace(old_btn, new_btn, 1)

# 4. Tab 4 verification section
old_tab4 = '''          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { code: "STATE_FIRE_SERVICES_PORTAL", title: "State Fire & Rescue Services", desc: "Fire Safety NOC verification adapter" },
              { code: "STATE_REVENUE_LAND_REGISTRY", title: "Revenue & Land Title Registry", desc: "Freehold ownership & encumbrance lookup" },
              { code: "AFFILIATING_UNIVERSITY_REGISTRY", title: "University Academic Portal", desc: "Course-wise sanctioned intake validation" },
            ].map((src) => (
              <div key={src.code} className="p-4 rounded-xl border border-[#DCE4ED] bg-slate-50 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                    <ShieldCheck className="w-4 h-4 text-[#1677C8]" />
                    <span>{src.title}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{src.desc}</p>
                </div>
                <button
                  onClick={() => handleVerifyIssuer(documents[0]?.id || 1)}
                  disabled={actionLoading}
                  className="mt-4 w-full py-1.5 text-xs font-bold rounded bg-[#0B2545] text-white hover:bg-[#123B63] transition-colors cursor-pointer"
                >
                  Test Authority Lookup
                </button>
              </div>
            ))}
          </div>'''

new_tab4 = '''          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { code: "STATE_FIRE_SERVICES_PORTAL", docType: "FIRE_SAFETY_CERTIFICATE", title: "State Fire & Rescue Services", desc: "Fire Safety NOC verification adapter" },
              { code: "STATE_REVENUE_LAND_REGISTRY", docType: "LAND_DOCUMENT", title: "Revenue & Land Title Registry", desc: "Freehold ownership & encumbrance lookup" },
              { code: "AFFILIATING_UNIVERSITY_REGISTRY", docType: "AFFILIATION_CERTIFICATE", title: "University Academic Portal", desc: "Course-wise sanctioned intake validation" },
            ].map((src) => {
              const matchedDoc = documents.find((d: any) => d.document_type === src.docType || d.title.toLowerCase().includes(src.docType.toLowerCase().split("_")[0])) || documents[0];
              return (
                <div key={src.code} className="p-4 rounded-xl border border-[#DCE4ED] bg-slate-50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                      <ShieldCheck className="w-4 h-4 text-[#1677C8]" />
                      <span>{src.title}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{src.desc}</p>
                    {matchedDoc && (
                      <div className="mt-2 text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-[#DCE4ED]">
                        <span className="font-semibold text-slate-500">Target Document: </span>
                        <span className="font-bold text-slate-800">{matchedDoc.title}</span>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => matchedDoc && handleOpenVerifyModal(matchedDoc)}
                    disabled={actionLoading || !matchedDoc}
                    className="mt-4 w-full py-1.5 text-xs font-bold rounded-lg bg-[#0B2545] text-white hover:bg-[#123B63] transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-[#16A6C8]" />
                    <span>Verify Authority</span>
                  </button>
                </div>
              );
            })}
          </div>'''

assert old_tab4 in c_normalized, 'old_tab4 not found'
c_normalized = c_normalized.replace(old_tab4, new_tab4, 1)

# 5. Modal rendering before close
old_modal_end = '''      {/* Document Interactive Preview Modal */}
      <DocumentPreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        document={previewDoc}
        version={previewVersion}
        applicationRef={app.reference_no}
      />'''

new_modal_end = '''      {/* Document Interactive Preview Modal */}
      <DocumentPreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        document={previewDoc}
        version={previewVersion}
        applicationRef={app.reference_no}
      />

      {/* Authority Verification Modal */}
      <AuthorityVerificationModal
        isOpen={showVerifModal}
        onClose={() => setShowVerifModal(false)}
        document={verifDoc}
        version={verifVersion}
        isOfficerOrAdmin={isOfficerOrAdmin}
        onVerificationComplete={loadAllData}
      />'''

assert old_modal_end in c_normalized, 'old_modal_end not found'
c_normalized = c_normalized.replace(old_modal_end, new_modal_end, 1)

# Write back preserving CRLF
with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c_normalized.replace('\n', '\r\n'))

print('ApplicationDetail.tsx updated successfully!')

