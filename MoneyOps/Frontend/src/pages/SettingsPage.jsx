import { useState } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Save } from "lucide-react";

export default function SettingsPage() {
    const [profile, setProfile] = useState({
        name: "abc",
        email: "abc@example.com",
        company: "LedgerTalk Inc.",
        phone: "+91 98765 43210",
    });

    const [preferences, setPreferences] = useState({
        currency: "INR",
        timezone: "Asia/Kolkata",
        notifications: true,
    });

    const handleSaveProfile = () => {
        toast.success("Profile updated successfully");
    };

    const handleSavePreferences = () => {
        toast.success("Preferences saved successfully");
    };

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div>
                <h1 className="text-3xl font-bold">Settings</h1>
                <p className="text-slate-500 text-sm mt-1">
                    Manage your account and preferences
                </p>
            </div>

            {/* ── Tabs ───────────────────────────────────────────────────────── */}
            <Tabs defaultValue="profile" className="w-full">
                <TabsList>
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="preferences">Preferences</TabsTrigger>
                    <TabsTrigger value="billing">Billing</TabsTrigger>
                </TabsList>

                {/* Profile tab */}
                <TabsContent value="profile" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Profile Information</CardTitle>
                            <CardDescription>
                                Update your personal and business details
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-2">
                                <Label htmlFor="profile-name">Full Name</Label>
                                <Input
                                    id="profile-name"
                                    value={profile.name}
                                    onChange={(e) =>
                                        setProfile((p) => ({ ...p, name: e.target.value }))
                                    }
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="profile-email">Email</Label>
                                <Input
                                    id="profile-email"
                                    type="email"
                                    value={profile.email}
                                    onChange={(e) =>
                                        setProfile((p) => ({ ...p, email: e.target.value }))
                                    }
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="profile-company">Company Name</Label>
                                <Input
                                    id="profile-company"
                                    value={profile.company}
                                    onChange={(e) =>
                                        setProfile((p) => ({ ...p, company: e.target.value }))
                                    }
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="profile-phone">Phone Number</Label>
                                <Input
                                    id="profile-phone"
                                    type="tel"
                                    value={profile.phone}
                                    onChange={(e) =>
                                        setProfile((p) => ({ ...p, phone: e.target.value }))
                                    }
                                />
                            </div>
                            <Button onClick={handleSaveProfile}>
                                <Save className="mr-2 h-4 w-4" /> Save Changes
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Preferences tab */}
                <TabsContent value="preferences" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>App Preferences</CardTitle>
                            <CardDescription>
                                Customize your LedgerTalk experience
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-2">
                                <Label htmlFor="pref-currency">Default Currency</Label>
                                <Input
                                    id="pref-currency"
                                    value={preferences.currency}
                                    onChange={(e) =>
                                        setPreferences((p) => ({ ...p, currency: e.target.value }))
                                    }
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="pref-timezone">Timezone</Label>
                                <Input
                                    id="pref-timezone"
                                    value={preferences.timezone}
                                    onChange={(e) =>
                                        setPreferences((p) => ({
                                            ...p,
                                            timezone: e.target.value,
                                        }))
                                    }
                                />
                            </div>
                            <Button onClick={handleSavePreferences}>
                                <Save className="mr-2 h-4 w-4" /> Save Preferences
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Billing tab */}
                <TabsContent value="billing" className="mt-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Billing &amp; Subscription</CardTitle>
                            <CardDescription>Manage your subscription plan</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="p-6 bg-slate-50 rounded-lg text-center border border-dashed">
                                <p className="text-slate-400 text-sm">
                                    Billing management coming soon.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
