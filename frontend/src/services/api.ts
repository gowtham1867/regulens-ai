const API_BASE = "/api/v1";

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem("regulens_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...options.headers,
  };

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    if (endpoint.includes("/auth/login")) {
      let failMsg = "Incorrect email or password";
      try {
        const errJson = await response.json();
        failMsg = errJson.detail || failMsg;
      } catch {}
      throw new Error(failMsg);
    }
    localStorage.removeItem("regulens_token");
    localStorage.removeItem("regulens_user");
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (response.status === 502 || response.status === 503 || response.status === 504) {
    throw new Error(
      "Backend scrutiny service is unreachable (HTTP 502 Bad Gateway). Please verify the FastAPI backend is running on http://127.0.0.1:8000."
    );
  }

  if (!response.ok) {
    let errorMsg = `API Error (${response.status})`;
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errorMsg;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Auth
  login: (data: { email: string; password: string }, portal?: string) => {
    const endpoint = portal ? `/auth/login?portal=${encodeURIComponent(portal)}` : "/auth/login";
    return apiRequest<any>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  register: (data: any) =>
    apiRequest<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMe: () => apiRequest<any>("/auth/me"),
  logout: () => apiRequest<any>("/auth/logout", { method: "POST" }),
  getPendingInstitutions: () => apiRequest<any[]>("/auth/institutions/pending"),
  verifyInstitution: (id: number, action: "APPROVED" | "REJECTED") =>
    apiRequest<any>(`/auth/institutions/${id}/verify?approval_status=${action}`, {
      method: "PATCH",
      body: JSON.stringify({ approval_status: action }),
    }),

  // Applications
  getApplications: (params?: { status?: string; category?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.category) query.append("category", params.category);
    if (params?.search) query.append("search", params.search);
    return apiRequest<any[]>(`/applications?${query.toString()}`);
  },
  getApplication: (id: number) => apiRequest<any>(`/applications/${id}`),
  createApplication: (data: any) =>
    apiRequest<any>("/applications", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  submitApplication: (id: number) =>
    apiRequest<any>(`/applications/${id}/submit`, { method: "POST" }),
  getDashboardSummary: () => apiRequest<any>("/dashboard/summary"),

  // Documents
  getDocuments: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/documents`),
  uploadDocument: (applicationId: number, formData: FormData) => {
    return fetch(`${API_BASE}/applications/${applicationId}/documents`, {
      method: "POST",
      headers: getAuthHeader(),
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail);
      }
      return res.json();
    });
  },
  correctField: (fieldId: number, data: { corrected_value: string; reason: string }) =>
    apiRequest<any>(`/extracted-fields/${fieldId}/correct`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getDownloadUrl: (versionId: number) => {
    const token = localStorage.getItem("regulens_token");
    return `${API_BASE}/document-versions/${versionId}/download${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  },
  downloadDocumentVersion: async (versionId: number, inline: boolean = false): Promise<{ blob: Blob; filename: string; contentType: string }> => {
    const token = localStorage.getItem("regulens_token");
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${API_BASE}/document-versions/${versionId}/download?inline=${inline}`, {
      method: "GET",
      headers,
    });
    if (!res.ok) {
      let errDetail = `Failed to retrieve document (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {}
      throw new Error(errDetail);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    let filename = `document_v${versionId}`;
    const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
    if (match && match[1]) filename = match[1].trim();
    const contentType = res.headers.get("Content-Type") || blob.type || "application/octet-stream";
    return { blob, filename, contentType };
  },

  // Validation
  runValidation: (applicationId: number) =>
    apiRequest<any>(`/applications/${applicationId}/validate`, { method: "POST" }),
  getFindings: (applicationId: number, includeHistoric: boolean = false) =>
    apiRequest<any[]>(`/applications/${applicationId}/findings?include_historic=${includeHistoric}`),
  getAnomalies: (applicationId: number) =>
    apiRequest<any>(`/applications/${applicationId}/anomalies`),

  // Verification
  getVerificationSources: () => apiRequest<any[]>("/verification-sources"),
  verifyDocument: (documentId: number, sourceCode?: string, forceRefresh: boolean = false) => {
    const q = new URLSearchParams();
    if (sourceCode) q.append("source_code", sourceCode);
    if (forceRefresh) q.append("force_refresh", "true");
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return apiRequest<any>(`/documents/${documentId}/verify${queryStr}`, {
      method: "POST",
    });
  },
  manualVerifyDocument: (
    documentId: number,
    data: { outcome: string; notes: string; issuing_authority?: string; certificate_number?: string }
  ) =>
    apiRequest<any>(`/documents/${documentId}/manual-verify`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getVerificationHistory: (documentId: number) =>
    apiRequest<any[]>(`/documents/${documentId}/verification-history`),

  // TrustGraph
  getTrustGraph: (applicationId: number) =>
    apiRequest<any>(`/applications/${applicationId}/trustgraph`),

  // Clarifications & Corrections
  getClarifications: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/clarifications`),
  createClarification: (applicationId: number, data: any) =>
    apiRequest<any>(`/applications/${applicationId}/clarifications`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  submitCorrection: (clarificationId: number, formData: FormData) => {
    return fetch(`${API_BASE}/clarifications/${clarificationId}/correction`, {
      method: "POST",
      headers: getAuthHeader(),
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Correction upload failed" }));
        throw new Error(err.detail);
      }
      return res.json();
    });
  },
  revalidateApplication: (applicationId: number) =>
    apiRequest<any>(`/applications/${applicationId}/revalidate`, { method: "POST" }),

  // Officer Reviews & Decisions
  addReviewNote: (applicationId: number, data: any) =>
    apiRequest<any>(`/applications/${applicationId}/reviews`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getReviews: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/reviews`),
  getDecisions: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/decisions`),
  recordDecision: (applicationId: number, data: any) =>
    apiRequest<any>(`/applications/${applicationId}/decisions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Reports & Exports
  exportCsvUrl: (applicationId: number, exportType: string = "findings") => {
    const token = localStorage.getItem("regulens_token");
    const q = new URLSearchParams();
    q.append("export_type", exportType);
    if (token) q.append("token", token);
    return `${API_BASE}/applications/${applicationId}/report.csv?${q.toString()}`;
  },
  exportPdfUrl: (applicationId: number) => {
    const token = localStorage.getItem("regulens_token");
    return `${API_BASE}/applications/${applicationId}/report.pdf${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  },
  exportPdf: async (applicationId: number): Promise<{ blob: Blob; filename: string }> => {
    const token = localStorage.getItem("regulens_token");
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${API_BASE}/applications/${applicationId}/report.pdf`, {
      method: "GET",
      headers,
    });
    if (!res.ok) {
      let errDetail = `Failed to generate PDF report (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {}
      throw new Error(errDetail);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    let filename = `ReguLens_Scrutiny_${applicationId}.pdf`;
    const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
    if (match && match[1]) filename = match[1].trim();
    return { blob, filename };
  },
  exportCsv: async (applicationId: number, exportType: string = "findings"): Promise<{ blob: Blob; filename: string }> => {
    const token = localStorage.getItem("regulens_token");
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const res = await fetch(`${API_BASE}/applications/${applicationId}/report.csv?export_type=${encodeURIComponent(exportType)}`, {
      method: "GET",
      headers,
    });
    if (!res.ok) {
      let errDetail = `Failed to generate CSV report (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {}
      throw new Error(errDetail);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    let filename = `ReguLens_${exportType}_${applicationId}.csv`;
    const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
    if (match && match[1]) filename = match[1].trim();
    return { blob, filename };
  },
  exportApplicationsQueueCsv: async (params?: { status?: string; category?: string; search?: string }): Promise<{ blob: Blob; filename: string }> => {
    const token = localStorage.getItem("regulens_token");
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.category) q.append("category", params.category);
    if (params?.search) q.append("search", params.search);
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    const res = await fetch(`${API_BASE}/applications/export.csv${queryStr}`, {
      method: "GET",
      headers,
    });
    if (!res.ok) {
      let errDetail = `Failed to export applications queue CSV (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errDetail = errJson.detail || errDetail;
      } catch {}
      throw new Error(errDetail);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    let filename = `regulens_applications_${new Date().toISOString().split("T")[0]}.csv`;
    const match = disposition.match(/filename=["']?([^"';]+)["']?/i);
    if (match && match[1]) filename = match[1].trim();
    return { blob, filename };
  },

  // Audit
  getAuditEvents: (params?: { action?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.action) q.append("action", params.action);
    if (params?.limit) q.append("limit", params.limit.toString());
    return apiRequest<any[]>(`/audit-events?${q.toString()}`);
  },
  checkAuditIntegrity: () => apiRequest<any>("/audit-integrity"),

  // Admin Rules
  getRules: () => apiRequest<any[]>("/admin/rules"),
  toggleRule: (ruleId: number) =>
    apiRequest<any>(`/admin/rules/${ruleId}/toggle`, { method: "PATCH" }),

  // Benchmark Evaluation
  runBenchmarkSuite: () =>
    apiRequest<any>("/admin/evaluation/run-suite", { method: "POST" }),

  // Notifications
  getNotifications: () => apiRequest<any[]>("/notifications"),
  markNotificationRead: (id: number) =>
    apiRequest<any>(`/notifications/${id}/read`, { method: "PATCH" }),
  markAllNotificationsRead: () =>
    apiRequest<any>("/notifications/mark-all-read", { method: "POST" }),

  // Regulatory Requirements & Checklists
  getRequirements: (applicationId: number) =>
    apiRequest<any>(`/applications/${applicationId}/requirements`),
  getDeficiencies: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/deficiencies`),
  resolveDeficiency: (applicationId: number, deficiencyId: number, data: { status: string; resolution_notes?: string }) =>
    apiRequest<any>(`/applications/${applicationId}/deficiencies/${deficiencyId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getDuplicates: (applicationId: number) =>
    apiRequest<any[]>(`/applications/${applicationId}/duplicates`),
  resolveDuplicate: (applicationId: number, duplicateId: number, data: { status: string; officer_resolution_notes?: string }) =>
    apiRequest<any>(`/applications/${applicationId}/duplicates/${duplicateId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};
