import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
  Building2,
  UserCheck,
  BadgeCheck,
  ArrowLeft,
  CheckCircle2,
  Lock,
  Mail,
  Phone,
  MapPin,
  Building
} from "lucide-react";
import { api } from "../services/api";

const INDIAN_STATES = [
  "Andhra Pradesh",
  "Assam",
  "Bihar",
  "Chandigarh",
  "Chhattisgarh",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu & Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Tamil Nadu",
  "Telangana",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal"
];

const INSTITUTION_TYPES = [
  { value: "ENGINEERING_AND_TECHNOLOGY", label: "Engineering & Technology" },
  { value: "MANAGEMENT", label: "Management Studies (MBA / PGDM)" },
  { value: "PHARMACY", label: "Pharmacy" },
  { value: "ARCHITECTURE_AND_PLANNING", label: "Architecture & Planning" },
  { value: "APPLIED_ARTS_AND_CRAFTS", label: "Applied Arts & Crafts" },
  { value: "HOTEL_MANAGEMENT", label: "Hotel Management & Catering" },
  { value: "POLYTECHNIC_DIPLOMA", label: "Polytechnic / Diploma Institution" }
];

export const InstitutionRegister: React.FC = () => {
  const navigate = useNavigate();

  // Institution Fields
  const [institutionName, setInstitutionName] = useState("");
  const [institutionType, setInstitutionType] = useState("ENGINEERING_AND_TECHNOLOGY");
  const [aicteId, setAicteId] = useState("");
  const [address, setAddress] = useState("");
  const [state, setState] = useState("Delhi");
  const [district, setDistrict] = useState("");
  const [pinCode, setPinCode] = useState("");
  const [institutionEmail, setInstitutionEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  // Account Administrator Fields
  const [fullName, setFullName] = useState("");
  const [designation, setDesignation] = useState("");
  const [workEmail, setWorkEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Authorization Checkbox
  const [isAuthorized, setIsAuthorized] = useState(false);

  // Feedback State
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validations
    if (!institutionName.trim()) {
      setError("Please provide the official institution name.");
      return;
    }

    if (!address.trim()) {
      setError("Please provide the official institutional address.");
      return;
    }

    if (!district.trim()) {
      setError("Please provide the district where the institution is situated.");
      return;
    }

    if (!pinCode.trim() || !/^\d{6}$/.test(pinCode.trim())) {
      setError("Please provide a valid 6-digit postal PIN code.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!institutionEmail.trim() || !emailRegex.test(institutionEmail.trim())) {
      setError("Please provide a valid official institutional email address.");
      return;
    }

    if (!contactPhone.trim() || !/^\d{10}$/.test(contactPhone.trim().replace(/[-\s]/g, ""))) {
      setError("Please provide a valid 10-digit institutional contact telephone number.");
      return;
    }

    if (!fullName.trim()) {
      setError("Please provide the authorized representative's full name.");
      return;
    }

    if (!designation.trim()) {
      setError("Please provide the representative's official designation (e.g. Principal, Director, Registrar).");
      return;
    }

    if (!workEmail.trim() || !emailRegex.test(workEmail.trim())) {
      setError("Please provide a valid administrator work email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long for regulatory compliance.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Password and confirmation password do not match. Please verify.");
      return;
    }

    if (!isAuthorized) {
      setError("You must confirm that you are authorized to register this institution and verify accuracy.");
      return;
    }

    setLoading(true);

    try {
      const payload = {
        institution_name: institutionName.trim(),
        institution_type: institutionType,
        aicte_id: aicteId.trim() || undefined,
        address: address.trim(),
        state: state,
        district: district.trim(),
        pin_code: pinCode.trim(),
        institution_email: institutionEmail.trim().toLowerCase(),
        contact_phone: contactPhone.trim(),
        full_name: fullName.trim(),
        designation: designation.trim(),
        email: workEmail.trim().toLowerCase(),
        password: password,
        phone: contactPhone.trim()
      };

      const result = await api.register(payload);

      // Successfully registered with PENDING_VERIFICATION
      navigate("/institution/confirmation", {
        replace: true,
        state: {
          institution_name: result.institution_name || institutionName.trim(),
          aicte_id: aicteId.trim() || "Generated upon AICTE verification",
          email: workEmail.trim().toLowerCase(),
          full_name: fullName.trim(),
          approval_status: result.approval_status || "PENDING_VERIFICATION",
          submitted_at: new Date().toISOString()
        }
      });
    } catch (err: any) {
      const msg = err.message || "Failed to create institution account. Please check your information.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F6F6F4] flex flex-col justify-between py-6 px-4 sm:px-6 lg:px-8 font-sans text-[#241C15]">
      {/* Top Header */}
      <header className="max-w-4xl mx-auto w-full flex items-center justify-between pb-4">
        <Link to="/login" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-[#0B2545] flex items-center justify-center text-white shadow-xs group-hover:bg-[#123B63] transition-colors">
            <Shield className="w-5 h-5 text-[#16A6C8]" />
          </div>
          <div>
            <div className="font-extrabold text-lg tracking-tight text-[#0B2545] leading-none flex items-center">
              <span>ReguLens</span>
              <span className="text-[#007C89] ml-1">AI</span>
            </div>
            <div className="text-[11px] text-slate-500 font-medium tracking-wide mt-0.5">
              Evidence-Driven Regulatory Intelligence
            </div>
          </div>
        </Link>

        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-[#007C89] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Institution Login</span>
        </Link>
      </header>

      {/* Main Registration Card */}
      <main className="w-full max-w-2xl mx-auto my-auto py-4">
        <div className="bg-white rounded-2xl border border-[#E2E2DF] shadow-xs p-6 sm:p-9">
          {/* Heading */}
          <div className="mb-6">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#007C89]/10 text-[#007C89] text-[11px] font-bold uppercase tracking-wider mb-2">
              <Building2 className="w-3.5 h-3.5 text-[#007C89]" />
              <span>AICTE Institutional Enrollment</span>
            </div>
            <h1 className="text-2xl font-bold text-[#241C15] tracking-tight">
              Register Your Institution
            </h1>
            <p className="mt-1 text-xs text-[#555555] font-normal leading-relaxed">
              Create an institution account to submit applications and manage regulatory compliance through ReguLens AI.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 animate-in fade-in duration-150"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="leading-relaxed font-medium">{error}</span>
                {error.includes("already exists") && (
                  <div className="mt-2">
                    <Link
                      to="/login"
                      className="inline-flex items-center gap-1 font-bold text-[#007C89] hover:underline"
                    >
                      <span>Proceed to Sign In</span>
                      <ArrowLeft className="w-3.5 h-3.5 rotate-180" />
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* SECTION 1: INSTITUTION INFORMATION */}
            <div className="border border-[#E2E2DF] rounded-xl p-4.5 bg-[#FAFBFB]">
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-[#E5E5E2]">
                <Building className="w-4 h-4 text-[#007C89]" />
                <h2 className="text-sm font-bold text-[#0B2545]">
                  1. Institution Information
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div className="sm:col-span-2">
                  <label
                    htmlFor="reg-name"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Official Institution Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-name"
                    type="text"
                    required
                    value={institutionName}
                    onChange={(e) => setInstitutionName(e.target.value)}
                    placeholder="e.g. National Institute of Technology & Engineering"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-type"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Institution Category / Type <span className="text-rose-500">*</span>
                  </label>
                  <select
                    id="reg-type"
                    value={institutionType}
                    onChange={(e) => setInstitutionType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  >
                    {INSTITUTION_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="reg-aicte-id"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    AICTE Permanent ID <span className="text-slate-400 font-normal">(if assigned)</span>
                  </label>
                  <input
                    id="reg-aicte-id"
                    type="text"
                    value={aicteId}
                    onChange={(e) => setAicteId(e.target.value)}
                    placeholder="e.g. 1-2814891129 (optional for new)"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label
                    htmlFor="reg-address"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Official Institutional Address <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-address"
                    type="text"
                    required
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Campus building, survey number, street name"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-state"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    State / Union Territory <span className="text-rose-500">*</span>
                  </label>
                  <select
                    id="reg-state"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  >
                    {INDIAN_STATES.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="reg-district"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    District <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-district"
                    type="text"
                    required
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    placeholder="e.g. Pune, South Delhi, Bengaluru"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-pincode"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Postal PIN Code <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-pincode"
                    type="text"
                    required
                    maxLength={6}
                    value={pinCode}
                    onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ""))}
                    placeholder="6-digit PIN code"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-contact-phone"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Contact Telephone Number <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-contact-phone"
                    type="tel"
                    required
                    maxLength={10}
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value.replace(/\D/g, ""))}
                    placeholder="10-digit phone number"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label
                    htmlFor="reg-inst-email"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Official Institution Email <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-inst-email"
                    type="email"
                    required
                    value={institutionEmail}
                    onChange={(e) => setInstitutionEmail(e.target.value)}
                    placeholder="e.g. registrar@institution.edu.in"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>
              </div>
            </div>

            {/* SECTION 2: ACCOUNT ADMINISTRATOR INFORMATION */}
            <div className="border border-[#E2E2DF] rounded-xl p-4.5 bg-[#FAFBFB]">
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-[#E5E5E2]">
                <UserCheck className="w-4 h-4 text-[#007C89]" />
                <h2 className="text-sm font-bold text-[#0B2545]">
                  2. Account Administrator Information
                </h2>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label
                    htmlFor="reg-admin-name"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Authorized Representative's Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-admin-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Dr. Ramesh Kumar"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div>
                  <label
                    htmlFor="reg-designation"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Designation <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-designation"
                    type="text"
                    required
                    value={designation}
                    onChange={(e) => setDesignation(e.target.value)}
                    placeholder="e.g. Principal / Director / Registrar"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label
                    htmlFor="reg-work-email"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Work Email Address (Sign In Username) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="reg-work-email"
                    type="email"
                    required
                    value={workEmail}
                    onChange={(e) => setWorkEmail(e.target.value)}
                    placeholder="e.g. principal@institution.edu.in"
                    className="w-full px-3 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    This email will serve as your primary administrator credential for logging into ReguLens AI.
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="reg-password"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Password (min. 8 characters) <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="At least 8 characters"
                      className="w-full pl-3 pr-9 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#241C15] p-1 cursor-pointer"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <EyeOff className="w-3.5 h-3.5" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="reg-confirm-password"
                    className="block text-xs font-semibold text-[#241C15] mb-1"
                  >
                    Confirm Password <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="reg-confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter password"
                      className="w-full pl-3 pr-9 py-2 rounded-lg border border-[#D0D0CD] bg-white text-xs text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#007C89] focus:ring-1 focus:ring-[#007C89]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#241C15] p-1 cursor-pointer"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-3.5 h-3.5" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION 3: AUTHORIZATION CONFIRMATION */}
            <div className="p-4 rounded-xl border border-teal-200 bg-teal-50/50">
              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  required
                  checked={isAuthorized}
                  onChange={(e) => setIsAuthorized(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded border-[#C8C8C8] text-[#007C89] focus:ring-[#007C89] cursor-pointer"
                />
                <span className="text-xs text-[#241C15] leading-relaxed">
                  <strong className="font-semibold text-[#007C89]">Statutory Authorization Declaration:</strong> I confirm that I am authorized to register this institution and that all submitted information is accurate, genuine, and subject to verification by AICTE Scrutiny Officers.
                </span>
              </label>
            </div>

            {/* SUBMIT BUTTON */}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-lg bg-[#007C89] hover:bg-[#006570] text-white font-bold text-sm tracking-wide shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Submitting Registration to AICTE...</span>
                  </>
                ) : (
                  <span>Create Institution Account</span>
                )}
              </button>
            </div>

            {/* Back to Login */}
            <div className="text-center pt-2">
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-[#007C89] transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Already registered? Back to Institution Login</span>
              </Link>
            </div>
          </form>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-4xl mx-auto w-full text-center text-xs text-slate-400 py-2">
        <p>
          © 2026 All India Council for Technical Education (AICTE) • ReguLens AI Regulatory Compliance Engine
        </p>
      </footer>
    </div>
  );
};

