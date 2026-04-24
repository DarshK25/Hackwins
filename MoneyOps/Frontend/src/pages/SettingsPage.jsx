import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Save, User, Building, Bell, Shield, AlertTriangle, Trash2 } from "lucide-react";
import { useClerk, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { useSettings } from "@/hooks/useSettings";
import { rememberDeletedAccountNotice } from "@/lib/accountDeletionNotice";
import { clearRememberedTeamSecurityCode } from "@/lib/teamSecurityCode";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

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

const currencyOptions = [
    { value: "INR", label: "Indian Rupee (INR)" },
    { value: "USD", label: "US Dollar (USD)" },
    { value: "EUR", label: "Euro (EUR)" },
    { value: "GBP", label: "British Pound (GBP)" },
    { value: "AUD", label: "Australian Dollar (AUD)" },
    { value: "CAD", label: "Canadian Dollar (CAD)" },
    { value: "SGD", label: "Singapore Dollar (SGD)" },
    { value: "AED", label: "UAE Dirham (AED)" },
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
    const { signOut } = useClerk();
    const { user } = useUser();
    const { orgId, userId, reset: resetOnboardingStatus } = useOnboardingStatus();
    const {
        settings,
        loading: settingsLoading,
        savingBySection,
        profileDraft,
        setProfileDraft,
        businessDraft,
        setBusinessDraft,
        notificationsDraft,
        setNotificationsDraft,
        updateSettings,
    } = useSettings();

    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [deleteTeamActionCode, setDeleteTeamActionCode] = useState("");
    const [deletingAccount, setDeletingAccount] = useState(false);

    useEffect(() => {
        if (user && profileDraft === null) {
            setProfileDraft({
                firstName: user.firstName || "",
                lastName: user.lastName || "",
                email: user.primaryEmailAddress?.emailAddress || "",
                phone: user.primaryPhoneNumber?.phoneNumber || "",
                professionalTitle: "",
            });
        }
    }, [user, profileDraft, setProfileDraft]);

    const updateBusiness = (field, value) => {
        setBusinessDraft((prev) => ({ ...prev, [field]: value }));
    };

    const validateBusiness = () => {
        if (!businessDraft?.legalName?.trim()) return "Legal name is required";
        if (!businessDraft?.businessType?.trim()) return "Business type is required";
        if (!businessDraft?.industry?.trim()) return "Industry is required";
        if (!businessDraft?.primaryEmail?.trim()) return "Primary email is required";
        if (!businessDraft?.primaryPhone?.trim()) return "Primary phone is required";
        if (!businessDraft?.panNumber?.trim()) return "PAN number is required";
        if (!businessDraft?.primaryActivity?.trim()) return "Primary activity is required";
        if (!businessDraft?.targetMarket?.trim()) return "Target market is required";
        if (businessDraft?.gstRegistered) {
            if (!businessDraft?.gstin?.trim()) return "GSTIN is required when GST is enabled";
            if (!businessDraft?.gstFilingFrequency?.trim()) return "GST filing frequency is required when GST is enabled";
        }
        return null;
    };

    const handleSaveProfile = async () => {
        try {
            if (user) {
                try {
                    await user.update({
                        firstName: profileDraft.firstName,
                        lastName: profileDraft.lastName,
                    });
                } catch (clerkErr) {
                    toast.error("Failed to update profile in Clerk");
                    return;
                }
            }
            await updateSettings("profile");
        } catch (err) {
            // error already shown via toast
        }
    };

    const handleSaveBusiness = async () => {
        const validationError = validateBusiness();
        if (validationError) {
            toast.error(validationError);
            return;
        }
        try {
            await updateSettings("business");
        } catch (err) {
            if (err.message?.includes("403")) {
                toast.error("You do not have permission to edit business settings");
            }
        }
    };

    const handleSaveNotifications = async () => {
        try {
            await updateSettings("notifications");
        } catch (err) {
            // error already shown via toast
        }
    };

    const handleDeleteDialogChange = (open) => {
        if (deletingAccount) return;
        setDeleteDialogOpen(open);
        if (!open) {
            setDeleteTeamActionCode("");
        }
    };

    const handleDeleteAccount = async () => {
        if (!orgId || !userId) {
            toast.error("Account context is missing");
            return;
        }

        if (!deleteTeamActionCode.trim()) {
            toast.error("Team security code is required");
            return;
        }

        setDeletingAccount(true);
        try {
            const response = await fetch(`/api/org/${orgId}`, {
                method: "DELETE",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": userId,
                },
                body: JSON.stringify({
                    teamActionCode: deleteTeamActionCode.trim(),
                }),
            });

            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload?.message || "Failed to delete account");
            }

            clearRememberedTeamSecurityCode(orgId);
            rememberDeletedAccountNotice({
                businessName: businessDraft?.legalName || businessDraft?.tradingName || "your workspace",
            });
            toast.success("Account deleted permanently");
            setDeleteDialogOpen(false);
            setDeleteTeamActionCode("");
            resetOnboardingStatus();
            await signOut();
            window.location.replace("/");
        } catch (error) {
            toast.error(error.message || "Failed to delete account");
        } finally {
            setDeletingAccount(false);
        }
    };

    if (settingsLoading) {
        return (
            <div className="flex flex-col gap-6">
                <div>
                    <h1 className="mo-h1">Settings</h1>
                    <p className="mo-text-secondary mt-1">Manage your account and business preferences</p>
                </div>
                <div className="flex items-center justify-center py-12">
                    <p className="text-[#A0A0A0]">Loading settings...</p>
                </div>
            </div>
        );
    }

    return (
        <>
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
                            <div className="grid gap-2">
                                <label htmlFor="settings-first-name" className="text-sm font-medium text-[#A0A0A0]">First Name</label>
                                <input
                                    id="settings-first-name"
                                    type="text"
                                    value={profileDraft?.firstName || ""}
                                    onChange={(e) => setProfileDraft((prev) => ({ ...prev, firstName: e.target.value }))}
                                    style={inputStyle}
                                />
                            </div>
                            <div className="grid gap-2">
                                <label htmlFor="settings-last-name" className="text-sm font-medium text-[#A0A0A0]">Last Name</label>
                                <input
                                    id="settings-last-name"
                                    type="text"
                                    value={profileDraft?.lastName || ""}
                                    onChange={(e) => setProfileDraft((prev) => ({ ...prev, lastName: e.target.value }))}
                                    style={inputStyle}
                                />
                            </div>
                            <div className="grid gap-2">
                                <label htmlFor="settings-email" className="text-sm font-medium text-[#A0A0A0]">Email</label>
                                <input
                                    id="settings-email"
                                    type="email"
                                    value={profileDraft?.email || ""}
                                    readOnly
                                    style={{ ...inputStyle, opacity: 0.6, cursor: "not-allowed" }}
                                />
                                <p className="text-xs text-[#777]">Managed by Clerk</p>
                            </div>
                            <div className="grid gap-2">
                                <label htmlFor="settings-phone" className="text-sm font-medium text-[#A0A0A0]">Phone</label>
                                <input
                                    id="settings-phone"
                                    type="tel"
                                    value={profileDraft?.phone || ""}
                                    onChange={(e) => setProfileDraft((prev) => ({ ...prev, phone: e.target.value }))}
                                    style={inputStyle}
                                />
                            </div>
                            <div className="grid gap-2 md:col-span-2">
                                <label htmlFor="settings-title" className="text-sm font-medium text-[#A0A0A0]">Professional Title</label>
                                <input
                                    id="settings-title"
                                    type="text"
                                    value={profileDraft?.professionalTitle || ""}
                                    onChange={(e) => setProfileDraft((prev) => ({ ...prev, professionalTitle: e.target.value }))}
                                    style={inputStyle}
                                />
                            </div>
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={handleSaveProfile}
                                disabled={savingBySection?.profile}
                                className="mo-btn-primary flex items-center gap-2"
                            >
                                <Save className="h-4 w-4" /> {savingBySection?.profile ? "Saving..." : "Save Profile"}
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
                                    <input id="biz-legal-name" value={businessDraft?.legalName || ""} onChange={(e) => updateBusiness("legalName", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Trading Name" id="biz-trading-name">
                                    <input id="biz-trading-name" value={businessDraft?.tradingName || ""} onChange={(e) => updateBusiness("tradingName", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Business Type" id="biz-type" required>
                                    <input id="biz-type" value={businessDraft?.businessType || ""} onChange={(e) => updateBusiness("businessType", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Industry" id="biz-industry" required>
                                    <input id="biz-industry" value={businessDraft?.industry || ""} onChange={(e) => updateBusiness("industry", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Registration Date" id="biz-registration-date">
                                    <input id="biz-registration-date" type="date" value={businessDraft?.registrationDate || ""} onChange={(e) => updateBusiness("registrationDate", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Annual Turnover Range" id="biz-turnover">
                                    <input id="biz-turnover" value={businessDraft?.annualTurnoverRange || ""} onChange={(e) => updateBusiness("annualTurnoverRange", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Primary Email" id="biz-primary-email" required>
                                    <input id="biz-primary-email" type="email" value={businessDraft?.primaryEmail || ""} onChange={(e) => updateBusiness("primaryEmail", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Primary Phone" id="biz-primary-phone" required>
                                    <input id="biz-primary-phone" value={businessDraft?.primaryPhone || ""} onChange={(e) => updateBusiness("primaryPhone", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Website" id="biz-website">
                                    <input id="biz-website" value={businessDraft?.website || ""} onChange={(e) => updateBusiness("website", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Employee Count" id="biz-employee-count">
                                    <input id="biz-employee-count" type="number" min="0" value={businessDraft?.employeeCount ?? ""} onChange={(e) => updateBusiness("employeeCount", e.target.value === "" ? null : Number(e.target.value))} style={inputStyle} />
                                </Field>
                                <div className="md:col-span-2">
                                    <Field label="Registered Address" id="biz-registered-address">
                                        <textarea id="biz-registered-address" value={businessDraft?.registeredAddress || ""} onChange={(e) => updateBusiness("registeredAddress", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                                <Field label="Pincode" id="biz-pincode">
                                    <input id="biz-pincode" value={businessDraft?.pincode || ""} onChange={(e) => updateBusiness("pincode", e.target.value)} style={inputStyle} />
                                </Field>
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <Field label="PAN Number" id="biz-pan" required>
                                    <input id="biz-pan" value={businessDraft?.panNumber || ""} onChange={(e) => updateBusiness("panNumber", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="State of Registration" id="biz-state">
                                    <input id="biz-state" value={businessDraft?.stateOfRegistration || ""} onChange={(e) => updateBusiness("stateOfRegistration", e.target.value)} style={inputStyle} />
                                </Field>
                                <div className="flex items-center gap-3 md:col-span-2">
                                    <input
                                        id="biz-gst-registered"
                                        type="checkbox"
                                        checked={businessDraft?.gstRegistered || false}
                                        onChange={(e) => updateBusiness("gstRegistered", e.target.checked)}
                                    />
                                    <label htmlFor="biz-gst-registered" className="text-sm font-medium text-[#A0A0A0]">GST Registered</label>
                                </div>
                                <Field label="GSTIN" id="biz-gstin" required={businessDraft?.gstRegistered}>
                                    <input id="biz-gstin" value={businessDraft?.gstin || ""} onChange={(e) => updateBusiness("gstin", e.target.value.toUpperCase())} style={inputStyle} disabled={!businessDraft?.gstRegistered} />
                                </Field>
                                <Field label="GST Filing Frequency" id="biz-gst-frequency" required={businessDraft?.gstRegistered}>
                                    <input id="biz-gst-frequency" value={businessDraft?.gstFilingFrequency || ""} onChange={(e) => updateBusiness("gstFilingFrequency", e.target.value)} style={inputStyle} disabled={!businessDraft?.gstRegistered} />
                                </Field>
                                <Field label="TAN Number" id="biz-tan">
                                    <input id="biz-tan" value={businessDraft?.tanNumber || ""} onChange={(e) => updateBusiness("tanNumber", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="CIN" id="biz-cin">
                                    <input id="biz-cin" value={businessDraft?.cin || ""} onChange={(e) => updateBusiness("cin", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="LLPIN" id="biz-llpin">
                                    <input id="biz-llpin" value={businessDraft?.llpin || ""} onChange={(e) => updateBusiness("llpin", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="MSME Number" id="biz-msme">
                                    <input id="biz-msme" value={businessDraft?.msmeNumber || ""} onChange={(e) => updateBusiness("msmeNumber", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="IEC Code" id="biz-iec">
                                    <input id="biz-iec" value={businessDraft?.iecCode || ""} onChange={(e) => updateBusiness("iecCode", e.target.value.toUpperCase())} style={inputStyle} />
                                </Field>
                                <Field label="Professional Tax Registration" id="biz-prof-tax">
                                    <input id="biz-prof-tax" value={businessDraft?.professionalTaxReg || ""} onChange={(e) => updateBusiness("professionalTaxReg", e.target.value)} style={inputStyle} />
                                </Field>
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="md:col-span-2">
                                    <Field label="Primary Activity" id="biz-primary-activity" required>
                                        <textarea id="biz-primary-activity" value={businessDraft?.primaryActivity || ""} onChange={(e) => updateBusiness("primaryActivity", e.target.value)} style={textareaStyle} />
                                    </Field>
                                </div>
                                <Field label="Target Market" id="biz-target-market" required>
                                    <input id="biz-target-market" value={businessDraft?.targetMarket || ""} onChange={(e) => updateBusiness("targetMarket", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Accounting Method" id="biz-accounting-method" required>
                                    <input id="biz-accounting-method" value={businessDraft?.accountingMethod || "accrual"} onChange={(e) => updateBusiness("accountingMethod", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Financial Year Start Month" id="biz-fy-start" required>
                                    <select id="biz-fy-start" value={businessDraft?.financialYearStartMonth || "4"} onChange={(e) => updateBusiness("financialYearStartMonth", e.target.value)} style={inputStyle}>
                                        {monthOptions.map((month) => (
                                            <option key={month.value} value={month.value}>{month.label}</option>
                                        ))}
                                    </select>
                                </Field>
                                <Field label="Preferred Language" id="biz-language" required>
                                    <input id="biz-language" value={businessDraft?.preferredLanguage || "en"} onChange={(e) => updateBusiness("preferredLanguage", e.target.value)} style={inputStyle} />
                                </Field>
                                <Field label="Currency" id="biz-currency" required>
                                    <select id="biz-currency" value={businessDraft?.currency || "INR"} onChange={(e) => updateBusiness("currency", e.target.value)} style={inputStyle}>
                                        {currencyOptions.map((curr) => (
                                            <option key={curr.value} value={curr.value}>{curr.label}</option>
                                        ))}
                                    </select>
                                </Field>
                                <div className="md:col-span-2">
                                    <Field label="Key Products / Services" id="biz-key-products" hint="Enter one product or service per line.">
                                        <textarea id="biz-key-products" value={toLines(businessDraft?.keyProducts)} onChange={(e) => updateBusiness("keyProducts", parseLines(e.target.value))} style={textareaStyle} />
                                    </Field>
                                </div>
                                <div className="md:col-span-2">
                                    <Field label="Current Challenges" id="biz-current-challenges" hint="Enter one challenge per line.">
                                        <textarea id="biz-current-challenges" value={toLines(businessDraft?.currentChallenges)} onChange={(e) => updateBusiness("currentChallenges", parseLines(e.target.value))} style={textareaStyle} />
                                    </Field>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={handleSaveBusiness}
                                disabled={savingBySection?.business || !settings?.permissions?.canEditBusiness}
                                className="mo-btn-primary flex items-center gap-2"
                                title={!settings?.permissions?.canEditBusiness ? "Only the owner can edit business settings" : ""}
                            >
                                <Save className="h-4 w-4" /> {savingBySection?.business ? "Saving..." : "Save Business"}
                            </button>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="notifications">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Notification Preferences</h2>
                        <p className="mo-text-secondary mb-6">Choose when you want to be notified</p>
                        <div className="space-y-4">
                            {Object.entries(notificationsDraft || {}).map(([key, enabled]) => {
                                const labels = {
                                    invoiceDue: { title: "Invoice Due Reminders", desc: "Get notified when invoices are about to be due" },
                                    paymentReceived: { title: "Payment Received", desc: "Get notified when a payment is received" },
                                    clientUpdates: { title: "Client Updates", desc: "Notifications when client info changes" },
                                    weeklyReport: { title: "Weekly Report", desc: "Receive a weekly financial summary every Monday" },
                                    systemAlerts: { title: "System Alerts", desc: "Important system and security notifications" },
                                };
                                const info = labels[key];
                                if (!info) return null;

                                return (
                                    <div key={key} className="flex items-center justify-between p-4 bg-[#111111] rounded-xl border border-[#2A2A2A]">
                                        <div>
                                            <p className="text-sm font-medium text-white">{info.title}</p>
                                            <p className="text-xs text-[#A0A0A0] mt-0.5">{info.desc}</p>
                                        </div>
                                        <button
                                            role="switch"
                                            aria-checked={enabled}
                                            onClick={() => setNotificationsDraft((prev) => ({ ...prev, [key]: !prev[key] }))}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enabled ? "bg-[#4CBB17]" : "bg-[#2A2A2A]"}`}
                                        >
                                            <span className={`inline-block h-4 w-4 transform rounded-full bg-black transition-transform ${enabled ? "translate-x-6" : "translate-x-1"}`} />
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={handleSaveNotifications}
                                disabled={savingBySection?.notifications}
                                className="mo-btn-primary flex items-center gap-2"
                            >
                                <Save className="h-4 w-4" /> {savingBySection?.notifications ? "Saving..." : "Save Preferences"}
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

                        <div className="mt-6 rounded-xl border border-[#CD1C1840] bg-[#CD1C180F] p-5">
                            <div className="flex items-start gap-3">
                                <div className="mt-0.5 rounded-full bg-[#CD1C1820] p-2">
                                    <AlertTriangle className="h-4 w-4 text-[#FF8A80]" />
                                </div>
                                <div className="flex-1">
                                    <h3 className="text-sm font-semibold text-white">Delete Account</h3>
                                    <p className="mt-1 text-sm text-[#A0A0A0]">
                                        This permanently deletes {businessDraft?.legalName || "your business account"} and removes
                                        its team, clients, invoices, transactions, documents, and related workspace records
                                        from the database.
                                    </p>
                                    <p className="mt-2 text-sm text-[#FF8A80]">
                                        Only the workspace owner can do this, and the team security code is required.
                                        After deletion, the next login goes back to onboarding because the old workspace no longer exists.
                                    </p>
                                </div>
                            </div>

                            <div className="mt-5 flex justify-end">
                                <button
                                    type="button"
                                    onClick={() => setDeleteDialogOpen(true)}
                                    disabled={!orgId || !userId}
                                    className="flex items-center gap-2 rounded-lg bg-[#CD1C18] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#B71C1C] disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <Trash2 className="h-4 w-4" />
                                    Delete Account
                                </button>
                            </div>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>

        <Dialog open={deleteDialogOpen} onOpenChange={handleDeleteDialogChange}>
            <DialogContent className="border-[#2A2A2A] bg-[#111111] text-white sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Permanently Delete Account</DialogTitle>
                    <DialogDescription className="text-[#A0A0A0]">
                        Enter the team security code to permanently delete this account from the database.
                        This action cannot be undone.
                    </DialogDescription>
                </DialogHeader>

                <div className="rounded-xl border border-[#CD1C1840] bg-[#CD1C1810] p-4 text-sm text-[#FFB4B1]">
                    Deleting this account removes the workspace, team members, clients, invoices, transactions,
                    documents, audit history, and related organization records. The next sign-in will be treated as
                    a fresh onboarding flow.
                </div>

                <div className="grid gap-2">
                    <label htmlFor="delete-account-security-code" className="text-sm font-medium text-[#A0A0A0]">
                        Team Security Code
                    </label>
                    <input
                        id="delete-account-security-code"
                        type="password"
                        value={deleteTeamActionCode}
                        onChange={(e) => setDeleteTeamActionCode(e.target.value)}
                        placeholder="Enter team security code"
                        style={inputStyle}
                        autoFocus
                    />
                </div>

                <DialogFooter className="gap-2 sm:justify-end">
                    <button
                        type="button"
                        onClick={() => handleDeleteDialogChange(false)}
                        className="mo-btn-secondary"
                        disabled={deletingAccount}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={handleDeleteAccount}
                        disabled={deletingAccount}
                        className="flex items-center justify-center gap-2 rounded-lg bg-[#CD1C18] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#B71C1C] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <Trash2 className="h-4 w-4" />
                        {deletingAccount ? "Deleting..." : "Delete Permanently"}
                    </button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
        </>
    );
}
