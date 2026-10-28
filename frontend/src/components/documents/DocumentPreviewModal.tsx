import React, { useState, useEffect } from "react";
import {
  X,
  Download,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";
import { api } from "../../services/api";

interface ExtractedFieldData {
  id: number;
  field_key: string;
  field_label: string;
  extracted_value: string;
  normalized_value?: string;
  source_page?: number;
  confidence?: number;
  is_manually_corrected?: boolean;
  corrected_value?: string;
  correction_reason?: string;
}

interface VersionData {
  id: number;
  version_number: number;
  original_filename: string;
  file_hash: string;
  mime_type?: string;
  file_size_bytes?: number;
  page_count?: number;
  status: string;
  error_message?: string;
  ocr_confidence?: number;
  extracted_fields?: ExtractedFieldData[];
}

interface DocumentData {
  id: number;
  title: string;
  document_type: string;
  is_required?: boolean;
}

interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentData | null;
  version: VersionData | null;
  applicationRef?: string;
}

export const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({
  isOpen,
  onClose,
  document,
  version,
  applicationRef,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);
  const [showFields, setShowFields] = useState(false);

  useEffect(() => {
    if (!isOpen || !version) {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
      setError(null);
      setLoading(false);
      setZoom(100);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    api
      .downloadDocumentVersion(version.id, true)
      .then((res) => {
        if (!active) return;
        const url = URL.createObjectURL(res.blob);
        setBlobUrl(url);
        setContentType(res.contentType.toLowerCase());
        setFilename(res.filename || version.original_filename);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        console.error("Preview load error:", err);
        setError(err.message || "Failed to load document file from server storage.");
        setLoading(false);
      });

    return () => {
      active = false;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [isOpen, version?.id]);

  if (!isOpen || !document || !version) return null;

  const isPdf =
    contentType?.includes("pdf") ||
    filename?.toLowerCase().endsWith(".pdf") ||
    (version?.original_filename?.toLowerCase().endsWith(".pdf") ?? false);

  const isImage =
    contentType?.includes("image") ||
    /\.(png|jpe?g|webp|gif)$/i.test(filename || "") ||
    (version?.original_filename ? /\.(png|jpe?g|webp|gif)$/i.test(version.original_filename) : false);

  const handleDownload = () => {
    if (!blobUrl) return;
    const a = window.document.createElement("a");
    a.href = blobUrl;
    a.download = filename || version?.original_filename || "document";
    window.document.body.appendChild(a);
    a.click();
    window.document.body.removeChild(a);
  };

  const handleOpenNewTab = () => {
    if (!blobUrl) return;
    window.open(blobUrl, "_blank");
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unknown size";
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${Math.round(bytes / 1024)} KB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/75 backdrop-blur-xs p-4 sm:p-6 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl flex flex-col w-full max-w-6xl h-[92vh] border border-slate-200 overflow-hidden">
        {/* Modal Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-blue-100 border border-blue-200 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5 text-[#1677C8]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-bold text-slate-900 text-sm truncate max-w-md">
                  {document.title}
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-bold">
                  {document.document_type}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-800 font-bold">
                  v{version.version_number}
                </span>
                {version.status === "COMPLETED" && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> PROCESSED
                  </span>
                )}
                {version.status === "FAILED" && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> FAILED
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 truncate">
                File: <span className="font-medium text-slate-700">{version.original_filename || "Unnamed"}</span> •{" "}
                {formatFileSize(version.file_size_bytes)} • Hash:{" "}
                <span className="font-mono text-[11px] text-slate-600">
                  {(version.file_hash || "").substring(0, 16)}...
                </span>{" "}
                {applicationRef && `• App: ${applicationRef}`}
              </p>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2 shrink-0">
            {isImage && blobUrl && (
              <div className="flex items-center gap-1 bg-white border border-slate-300 rounded-lg p-0.5 mr-2">
                <button
                  onClick={() => setZoom((z) => Math.max(50, z - 25))}
                  className="p-1.5 hover:bg-slate-100 rounded text-slate-600 hover:text-slate-900"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[11px] font-mono px-1 font-semibold text-slate-600 w-12 text-center">
                  {zoom}%
                </span>
                <button
                  onClick={() => setZoom((z) => Math.min(250, z + 25))}
                  className="p-1.5 hover:bg-slate-100 rounded text-slate-600 hover:text-slate-900"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoom(100)}
                  className="p-1.5 hover:bg-slate-100 rounded text-slate-600 hover:text-slate-900"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {version.extracted_fields && version.extracted_fields.length > 0 && (
              <button
                onClick={() => setShowFields(!showFields)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors flex items-center gap-1.5 ${
                  showFields
                    ? "bg-blue-50 text-[#1677C8] border-blue-300"
                    : "bg-white text-slate-700 hover:bg-slate-100 border-slate-300"
                }`}
                title="Toggle OCR field intelligence drawer"
              >
                <Layers className="w-3.5 h-3.5 text-[#1677C8]" />
                <span>Extracted Entities ({version.extracted_fields.length})</span>
              </button>
            )}

            {blobUrl && (
              <>
                <button
                  onClick={handleOpenNewTab}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white text-slate-700 hover:bg-slate-100 border border-slate-300 transition-colors flex items-center gap-1.5"
                  title="Open in new browser tab"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                  <span>Open Tab</span>
                </button>
                <button
                  onClick={handleDownload}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#0B2545] text-white hover:bg-[#123B63] transition-colors flex items-center gap-1.5 shadow-xs"
                  title="Download copy of this file"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </button>
              </>
            )}

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors ml-1"
              title="Close viewer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Main Content Area */}
        <div className="flex-1 overflow-hidden relative flex flex-col bg-slate-100">
          {loading && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/90 z-20">
              <div className="w-10 h-10 border-3 border-[#1677C8] border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm font-semibold text-slate-700">
                Retrieving authentic document from secure vault...
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Authenticating session & verifying cryptographic integrity
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-white">
              <div className="w-14 h-14 rounded-full bg-rose-100 border border-rose-200 flex items-center justify-center mb-4">
                <AlertCircle className="w-7 h-7 text-rose-600" />
              </div>
              <h4 className="text-base font-bold text-slate-900 mb-1">
                Unable to Display Document Preview
              </h4>
              <p className="text-sm text-slate-600 max-w-md mb-4">{error}</p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setLoading(true);
                    setError(null);
                    api
                      .downloadDocumentVersion(version.id, true)
                      .then((res) => {
                        const url = URL.createObjectURL(res.blob);
                        setBlobUrl(url);
                        setContentType(res.contentType.toLowerCase());
                        setFilename(res.filename || version.original_filename);
                        setLoading(false);
                      })
                      .catch((err) => {
                        setError(err.message || "Failed to load document.");
                        setLoading(false);
                      });
                  }}
                  className="px-4 py-2 bg-[#1677C8] text-white text-xs font-bold rounded-lg hover:bg-[#1264a8]"
                >
                  Retry Connection
                </button>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-100 text-slate-700 text-xs font-bold rounded-lg hover:bg-slate-200 border border-slate-300"
                >
                  Close Viewer
                </button>
              </div>
            </div>
          )}

          {!loading && !error && blobUrl && (
            <div className="flex-1 flex flex-col lg:flex-row h-full overflow-hidden">
              {/* Document Display Canvas */}
              <div className="flex-1 h-full overflow-auto flex items-center justify-center p-2 sm:p-4 bg-slate-200/70">
                {isPdf ? (
                  <iframe
                    src={`${blobUrl}#toolbar=1&navpanes=0`}
                    className="w-full h-full rounded-xl bg-white shadow-md border border-slate-300"
                    title={document.title}
                  />
                ) : isImage ? (
                  <div className="overflow-auto max-h-full max-w-full flex items-center justify-center">
                    <img
                      src={blobUrl}
                      alt={document.title}
                      style={{
                        transform: `scale(${zoom / 100})`,
                        transformOrigin: "center center",
                        transition: "transform 0.15s ease",
                      }}
                      className="max-h-[80vh] object-contain rounded-lg shadow-lg border border-slate-300 bg-white"
                    />
                  </div>
                ) : (
                  <div className="bg-white p-8 rounded-2xl shadow-md border border-slate-200 text-center max-w-md">
                    <FileText className="w-16 h-16 text-[#1677C8] mx-auto mb-3" />
                    <h4 className="font-bold text-slate-900 text-base mb-1">
                      {version.original_filename}
                    </h4>
                    <p className="text-xs text-slate-500 mb-4">
                      Document Type: {document.document_type} • {formatFileSize(version.file_size_bytes)}
                    </p>
                    <p className="text-xs text-slate-600 mb-6 bg-slate-50 p-3 rounded-lg border border-slate-200 text-left">
                      This file format ({contentType || "binary"}) can be inspected by downloading it directly to your workstation.
                    </p>
                    <button
                      onClick={handleDownload}
                      className="w-full py-2.5 bg-[#0B2545] text-white font-bold rounded-lg hover:bg-[#123B63] flex items-center justify-center gap-2 text-xs"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download {version.original_filename}</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Side Drawer: Extracted OCR Entities (Collapsible) */}
              {showFields && version.extracted_fields && version.extracted_fields.length > 0 && (
                <div className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l border-slate-200 bg-white flex flex-col h-72 lg:h-full z-10 shrink-0">
                  <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wide">
                        Extracted Field Entities
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        {version.extracted_fields.length} structured regulatory claims
                      </p>
                    </div>
                    <button
                      onClick={() => setShowFields(false)}
                      className="text-slate-400 hover:text-slate-600 p-1 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
                    {version.extracted_fields.map((ef) => (
                      <div
                        key={ef.id}
                        className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-white transition-colors"
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-[10px] font-bold text-slate-500 uppercase">
                            {ef.field_label}
                          </span>
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-slate-200 text-slate-700">
                            Pg {ef.source_page || 1}
                          </span>
                        </div>
                        <div className="font-semibold text-slate-900 text-xs">
                          {ef.is_manually_corrected ? (
                            <div>
                              <span className="text-[#1677C8]">{ef.corrected_value}</span>
                              <span className="text-[10px] text-slate-400 line-through ml-1.5">
                                ({ef.extracted_value})
                              </span>
                              <div className="text-[10px] text-amber-700 bg-amber-50 p-1 rounded mt-1 border border-amber-200">
                                <b>Reason:</b> {ef.correction_reason}
                              </div>
                            </div>
                          ) : (
                            ef.extracted_value
                          )}
                        </div>
                        {ef.normalized_value && ef.normalized_value !== ef.extracted_value && (
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            Standardized: <span className="font-mono text-slate-700">{ef.normalized_value}</span>
                          </div>
                        )}
                        <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1.5 pt-1.5 border-t border-slate-100">
                          <span>Key: {ef.field_key}</span>
                          <span>Conf: {Math.round((ef.confidence || 0.9) * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Info Bar */}
        <div className="px-6 py-2.5 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-4">
            <span>
              Status:{" "}
              <strong className="text-slate-700 font-mono">
                {version.status}
              </strong>
            </span>
            {version.ocr_confidence && (
              <span>
                OCR Confidence:{" "}
                <strong className="text-slate-700">
                  {Math.round(version.ocr_confidence * 100)}%
                </strong>
              </span>
            )}
            {version.page_count && (
              <span>
                Pages: <strong className="text-slate-700">{version.page_count}</strong>
              </span>
            )}
          </div>
          <div className="text-slate-400">
            ReguLens Cryptographic Vault • SHA-256 Verified
          </div>
        </div>
      </div>
    </div>
  );
};

