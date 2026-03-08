import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Save, User, Building, Bell, Shield } from "lucide-react";
import { useUser, useAuth } from "@clerk/clerk-react";
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
        companyName: "",
        gstin: "",
        businessType: "",
        address: "",
        website: "",
        pincode: "",
        panNumber: "",
        stateOfRegistration: "",
    });

    const [notifications, setNotifications] = useState({
        invoiceDue: true,
        paymentReceived: true,
        clientUpdates: false,
        weeklyReport: true,
        systemAlerts: true,
    });

    const [loading, setLoading] = useState(true);

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
                const response = await fetch(`/api/org/my`, {
                    headers: {
                        "X-User-Id": userId
                    }
                });
                if (response.ok) {
                    const result = await response.json();
                    const data = result.data;
                    if (!data) return;
                    setBusiness({
                        id: data.id,
                        companyName: data.legalName || "",
                        gstin: data.gstin || "",
                        businessType: data.businessType || "",
                        address: data.registeredAddress || "",
                        website: data.website || "",
                        pincode: data.pincode || "", 
                        panNumber: data.panNumber || "",
                        stateOfRegistration: data.stateOfRegistration || "",
                    });
                }
            } catch (error) {
                console.error("Failed to fetch business data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchBusinessData();
    }, [user, orgId, userId]);

    const handleSave = async (section) => {
        try {
            if (section === "Business" && userId) {
                // If orgId is not yet available, we can use the 'my' endpoint if the backend supports PUT /my, 
                // but usually we have an orgId by this point if we loaded data.
                const targetId = orgId || business.id; 
                if (!targetId) throw new Error("Organization ID not found");

                const response = await fetch(`/api/org/${targetId}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "X-User-Id": userId
                    },
                    body: JSON.stringify({
                        legalName: business.companyName,
                        gstin: business.gstin,
                        businessType: business.businessType,
                        registeredAddress: business.address,
                        website: business.website,
                        pincode: business.pincode,
                        panNumber: business.panNumber,
                        stateOfRegistration: business.stateOfRegistration
                    })
                });
                if (!response.ok) throw new Error("Failed to update business");
            }
            toast.success(`${section} settings saved`);
        } catch (error) {
            toast.error(error.message);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
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

                {/* ── Profile Tab ─────────────────────────────────────────────── */}
                <TabsContent value="profile">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Profile Information</h2>
                        <p className="mo-text-secondary mb-6">Update your personal information</p>
                        <div className="grid gap-4 md:grid-cols-2">
                            {[
                                { label: "First Name", id: "settings-first-name", field: "firstName", placeholder: "John" },
                                { label: "Last Name", id: "settings-last-name", field: "lastName", placeholder: "Doe" },
                                { label: "Email", id: "settings-email", field: "email", type: "email", placeholder: "john@example.com" },
                                { label: "Phone", id: "settings-phone", field: "phone", type: "tel", placeholder: "+91 98765 43210" },
                                { label: "Professional Title", id: "settings-title", field: "professionalTitle", placeholder: "Freelance Consultant", colSpan: true },
                            ].map(({ label, id, field, type, placeholder, colSpan }) => (
                                <div key={id} className={`grid gap-2 ${colSpan ? "md:col-span-2" : ""}`}>
                                    <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0]">{label}</label>
                                    <input
                                        id={id}
                                        type={type || "text"}
                                        value={profile[field]}
                                        onChange={(e) => setProfile((p) => ({ ...p, [field]: e.target.value }))}
                                        placeholder={placeholder}
                                        style={inputStyle}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={() => handleSave("Profile")}
                                className="mo-btn-primary flex items-center gap-2"
                            >
                                <Save className="h-4 w-4" /> Save Profile
                            </button>
                        </div>
                    </div>
                </TabsContent>

                {/* ── Business Tab ─────────────────────────────────────────────── */}
                <TabsContent value="business">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Business Information</h2>
                        <p className="mo-text-secondary mb-6">Configure your business details for invoices</p>
                        <div className="grid gap-4 md:grid-cols-2">
                            {[
                                { label: "Company Name", id: "biz-company", field: "companyName", placeholder: "Acme Corp", colSpan: true },
                                { label: "GST Number", id: "biz-gstin", field: "gstin", placeholder: "22AAAAA0000A1Z5" },
                                { label: "PAN Number", id: "biz-pan", field: "panNumber", placeholder: "ABCDE1234F" },
                                { label: "Business Type", id: "biz-type", field: "businessType", placeholder: "Sole Proprietor" },
                                { label: "State", id: "biz-state", field: "stateOfRegistration", placeholder: "Maharashtra" },
                                { label: "Business Address", id: "biz-address", field: "address", placeholder: "123 Main St, City", colSpan: true },
                                { label: "Website", id: "biz-website", field: "website", type: "url", placeholder: "https://yourdomain.com" },
                                { label: "Pincode", id: "biz-pincode", field: "pincode", placeholder: "400001" },
                            ].map(({ label, id, field, type, placeholder, colSpan }) => (
                                <div key={id} className={`grid gap-2 ${colSpan ? "md:col-span-2" : ""}`}>
                                    <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0]">{label}</label>
                                    <input
                                        id={id}
                                        type={type || "text"}
                                        value={business[field]}
                                        onChange={(e) => setBusiness((p) => ({ ...p, [field]: e.target.value }))}
                                        placeholder={placeholder}
                                        style={inputStyle}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={() => handleSave("Business")}
                                className="mo-btn-primary flex items-center gap-2"
                            >
                                <Save className="h-4 w-4" /> Save Business
                            </button>
                        </div>
                    </div>
                </TabsContent>

                {/* ── Notifications Tab ────────────────────────────────────────── */}
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
                                            id={`notif-${key}`}
                                            role="switch"
                                            aria-checked={enabled}
                                            onClick={() => setNotifications((prev) => ({ ...prev, [key]: !prev[key] }))}
                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${enabled ? "bg-[#4CBB17]" : "bg-[#2A2A2A]"
                                                }`}
                                        >
                                            <span
                                                className={`inline-block h-4 w-4 transform rounded-full bg-black transition-transform ${enabled ? "translate-x-6" : "translate-x-1"
                                                    }`}
                                            />
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button
                                onClick={() => handleSave("Notifications")}
                                className="mo-btn-primary flex items-center gap-2"
                            >
                                <Save className="h-4 w-4" /> Save Preferences
                            </button>
                        </div>
                    </div>
                </TabsContent>

                {/* ── Security Tab ─────────────────────────────────────────────── */}
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
