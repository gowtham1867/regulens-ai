import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Eye,
  EyeOff,
  Lock,
  Mail,
  Building,
  UserCheck,
  ShieldAlert,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Building2,
  ArrowLeft,
  KeyRound,
  ExternalLink
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { AuthBranding } from "../components/auth/AuthBranding";

export const InstitutionLogin: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"SIGN_IN" | "REGISTER">("SIGN_IN");

  // Sign In Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Registration Form State
  const [regInstName, setRegInstName] = useState("");
  const [regFullName, setRegFullName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regState, setRegState] = useState("Delhi");
  const [regDistrict, setRegDistrict] = useState("New Delhi");
  const [regIntake, setRegIntake] = useState(300);
  const [regLandAcres, setRegLandAcres] = useState(5.0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showDemoGuide, setShowDemoGuide] = useState(false);
  const [wrongPortalOfficer, setWrongPortalOfficer] = useState(false);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please provide both your official email address and password.");
      return;
    }
    setLoading(true);
    setError(null);
    setWrongPortalOfficer(false);

    try {
      const user = await login(email, password, "INSTITUTION");
      if (user.role !== "INSTITUTION_USER") {
        setWrongPortalOfficer(true);
        setError("Access Denied: Your account has AICTE Scrutiny Officer privileges. Please sign in via the AICTE Officer Portal.");
        return;
      }
      navigate("/applications");
    } catch (err: any) {
      const msg = err.message || "Invalid authentication credentials";
      if (msg.includes("Officer Portal") || msg.includes("reserved for academic institutions")) {
        setWrongPortalOfficer(true);
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regEmail || !regPassword || !regInstName || !regFullName) {
      setError("Please complete all required fields for institutional accreditation onboarding.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await register({
        email: regEmail,
        password: regPassword,
        full_name: regFullName,
        institution_name: regInstName,
        state: regState,
        district: regDistrict,
        approved_intake: Number(regIntake),
        land_area_acres: Number(regLandAcres),
      });
      setSuccessMessage("Institution successfully registered and accredited! Entering portal...");
      setTimeout(() => navigate("/applications"), 600);
    } catch (err: any) {
      setError(err.message || "Registration failed. Please verify submitted details.");
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setMode("SIGN_IN");
    setError(null);
    setWrongPortalOfficer(false);
  };

  return (
    <div className="min-h-screen bg-[#F4F7FB] flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8">
      {/* Top Navigation Bar with Back to Selector */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md mb-3 flex items-center justify-between text-xs">
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-slate-500 hover:text-[#0B2545] font-semibold transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Switch Portal</span>
        </Link>
        <span className="text-[11px] font-semibold text-slate-400">
          Institution Access Gateway
        </span>
      </div>

      {/* Brand Branding */}
      <AuthBranding
        subtitle="Institution Compliance & Application Portal"
        roleBadge="For Colleges, Polytechnics & Universities"
      />

      {/* Main Card */}
      <div className="mt-5 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-6 px-6 sm:px-8 rounded-2xl shadow-sm border border-[#DCE4ED]">
          {/* Mode Switcher */}
          <div className="flex rounded-xl bg-slate-100 p-1 mb-5 text-xs font-bold">
            <button
              type="button"
              onClick={() => {
                setMode("SIGN_IN");
                setError(null);
                setWrongPortalOfficer(false);
              }}
              className={`flex-1 py-2 rounded-lg transition-all ${
                mode === "SIGN_IN"
                  ? "bg-[#0B2545] text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Institution Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("REGISTER");
                setError(null);
                setWrongPortalOfficer(false);
              }}
              className={`flex-1 py-2 rounded-lg transition-all ${
                mode === "REGISTER"
                  ? "bg-[#0B2545] text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Register Institution
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 animate-in fade-in">
              <div className="flex items-start gap-2.5">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold">{error}</p>
                  {wrongPortalOfficer && (
                    <div className="mt-2 pt-2 border-t border-rose-200/80">
                      <Link
                        to="/officer/login"
                        className="inline-flex items-center gap-1.5 font-bold text-[#1677C8] hover:text-[#0B2545] transition-colors"
                      >
                        <span>Click here to open AICTE Officer Login</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Success Alert */}
          {successMessage && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-2.5 text-xs text-emerald-800 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* SIGN IN FORM */}
          {mode === "SIGN_IN" && (
            <form onSubmit={handleLoginSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Authorized Institution Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="registrar@institution.edu.in"
                    required
                    className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs font-medium text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    className="w-full pl-9 pr-10 py-2.5 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs font-medium text-slate-900"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 px-4 rounded-xl bg-[#0B2545] hover:bg-[#123B63] text-white font-bold text-xs shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <span>{loading ? "Authenticating Institution..." : "Sign In to Institution Portal"}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* REGISTER INSTITUTION FORM */}
          {mode === "REGISTER" && (
            <form onSubmit={handleRegisterSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Institution Name <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Building className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={regInstName}
                    onChange={(e) => setRegInstName(e.target.value)}
                    placeholder="e.g. Apex Institute of Technology & Engineering"
                    required
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Authorized Signatory (Registrar / Principal) <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <UserCheck className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={regFullName}
                    onChange={(e) => setRegFullName(e.target.value)}
                    placeholder="e.g. Dr. K. Balasubramanian"
                    required
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Official Email <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="registrar@institution.edu.in"
                    required
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Password <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="Min 6 chars"
                    required
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1677C8] focus:bg-white text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">State</label>
                  <input
                    type="text"
                    value={regState}
                    onChange={(e) => setRegState(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl text-xs"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">District</label>
                  <input
                    type="text"
                    value={regDistrict}
                    onChange={(e) => setRegDistrict(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Approved Intake</label>
                  <input
                    type="number"
                    value={regIntake}
                    onChange={(e) => setRegIntake(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Land Area (Acres)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={regLandAcres}
                    onChange={(e) => setRegLandAcres(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-[#DCE4ED] rounded-xl text-xs font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 px-4 rounded-xl bg-[#1677C8] hover:bg-[#1264a8] text-white font-bold text-xs shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <span>{loading ? "Registering Institution..." : "Complete Registration & Accreditation"}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Quick Demo Credentials Guide for Colleges */}
          <div className="mt-5 pt-4 border-t border-[#DCE4ED]">
            <button
              type="button"
              onClick={() => setShowDemoGuide(!showDemoGuide)}
              className="w-full flex items-center justify-between text-[11px] font-semibold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-[#1677C8]" />
                <span>Demo Institution Accounts for Evaluators</span>
              </div>
              {showDemoGuide ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
            </button>

            {showDemoGuide && (
              <div className="mt-2.5 space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div
                  onClick={() => fillDemo("apex@institution.edu.in", "Institute@123")}
                  className="p-1.5 rounded-lg hover:bg-blue-50 cursor-pointer flex justify-between items-center transition-colors"
                >
                  <div>
                    <b className="text-slate-800">Apex Institute (Main EoA Case):</b>
                    <div className="text-[10px] text-slate-500 font-mono">apex@institution.edu.in</div>
                  </div>
                  <span className="font-bold text-[10px] text-[#1677C8] bg-blue-100/60 px-2 py-0.5 rounded">Fill</span>
                </div>
                <div
                  onClick={() => fillDemo("zenith@institution.edu.in", "Institute@123")}
                  className="p-1.5 rounded-lg hover:bg-blue-50 cursor-pointer flex justify-between items-center transition-colors"
                >
                  <div>
                    <b className="text-slate-800">Zenith University:</b>
                    <div className="text-[10px] text-slate-500 font-mono">zenith@institution.edu.in</div>
                  </div>
                  <span className="font-bold text-[10px] text-[#1677C8] bg-blue-100/60 px-2 py-0.5 rounded">Fill</span>
                </div>
                <div
                  onClick={() => fillDemo("vanguard@institution.edu.in", "Institute@123")}
                  className="p-1.5 rounded-lg hover:bg-blue-50 cursor-pointer flex justify-between items-center transition-colors"
                >
                  <div>
                    <b className="text-slate-800">Vanguard Institute:</b>
                    <div className="text-[10px] text-slate-500 font-mono">vanguard@institution.edu.in</div>
                  </div>
                  <span className="font-bold text-[10px] text-[#1677C8] bg-blue-100/60 px-2 py-0.5 rounded">Fill</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Switcher Footer to Officer Portal */}
        <div className="mt-4 text-center text-xs text-slate-500 flex flex-col gap-1 items-center">
          <div>
            <span>Are you an AICTE Scrutiny Officer? </span>
            <Link
              to="/officer/login"
              className="font-bold text-[#1677C8] hover:text-[#0B2545] transition-colors"
            >
              Sign In via AICTE Officer Portal →
            </Link>
          </div>
          <p className="text-[10px] text-slate-400">
            ReguLens AI • Evidence-Driven Regulatory Intelligence • SIH26261
          </p>
        </div>
      </div>
    </div>
  );
};

