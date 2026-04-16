import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
    Save,
    User,
    Building,
    Bell,
    Shield,
    Circle,
    CheckCircle2,
    Clock3,
    Upload,
} from "lucide-react";
import { useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const inputStyle = {
    backgroundColor: "#1A1A1A",
    border: "1px solid #2A2A2A",
    borderRadius: "8px",
    color: "#ffffff",
    padding: "10px 12px",
    fontSize: "14px",
    width: "100%",
    outline: "none",
    transition: "border-color 0.15s ease",
};

const textareaStyle = {
    ...inputStyle,
    minHeight: "88px",
    resize: "vertical",
};

const monthOptions = [
    { value: "1", label: "January" },
    { value: "2", label: "February" },
    { value: "3", label: "March" },
    { value: "4", label: "April" },
    { value: "5", label: "May" },
    { value: "6", label: "June" },
    { value: "7", label: "July" },
    { value: "8", label: "August" },
    { value: "9", label: "September" },
    { value: "10", label: "October" },
    { value: "11", label: "November" },
    { value: "12", label: "December" },
];

const FIELD_HELP = "Fields marked with * are required.";

function parseLines(value) {
    return value
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
}

function toLines(value) {
    return Array.isArray(value) ? value.join("\n") : "";
}

function Field({ label, id, required = false, children, hint }) {
    return (
        <div className="grid gap-2">
            <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0]">
                {label}{required ? " *" : ""}
            </label>
            {children}
            {hint ? <p className="text-xs text-[#777]">{hint}</p> : null}
        </div>
    );
}

