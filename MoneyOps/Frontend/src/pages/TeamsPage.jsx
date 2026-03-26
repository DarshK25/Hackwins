import { useState, useEffect } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Users, Plus, Mail, UserCheck, Crown, MoreHorizontal, Search, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { getRememberedTeamSecurityCode, rememberTeamSecurityCode } from "@/lib/teamSecurityCode";

const ROLE_STYLES = {
    OWNER: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    ADMIN: "bg-[#60A5FA20] text-[#60A5FA] border-[#60A5FA40]",
    STAFF: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
    MEMBER: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};

const STATUS_STYLES = {
    ACTIVE: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    PENDING: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
};

export default function TeamsPage() {
    const { user } = useUser();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    const [members, setMembers] = useState([]);
    const [orgName, setOrgName] = useState("Loading...");
    const [searchQuery, setSearchQuery] = useState("");
    const [inviteEmail, setInviteEmail] = useState("");
    const [showInvite, setShowInvite] = useState(false);
    const [loading, setLoading] = useState(true);
    const [generatedCode, setGeneratedCode] = useState("");
    const [copied, setCopied] = useState(false);
    const [teamActionCode, setTeamActionCode] = useState("");
    const [teamCodeToSet, setTeamCodeToSet] = useState("");
    const [oldTeamCode, setOldTeamCode] = useState("");
    const [savingTeamCode, setSavingTeamCode] = useState(false);
    const [currentUserRole, setCurrentUserRole] = useState(null);
    const [teamCodeConfigured, setTeamCodeConfigured] = useState(false);
    const isOwner = currentUserRole === "OWNER";

    const fetchMembers = async () => {
        try {
            if (!internalOrgId) return;

            // Fetch Members
            const memRes = await fetch("/api/users?orgId=" + internalOrgId, {
                headers: {
                    "X-Org-Id": internalOrgId,
                    "X-User-Id": internalUserId
                }
            });
            const memData = await memRes.json();
            setMembers(memData);

            // Find current user and set their role
            const currentUser = memData.find(m => m.id === internalUserId);
            if (currentUser) {
                setCurrentUserRole(currentUser.role);
            }

            // Fetch Org Name
            const orgRes = await fetch(`/api/org/${internalOrgId}`, {
                headers: { "X-User-Id": internalUserId }
            });
            if (orgRes.ok) {
                const result = await orgRes.json();
                const orgData = result.data;
                setOrgName(orgData.legalName || "Organization");
                setTeamCodeConfigured(Boolean(orgData.teamSecurityCodeConfigured));
            }
        } catch (error) {
            console.error("Failed to fetch data:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (internalOrgId) fetchMembers();
    }, [internalOrgId, internalUserId]);

    useEffect(() => {
        if (!internalOrgId) return;
        const remembered = getRememberedTeamSecurityCode(internalOrgId);
        if (remembered) {
            setTeamActionCode(remembered);
        }
    }, [internalOrgId]);

    const handleInvite = async () => {
        if (!inviteEmail.trim() || !inviteEmail.includes("@")) {
            toast.error("Please enter a valid email address");
            return;
        }
        if (!teamActionCode.trim()) {
            toast.error("Team security code is required");
            return;
        }

        try {
            const response = await fetch("/api/invites", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Org-Id": internalOrgId,
                    "X-User-Id": internalUserId
                },
                body: JSON.stringify({
                    email: inviteEmail,
                    role: "STAFF",
                    teamActionCode
                })
            });

            if (!response.ok) throw new Error("Failed to send invite");

            const data = await response.json();
            setGeneratedCode(data.token);
            toast.success(`Invitation code generated for ${inviteEmail}`);
            rememberTeamSecurityCode(internalOrgId, teamActionCode);
            setInviteEmail("");
        } catch (error) {
            toast.error(error.message);
        }
    };

    const handleSetTeamCode = async () => {
        if (!internalOrgId) return;
        if (!teamCodeToSet.trim()) {
            toast.error("Team security code is required");
            return;
        }
        setSavingTeamCode(true);
        try {
            const response = await fetch(`/api/org/${internalOrgId}/team-security-code`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": internalUserId
                },
                body: JSON.stringify({
                    teamActionCode: teamCodeToSet,
                    oldTeamActionCode: oldTeamCode
                })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data?.message || "Failed to save team security code");
            toast.success("Team security code updated");
            setTeamActionCode(teamCodeToSet);
            rememberTeamSecurityCode(internalOrgId, teamCodeToSet);
            setTeamCodeConfigured(true);
            setOldTeamCode("");
            setTeamCodeToSet("");
        } catch (error) {
            toast.error(error?.message || "Failed to save team security code");
        } finally {
            setSavingTeamCode(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(generatedCode);
        setCopied(true);
        toast.success("Code copied to clipboard!");
        setTimeout(() => setCopied(false), 2000);
    };

    const filtered = Array.isArray(members) ? members.filter(
        (m) =>
            !searchQuery ||
            m.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            m.email?.toLowerCase().includes(searchQuery.toLowerCase())
    ) : [];

    const roleIcon = (role) => {
        if (role === "OWNER") return <Crown className="h-3.5 w-3.5" />;
        if (role === "ADMIN") return <UserCheck className="h-3.5 w-3.5" />;
        return null;
    };

    const initials = (name) =>
        name
            ? name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .toUpperCase()
            : "??";

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Team</h1>
                    <p className="mo-text-secondary mt-1">Manage your workspace team members</p>
                </div>
                {isOwner && (
                    <button
                        onClick={() => {
                            setShowInvite(true);
                            setGeneratedCode("");
                        }}
                        className="mo-btn-primary flex items-center gap-2"
                    >
                        <Plus className="h-4 w-4" /> Invite Member
                    </button>
                )}
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-3">
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Members</p>
                        <Users className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">{members.length}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Active</p>
                        <UserCheck className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-[#4CBB17]">
                        {members.filter((m) => m.status === "ACTIVE").length}
                    </div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Organization</p>
                        <Mail className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-xl font-bold text-[#FFB300] truncate">
                        {orgName}
                    </div>
                </div>
            </div>

            {/* Team Security Code (Owner only) */}
            {isOwner && (
            <div className="mo-card border-[#4CBB1740]">
                <h2 className="mo-h2 mb-2">Team Security Code</h2>
                <p className="mo-text-secondary mb-4 text-sm">
                    Owner sets a shared code used to create invoices and add clients. Invited members receive it via email.
                </p>
                <div className="mb-4 rounded-lg border border-[#2A2A2A] bg-[#111111] px-4 py-3 text-sm">
                    <p className="text-white">
                        Status:{" "}
                        <span className={teamCodeConfigured ? "text-[#4CBB17]" : "text-[#FFB300]"}>
                            {teamCodeConfigured ? "Configured" : "Not configured"}
                        </span>
                    </p>
                    <p className="mt-1 text-[#A0A0A0]">
                        The raw code is never returned from the database because only a secure hash is stored.
                    </p>
                </div>
                <div className="grid gap-3">
                    <div className="grid gap-1">
                        <label className="text-sm text-[#A0A0A0]">{teamCodeConfigured ? "New Code" : "Set Code"}</label>
                        <input
                            type="password"
                            value={teamCodeToSet}
                            onChange={(e) => setTeamCodeToSet(e.target.value)}
                            placeholder="Enter team security code"
                            className="px-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                            style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                        />
                    </div>
                    {teamCodeConfigured && (
                        <div className="grid gap-1">
                            <label className="text-sm text-[#A0A0A0]">Old Code (required to update)</label>
                            <input
                                type="password"
                                value={oldTeamCode}
                                onChange={(e) => setOldTeamCode(e.target.value)}
                                placeholder="Enter old code"
                                className="px-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                                style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                            />
                        </div>
                    )}
                    <button
                        onClick={handleSetTeamCode}
                        disabled={savingTeamCode}
                        className="mo-btn-primary"
                    >
                        {savingTeamCode ? "Saving..." : teamCodeConfigured ? "Update Team Code" : "Set Team Code"}
                    </button>
                </div>
            </div>
            )}

            {/* Invite Box */}
            {isOwner && showInvite && (
                <div className="mo-card border-[#4CBB1740] animate-in fade-in slide-in-from-top-4 duration-300">
                    <h2 className="mo-h2 mb-4">Invite New Member</h2>
                    
                    {!generatedCode ? (
                        <div className="flex gap-3">
                            <input
                                type="email"
                                placeholder="colleague@company.com"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                                className="flex-1 px-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                                style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                            />
                            <input
                                type="password"
                                placeholder="Team security code"
                                value={teamActionCode}
                                onChange={(e) => setTeamActionCode(e.target.value)}
                                className="flex-1 px-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                                style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                            />
                            <button onClick={handleInvite} className="mo-btn-primary flex items-center gap-2">
                                <Mail className="h-4 w-4" /> Generate Code
                            </button>
                            <button onClick={() => setShowInvite(false)} className="mo-btn-secondary">
                                Cancel
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-sm text-[#A0A0A0]">Share this code with your team member. They can enter it during onboarding.</p>
                            <div className="flex items-center gap-3 p-4 rounded-xl border border-[#2A2A2A] bg-[#111111]">
                                <code className="flex-1 text-2xl font-mono font-bold tracking-widest text-[#4CBB17] text-center">
                                    {generatedCode}
                                </code>
                                <button
                                    onClick={copyToClipboard}
                                    className="p-3 rounded-lg bg-[#2A2A2A] hover:bg-[#3A3A3A] text-white transition-all active:scale-95"
                                >
                                    {copied ? <Check className="h-5 w-5 text-[#4CBB17]" /> : <Copy className="h-5 w-5" />}
                                </button>
                            </div>
                            <div className="flex justify-end">
                                <button onClick={() => setShowInvite(false)} className="mo-btn-primary">
                                    Done
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A0A0A0]" />
                <input
                    placeholder="Search members…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                    style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                />
            </div>

            {/* Members List */}
            <div className="mo-card !p-0 overflow-hidden">
                {loading ? (
                    <div className="p-8 text-center text-[#A0A0A0]">Loading members...</div>
                ) : filtered.length === 0 ? (
                    <div className="p-8 text-center text-[#A0A0A0]">No members found.</div>
                ) : (
                    <div className="divide-y divide-[#2A2A2A]">
                        {filtered.map((member) => (
                            <div key={member.id} className="flex items-center justify-between p-4 hover:bg-[#111111] transition-colors">
                                <div className="flex items-center gap-4">
                                    <Avatar className="h-10 w-10 bg-[#2A2A2A]">
                                        <AvatarFallback className="bg-[#4CBB1720] text-[#4CBB17] font-semibold text-sm">
                                            {initials(member.name)}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <p className="text-sm font-semibold text-white">{member.name || "Unnamed User"}</p>
                                            <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md border font-bold ${ROLE_STYLES[member.role] || ROLE_STYLES.MEMBER}`}>
                                                {roleIcon(member.role)}
                                                {member.role}
                                            </span>
                                        </div>
                                        <p className="text-xs text-[#A0A0A0] mt-0.5">{member.email}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <div className="text-right hidden sm:block">
                                        <span className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-md border font-bold ${STATUS_STYLES[member.status] || STATUS_STYLES.ACTIVE}`}>
                                            {member.status}
                                        </span>
                                        <p className="text-xs text-[#A0A0A0] mt-0.5">Joined {new Date(member.createdAt).toLocaleDateString()}</p>
                                    </div>
                                    {member.role !== "OWNER" && (
                                        <button className="p-1.5 rounded-lg text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] transition-colors">
                                            <MoreHorizontal className="h-4 w-4" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
