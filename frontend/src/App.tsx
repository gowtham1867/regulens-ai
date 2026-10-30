import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { Layout } from "./components/layout/Layout";
import { Login } from "./pages/Login";
import { InstitutionLogin } from "./pages/InstitutionLogin";
import { OfficerLogin } from "./pages/OfficerLogin";
import { InstitutionRegister } from "./pages/InstitutionRegister";
import { RegistrationConfirmation } from "./pages/RegistrationConfirmation";
import { Dashboard } from "./pages/Dashboard";
import { ApplicationsList } from "./pages/ApplicationsList";
import { ApplicationDetail } from "./pages/ApplicationDetail";
import { CreateApplication } from "./pages/CreateApplication";
import { TrustGraphExplorer } from "./pages/TrustGraphExplorer";
import { VerificationPage } from "./pages/VerificationPage";
import { RulesPage } from "./pages/RulesPage";
import { ClarificationsPage } from "./pages/ClarificationsPage";
import { AuditTrailPage } from "./pages/AuditTrailPage";
import { EvaluationBenchmarkPage } from "./pages/EvaluationBenchmarkPage";

// Enhancements for SIH Problem Statement 26262
import { ObligationsPage } from "./pages/ObligationsPage";
import { EVCManagementPage } from "./pages/EVCManagementPage";
import { UndertakingsPage } from "./pages/UndertakingsPage";
import { DocumentValidityPage } from "./pages/DocumentValidityPage";
import { ComplianceReportsPage } from "./pages/ComplianceReportsPage";
import { AdminWorkflowConfigPage } from "./pages/AdminWorkflowConfigPage";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#F4F7FB]">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-[#1677C8] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <div className="text-sm font-semibold text-[#0B2545]">
            Verifying Regulatory Credentials...
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/institution/login" element={<Login />} />
            <Route path="/officer/login" element={<OfficerLogin />} />
            <Route path="/institution/register" element={<InstitutionRegister />} />
            <Route path="/institution/confirmation" element={<RegistrationConfirmation />} />

            {/* Protected Application Workspace */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="applications" element={<ApplicationsList />} />
              <Route path="applications/new" element={<CreateApplication />} />
              <Route path="applications/:id" element={<ApplicationDetail />} />
              <Route path="trustgraph" element={<TrustGraphExplorer />} />
              <Route path="verification" element={<VerificationPage />} />
              <Route path="rules" element={<RulesPage />} />
              <Route path="clarifications" element={<ClarificationsPage />} />
              
              {/* SIH PS 26262 Module Routes */}
              <Route path="obligations" element={<ObligationsPage />} />
              <Route path="my-obligations" element={<ObligationsPage />} />
              <Route path="evc" element={<EVCManagementPage />} />
              <Route path="undertakings" element={<UndertakingsPage />} />
              <Route path="document-validity" element={<DocumentValidityPage />} />
              <Route path="reports" element={<ComplianceReportsPage />} />

              <Route
                path="admin/workflow-config"
                element={
                  <ProtectedRoute allowedRoles={["AICTE_OFFICER", "ADMINISTRATOR"]}>
                    <AdminWorkflowConfigPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="audit"
                element={
                  <ProtectedRoute allowedRoles={["AICTE_OFFICER", "ADMINISTRATOR"]}>
                    <AuditTrailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="evaluation"
                element={
                  <ProtectedRoute allowedRoles={["AICTE_OFFICER", "ADMINISTRATOR"]}>
                    <EvaluationBenchmarkPage />
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Catch-all redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
