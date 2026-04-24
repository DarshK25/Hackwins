import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { toast } from "sonner";

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
    const { userId, orgId, complete } = useOnboardingStatus();

    const [settings, setSettings] = useState(null);
    const [loading, setLoading] = useState(true);
    const [savingBySection, setSavingBySection] = useState({});

    const [profileDraft, setProfileDraft] = useState(null);
    const [businessDraft, setBusinessDraft] = useState(null);
    const [notificationsDraft, setNotificationsDraft] = useState(null);

    const fetchSettings = useCallback(async () => {
        if (!userId || !orgId || !complete) return;
        try {
            const res = await fetch("/api/settings", {
                headers: {
                    "X-User-Id": userId,
                    "X-Org-Id": orgId,
                },
            });
            if (!res.ok) throw new Error("Failed to load settings");
            const json = await res.json();
            const data = json.data ?? json;
            setSettings(data);
            setProfileDraft(data.profile ? { ...data.profile } : null);
            setBusinessDraft(data.business ? { ...data.business } : null);
            setNotificationsDraft(data.notifications ? { ...data.notifications } : null);
        } catch (err) {
            console.error("Failed to fetch settings:", err);
            toast.error("Failed to load settings");
        } finally {
            setLoading(false);
        }
    }, [userId, orgId, complete]);

    useEffect(() => {
        if (complete) {
            fetchSettings();
        }
    }, [complete, fetchSettings]);

    const updateSettings = useCallback(async (section) => {
        if (!userId || !orgId) return;
        setSavingBySection((prev) => ({ ...prev, [section]: true }));
        try {
            let body = { section };
            if (section === "profile") body.profile = profileDraft;
            if (section === "business") body.business = businessDraft;
            if (section === "notifications") body.notifications = notificationsDraft;

            const res = await fetch("/api/settings", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": userId,
                    "X-Org-Id": orgId,
                },
                body: JSON.stringify(body),
            });
            const json = await res.json().catch(() => ({}));
            if (!res.ok) {
                throw new Error(json.message || "Failed to update settings");
            }
            const data = json.data ?? json;
            setSettings(data);
            setProfileDraft(data.profile ? { ...data.profile } : null);
            setBusinessDraft(data.business ? { ...data.business } : null);
            setNotificationsDraft(data.notifications ? { ...data.notifications } : null);
            toast.success(`${section.charAt(0).toUpperCase() + section.slice(1)} settings saved`);
        } catch (err) {
            toast.error(err.message);
            throw err;
        } finally {
            setSavingBySection((prev) => ({ ...prev, [section]: false }));
        }
    }, [userId, orgId, profileDraft, businessDraft, notificationsDraft]);

    return (
        <SettingsContext.Provider
            value={{
                settings,
                loading,
                savingBySection,
                refreshSettings: fetchSettings,
                profileDraft,
                setProfileDraft,
                businessDraft,
                setBusinessDraft,
                notificationsDraft,
                setNotificationsDraft,
                updateSettings,
            }}
        >
            {children}
        </SettingsContext.Provider>
    );
}

export function useSettings() {
    const context = useContext(SettingsContext);
    if (!context) {
        throw new Error("useSettings must be used within a SettingsProvider");
    }
    return context;
}