export default function SettingsPage() {
    const { user } = useUser();
    const { orgId, userId } = useOnboardingStatus();

    const [profile, setProfile] = useState({
        firstName: "",
        lastName: "",
        email: "",
        phone: "",
        professionalTitle: "",
    });

    const [business, setBusiness] = useState({
        id: "",
        legalName: "",
        tradingName: "",
        businessType: "",
        industry: "",
        registrationDate: "",
        annualTurnoverRange: "",
        primaryEmail: "",
        primaryPhone: "",
        website: "",
        employeeCount: "",
        registeredAddress: "",
        pincode: "",
        panNumber: "",
        stateOfRegistration: "",
        gstRegistered: false,
        gstin: "",
        gstFilingFrequency: "",
        tanNumber: "",
        cin: "",
        llpin: "",
        msmeNumber: "",
        iecCode: "",
        professionalTaxReg: "",
        primaryActivity: "",
        targetMarket: "",
        keyProductsText: "",
        currentChallengesText: "",
        accountingMethod: "accrual",
        financialYearStartMonth: "4",
        preferredLanguage: "en",
    });

    const [notifications, setNotifications] = useState({
        invoiceDue: true,
        paymentReceived: true,
        clientUpdates: false,
        weeklyReport: true,
        systemAlerts: true,
    });

    const [loading, setLoading] = useState(true);
    const [savingBusiness, setSavingBusiness] = useState(false);
    const [verificationTier, setVerificationTier] = useState("UNVERIFIED");
    const [verifying, setVerifying] = useState(false);
    const [certFile, setCertFile] = useState(null);

    useEffect(() => {
        if (user) {
            setProfile({
                firstName: user.firstName || "",
                lastName: user.lastName || "",
                email: user.primaryEmailAddress?.emailAddress || "",
                phone: user.primaryPhoneNumber?.phoneNumber || "",
                professionalTitle: "",
            });
        }

        const fetchBusinessData = async () => {
            if (!userId) return;
            try {
                const response = await fetch("/api/org/my", {
                    headers: {
                        "X-User-Id": userId,
                    },
                });
                if (!response.ok) {
                    throw new Error("Failed to load organization settings");
                }
                const result = await response.json();
                const data = result.data;
                if (!data) return;

                setBusiness({
                    id: data.id || "",
                    legalName: data.legalName || "",
                    tradingName: data.tradingName || "",
                    businessType: data.businessType || "",
                    industry: data.industry || "",
                    registrationDate: data.registrationDate || "",
                    annualTurnoverRange: data.annualTurnoverRange || "",
                    primaryEmail: data.primaryEmail || "",
                    primaryPhone: data.primaryPhone || "",
                    website: data.website || "",
                    employeeCount: data.employeeCount ?? "",
                    registeredAddress: data.registeredAddress || "",
                    pincode: data.pincode || "",
                    panNumber: data.panNumber || "",
                    stateOfRegistration: data.stateOfRegistration || "",
                    gstRegistered: Boolean(data.gstRegistered),
                    gstin: data.gstin || "",
                    gstFilingFrequency: data.gstFilingFrequency || "",
                    tanNumber: data.tanNumber || "",
                    cin: data.cin || "",
                    llpin: data.llpin || "",
                    msmeNumber: data.msmeNumber || "",
                    iecCode: data.iecCode || "",
                    professionalTaxReg: data.professionalTaxReg || "",
                    primaryActivity: data.primaryActivity || "",
                    targetMarket: data.targetMarket || "",
                    keyProductsText: toLines(data.keyProducts),
                    currentChallengesText: toLines(data.currentChallenges),
                    accountingMethod: data.accountingMethod || "accrual",
                    financialYearStartMonth: data.financialYearStartMonth || "4",
                    preferredLanguage: data.preferredLanguage || "en",
                });
                if (data.verificationTier) {
                    setVerificationTier(data.verificationTier);
                }
            } catch (error) {
                console.error("Failed to fetch business data:", error);
                toast.error(error.message || "Failed to load business settings");
            } finally {
                setLoading(false);
            }
        };

        fetchBusinessData();
    }, [user, orgId, userId]);

    const updateBusiness = (field, value) => {
        setBusiness((prev) => ({ ...prev, [field]: value }));
    };

    const handleBasicVerify = async () => {
        if (!userId) return;
        setVerifying(true);
        try {
            const resp = await fetch("/api/org/verify/basic", {
                method: "POST",
                headers: { "X-User-Id": userId },
            });
            const result = await resp.json();
            if (!resp.ok) throw new Error(result.message || "Verification failed");
            setVerificationTier("BASIC");
            toast.success("Basic verification complete!");
        } catch (err) {
            toast.error(err.message);
        } finally {
            setVerifying(false);
        }
    };

    const handleGstCertUpload = async (e) => {
        e.preventDefault();
        if (!certFile || !userId) return;
        setVerifying(true);
        try {
            const formData = new FormData();
            formData.append("file", certFile);
            const resp = await fetch("/api/org/verify/gst-certificate", {
                method: "POST",
                headers: { "X-User-Id": userId },
                body: formData,
            });
            const result = await resp.json();
            if (!resp.ok) throw new Error(result.message || "GST verification failed");
            setVerificationTier("GST_VERIFIED");
            setCertFile(null);
            toast.success("GST certificate verified!");
        } catch (err) {
            toast.error(err.message);
        } finally {
            setVerifying(false);
        }
    };

    const tierBadge = (tier) => {
        if (tier === "GST_VERIFIED") return { bg: "bg-[#4CBB17]", text: "text-black", label: "GST Verified" };
        if (tier === "BASIC") return { bg: "bg-[#F59E0B]", text: "text-black", label: "Basic Verified" };
        return { bg: "bg-[#2A2A2A]", text: "text-[#888]", label: "Unverified" };
    };

    const tierInfo = tierBadge(verificationTier);

    const validateBusiness = () => {
        if (!business.legalName.trim()) return "Legal name is required";
        if (!business.businessType.trim()) return "Business type is required";
        if (!business.industry.trim()) return "Industry is required";
        if (!business.primaryEmail.trim()) return "Primary email is required";
        if (!business.primaryPhone.trim()) return "Primary phone is required";
        if (!business.panNumber.trim()) return "PAN number is required";
        if (!business.primaryActivity.trim()) return "Primary activity is required";
        if (!business.targetMarket.trim()) return "Target market is required";
        if (business.gstRegistered) {
            if (!business.gstin.trim()) return "GSTIN is required when GST is enabled";
            if (!business.gstFilingFrequency.trim()) return "GST filing frequency is required when GST is enabled";
        }
        return null;
    };

    const handleSave = async (section) => {
        try {
            if (section === "Business" && userId) {
                const targetId = orgId || business.id;
                if (!targetId) throw new Error("Organization ID not found");

                const validationError = validateBusiness();
                if (validationError) throw new Error(validationError);

                setSavingBusiness(true);
                const response = await fetch(`/api/org/${targetId}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-Id": userId,
                    },
                    body: JSON.stringify({
                        legalName: business.legalName,
                        tradingName: business.tradingName,
                        businessType: business.businessType,
                        industry: business.industry,
                        registrationDate: business.registrationDate || null,
                        annualTurnoverRange: business.annualTurnoverRange,
                        primaryEmail: business.primaryEmail,
                        primaryPhone: business.primaryPhone,
                        website: business.website,
                        employeeCount: business.employeeCount === "" ? null : Number(business.employeeCount),
                        registeredAddress: business.registeredAddress,
                        pincode: business.pincode,
                        panNumber: business.panNumber,
                        stateOfRegistration: business.stateOfRegistration,
                        gstRegistered: business.gstRegistered,
                        gstin: business.gstRegistered ? business.gstin : "",
                        gstFilingFrequency: business.gstRegistered ? business.gstFilingFrequency : "",
                        tanNumber: business.tanNumber,
                        cin: business.cin,
                        llpin: business.llpin,
                        msmeNumber: business.msmeNumber,
                        iecCode: business.iecCode,
                        professionalTaxReg: business.professionalTaxReg,
                        primaryActivity: business.primaryActivity,
                        targetMarket: business.targetMarket,
                        keyProducts: parseLines(business.keyProductsText),
                        currentChallenges: parseLines(business.currentChallengesText),
                        accountingMethod: business.accountingMethod,
                        financialYearStartMonth: business.financialYearStartMonth,
                        preferredLanguage: business.preferredLanguage,
                    }),
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(payload?.message || "Failed to update business");
                }
                toast.success("Business settings saved");
                if (payload?.data) {
                    const data = payload.data;
                    setBusiness((prev) => ({
                        ...prev,
                        id: data.id || prev.id,
                        keyProductsText: toLines(data.keyProducts),
                        currentChallengesText: toLines(data.currentChallenges),
                    }));
                }
                return;
            }

            toast.success(`${section} settings saved`);
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSavingBusiness(false);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            <div>
                <h1 className="mo-h1">Settings</h1>
                <p className="mo-text-secondary mt-1">Manage your account and business preferences</p>
            </div>

            <Tabs defaultValue="profile" className="flex flex-col gap-4">
                <TabsList className="bg-[#1A1A1A] border border-[#2A2A2A] h-auto p-1 rounded-xl w-fit flex gap-1">
                    {[
                        { value: "profile", label: "Profile", icon: User },
                        { value: "business", label: "Business", icon: Building },
                        { value: "notifications", label: "Notifications", icon: Bell },
                        { value: "security", label: "Security", icon: Shield },
                    ].map(({ value, label, icon: Icon }) => (
                        <TabsTrigger
                            key={value}
                            value={value}
                            className="px-4 py-2 rounded-lg text-sm font-medium text-[#A0A0A0] data-[state=active]:bg-[#4CBB17] data-[state=active]:text-black transition-all flex items-center gap-2"
                        >
                            <Icon className="h-3.5 w-3.5" />
                            {label}
                        </TabsTrigger>
                    ))}
                </TabsList>

                <TabsContent value="profile">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Profile Information</h2>
                        <p className="mo-text-secondary mb-6">Update your personal information</p>
                        <div className="grid gap-4 md:grid-cols-2">
                            {[
                                { label: "First Name", id: "settings-first-name", field: "firstName" },
                                { label: "Last Name", id: "settings-last-name", field: "lastName" },
                                { label: "Email", id: "settings-email", field: "email", type: "email" },
                                { label: "Phone", id: "settings-phone", field: "phone", type: "tel" },
                                { label: "Professional Title", id: "settings-title", field: "professionalTitle", colSpan: true },
                            ].map(({ label, id, field, type, colSpan }) => (
                                <div key={id} className={`grid gap-2 ${colSpan ? "md:col-span-2" : ""}`}>
                                    <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0]">{label}</label>
                                    <input
                                        id={id}
                                        type={type || "text"}
                                        value={profile[field]}
                                        onChange={(e) => setProfile((prev) => ({ ...prev, [field]: e.target.value }))}
                                        style={inputStyle}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button onClick={() => handleSave("Profile")} className="mo-btn-primary flex items-center gap-2">
                                <Save className="h-4 w-4" /> Save Profile
                            </button>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="business">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Business Information</h2>
                        <p className="mo-text-secondary mb-2">Edit the same business details captured during onboarding.</p>
                        <p className="text-xs text-[#777] mb-6">{FIELD_HELP}</p>

                        <div className="grid gap-6">
                            <div className="grid gap-4 md:grid-cols-2">
                                <Field label="Legal Name" id="biz-legal-name" required>
                                    <input id="biz-legal-name" value={business.legalName} onChange={(e) => updateBusiness("legalName", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Trading Name" id="biz-trading-name">
                                    <input id="biz-trading-name" value={business.tradingName} onChange={(e) => updateBusiness("tradingName", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Business Type" id="biz-type" required>
                                    <input id="biz-type" value={business.businessType} onChange={(e) => updateBusiness("businessType", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Industry" id="biz-industry" required>
                                    <input id="biz-industry" value={business.industry} onChange={(e) => updateBusiness("industry", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Registration Date" id="biz-registration-date">
                                    <input id="biz-registration-date" type="date" value={business.registrationDate || ""} onChange={(e) => updateBusiness("registrationDate", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Annual Turnover Range" id="biz-turnover">
                                    <input id="biz-turnover" value={business.annualTurnoverRange} onChange={(e) => updateBusiness("annualTurnoverRange", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Primary Email" id="biz-primary-email" required>
                                    <input id="biz-primary-email" type="email" value={business.primaryEmail} onChange={(e) => updateBusiness("primaryEmail", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Primary Phone" id="biz-primary-phone" required>
                                    <input id="biz-primary-phone" value={business.primaryPhone} onChange={(e) => updateBusiness("primaryPhone", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Website" id="biz-website">
                                    <input id="biz-website" value={business.website} onChange={(e) => updateBusiness("website", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Employee Count" id="biz-employee-count">
                                    <input id="biz-employee-count" type="number" min="0" value={business.employeeCount} onChange={(e) => updateBusiness("employeeCount", e.target.value)} style={inputStyle} />
                                </Field>
                                <div className="md:col-span-2">
                                    <Field label="Registered Address" id="biz-registered-address">
                                        <textarea id="biz-registered-address" value={business.registeredAddress} onChange={(e) => updateBusiness("registeredAddress", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                                <Field label="Pincode" id="biz-pincode">
                                    <input id="biz-pincode" value={business.pincode} onChange={(e) => updateBusiness("pincode", e.target.value)} style={inputStyle} />
                                </Field>
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <Field label="PAN Number" id="biz-pan" required>
                                    <input id="biz-pan" value={business.panNumber} onChange={(e) => updateBusiness("panNumber", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="State of Registration" id="biz-state">
                                    <input id="biz-state" value={business.stateOfRegistration} onChange={(e) => updateBusiness("stateOfRegistration", e.target.value)} style={inputStyle} />
                                </Field>
                                <div className="flex items-center gap-3 md:col-span-2">
                                    <input
                                        id="biz-gst-registered"
                                        type="checkbox"
                                        checked={business.gstRegistered}
                                        onChange={(e) => updateBusiness("gstRegistered", e.target.checked)}
                                    />
                                    <label htmlFor="biz-gst-registered" className="text-sm font-medium text-[#A0A0A0]">GST Registered</label>
                                </div>
                                <Field label="GSTIN" id="biz-gstin" required={business.gstRegistered}>
                                    <input id="biz-gstin" value={business.gstin} onChange={(e) => updateBusiness("gstin", e.target.value.toUpperCase())} style={inputStyle} disabled={!business.gstRegistered} />
                                </Field>
                                <Field label="GST Filing Frequency" id="biz-gst-frequency" required={business.gstRegistered}>
                                    <input id="biz-gst-frequency" value={business.gstFilingFrequency} onChange={(e) => updateBusiness("gstFilingFrequency", e.target.value)} style={inputStyle} disabled={!business.gstRegistered} />
                                </Field>
                                <Field label="TAN Number" id="biz-tan">
                                    <input id="biz-tan" value={business.tanNumber} onChange={(e) => updateBusiness("tanNumber", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="CIN" id="biz-cin">
                                    <input id="biz-cin" value={business.cin} onChange={(e) => updateBusiness("cin", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="LLPIN" id="biz-llpin">
                                    <input id="biz-llpin" value={business.llpin} onChange={(e) => updateBusiness("llpin", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="MSME Number" id="biz-msme">
                                    <input id="biz-msme" value={business.msmeNumber} onChange={(e) => updateBusiness("msmeNumber", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="IEC Code" id="biz-iec">
                                    <input id="biz-iec" value={business.iecCode} onChange={(e) => updateBusiness("iecCode", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="Professional Tax Registration" id="biz-prof-tax">
                                    <input id="biz-prof-tax" value={business.professionalTaxReg} onChange={(e) => updateBusiness("professionalTaxReg", e.target.value)} style={inputStyle} />
                                </Field>
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="md:col-span-2">
                                    <Field label="Primary Activity" id="biz-primary-activity" required>
                                        <textarea id="biz-primary-activity" value={business.primaryActivity} onChange={(e) => updateBusiness("primaryActivity", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                                <Field label="Target Market" id="biz-target-market" required>
                                    <input id="biz-target-market" value={business.targetMarket} onChange={(e) => updateBusiness("targetMarket", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Accounting Method" id="biz-accounting-method" required>
                                    <input id="biz-accounting-method" value={business.accountingMethod} onChange={(e) => updateBusiness("accountingMethod", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Financial Year Start Month" id="biz-fy-start" required>
                                    <select id="biz-fy-start" value={business.financialYearStartMonth} onChange={(e) => updateBusiness("financialYearStartMonth", e.target.value)} style={inputStyle}>
                                        {monthOptions.map((month) => (
                                            <option key={month.value} value={month.value}>{month.label}</option>
                                        ))}
                                    </select>
                                </Field>
                                <Field label="Preferred Language" id="biz-language" required>
                                    <input id="biz-language" value={business.preferredLanguage} onChange={(e) => updateBusiness("preferredLanguage", e.target.value)} style={inputStyle} />
                                </Field>
                                <div className="md:col-span-2">
                                    <Field label="Key Products / Services" id="biz-key-products" hint="Enter one product or service per line.">
                                        <textarea id="biz-key-products" value={business.keyProductsText} onChange={(e) => updateBusiness("keyProductsText", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                                <div className="md:col-span-2">
                                    <Field label="Current Challenges" id="biz-current-challenges" hint="Enter one challenge per line.">
                                        <textarea id="biz-current-challenges" value={business.currentChallengesText} onChange={(e) => updateBusiness("currentChallengesText", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 rounded-2xl border border-[#2A2A2A] bg-[#0F0F0F] p-5">
                            <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
                                <div>
                                    <div className="flex items-center gap-3">
                                        <Shield className="h-5 w-5 text-white" />
                                        <h3 className="text-white font-semibold">Business Verification</h3>
                                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${tierInfo.bg} ${tierInfo.text}`}>
                                            {tierInfo.label}
                                        </span>
                                    </div>
                                    <p className="text-sm text-[#A0A0A0] mt-1">Unlock higher trust workflows as you complete verification steps.</p>
                                </div>
                            </div>

                            <div className="grid gap-3">
                                <div className="flex items-start gap-3 rounded-xl border border-[#1F1F1F] bg-[#141414] p-4">
                                    {verificationTier !== "UNVERIFIED"
                                        ? <CheckCircle2 className="h-5 w-5 text-[#4CBB17] mt-0.5" />
                                        : <Circle className="h-5 w-5 text-[#666] mt-0.5" />}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <p className="text-sm font-medium text-white">Basic Profile</p>
                                            {verificationTier === "BASIC" || verificationTier === "GST_VERIFIED"
                                                ? <span className="text-[11px] uppercase tracking-wide text-[#4CBB17]">Verified</span>
                                                : <span className="text-[11px] uppercase tracking-wide text-[#777]">Pending</span>}
                                        </div>
                                        <p className="text-xs text-[#A0A0A0] mt-0.5">Business name, phone, and industry on record.</p>
                                        {verificationTier === "UNVERIFIED" && (
                                            <button
                                                onClick={handleBasicVerify}
                                                disabled={verifying}
                                                className="mt-3 text-xs px-3 py-1.5 rounded-lg bg-[#4CBB17] text-black font-semibold hover:bg-[#45a815] transition-colors disabled:opacity-50"
                                            >
                                                {verifying ? "Verifying..." : "Verify Now"}
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-start gap-3 rounded-xl border border-[#1F1F1F] bg-[#141414] p-4">
                                    {verificationTier === "GST_VERIFIED"
                                        ? <CheckCircle2 className="h-5 w-5 text-[#4CBB17] mt-0.5" />
                                        : verificationTier === "BASIC"
                                        ? <Clock3 className="h-5 w-5 text-[#F59E0B] mt-0.5" />
                                        : <Circle className="h-5 w-5 text-[#666] mt-0.5" />}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <p className="text-sm font-medium text-white">GST Certificate</p>
                                            {verificationTier === "GST_VERIFIED"
                                                ? <span className="text-[11px] uppercase tracking-wide text-[#4CBB17]">Verified</span>
                                                : <span className="text-[11px] uppercase tracking-wide text-[#777]">Optional</span>}
                                        </div>
                                        <p className="text-xs text-[#A0A0A0] mt-0.5">Upload your GST certificate for GST_VERIFIED status. Requires valid GSTIN.</p>
                                        {verificationTier !== "GST_VERIFIED" && business.gstRegistered && business.gstin && (
                                            <form onSubmit={handleGstCertUpload} className="mt-3 flex items-center gap-2">
                                                <label className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border border-[#2A2A2A] cursor-pointer hover:border-[#4CBB17] transition-colors">
                                                    <Upload className="h-3.5 w-3.5 text-[#A0A0A0]" />
                                                    <span className="text-[#A0A0A0]">{certFile ? certFile.name : "Upload certificate"}</span>
                                                    <input
                                                        type="file"
                                                        accept="application/pdf,image/jpeg,image/png"
                                                        onChange={(e) => setCertFile(e.target.files[0])}
                                                        className="hidden"
                                                    />
                                                </label>
                                                {certFile && (
                                                    <button type="submit" disabled={verifying} className="text-xs px-3 py-1.5 rounded-lg bg-[#4CBB17] text-black font-semibold hover:bg-[#45a815] transition-colors disabled:opacity-50">
                                                        {verifying ? "Uploading..." : "Verify"}
                                                    </button>
                                                )}
                                            </form>
                                        )}
                                        {verificationTier !== "GST_VERIFIED" && (!business.gstRegistered || !business.gstin) && (
                                            <p className="mt-2 text-xs text-[#777]">Enable GST and add your GSTIN in the fields above to enable certificate upload.</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end">
                            <button onClick={() => handleSave("Business")} className="mo-btn-primary flex items-center gap-2" disabled={loading || savingBusiness}>
                                <Save className="h-4 w-4" /> {savingBusiness ? "Saving..." : "Save Business"}
                            </button>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="notifications">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Notification Preferences</h2>
                        <p className="mo-text-secondary mb-6">Choose when you want to be notified</p>
                        <div className="space-y-4">
                            {Object.entries(notifications).map(([key, enabled]) => {
                                const labels = {
                                    invoiceDue: { title: "Invoice Due Reminders", desc: "Get notified when invoices are about to be due" },
                                    paymentReceived: { title: "Payment Received", desc: "Get notified when a payment is received" },
                                    clientUpdates: { title: "Client Updates", desc: "Notifications when client info changes" },
                                    weeklyReport: { title: "Weekly Report", desc: "Receive a weekly financial summary every Monday" },
                                    systemAlerts: { title: "System Alerts", desc: "Important system and security notifications" },
                                };
                                const info = labels[key];

                                return (
                                    <div key={key} className="flex items-center justify-between p-4 bg-[#111111] rounded-xl border border-[#2A2A2A]">
                                        <div>
                                            <p className="text-sm font-medium text-white">{info.title}</p>
                                            <p className="text-xs text-[#A0A0A0] mt-0.5">{info.desc}</p>
                                        </div>
                                        <button
                                            role="switch"
                                            aria-checked={enabled}
                                            onClick={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key] }))}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enabled ? "bg-[#4CBB17]" : "bg-[#2A2A2A]"}`}
                                        >
                                            <span className={`inline-block h-4 w-4 transform rounded-full bg-black transition-transform ${enabled ? "translate-x-6" : "translate-x-1"}`} />
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button onClick={() => handleSave("Notifications")} className="mo-btn-primary flex items-center gap-2">
                                <Save className="h-4 w-4" /> Save Preferences
                            </button>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="security">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Security</h2>
                        <p className="mo-text-secondary mb-6">Manage your account security settings</p>
                        <div className="p-4 bg-[#4CBB1710] border border-[#4CBB1730] rounded-xl">
                            <p className="text-sm text-[#4CBB17] font-medium">Clerk-Managed Authentication</p>
                            <p className="text-sm text-[#A0A0A0] mt-1">
                                Your account is secured by Clerk. Password changes and two-factor authentication
                                are managed through the Clerk user portal.
                            </p>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
