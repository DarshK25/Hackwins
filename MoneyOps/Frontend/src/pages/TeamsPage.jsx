import { useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Users, Plus, Mail, UserCheck, Crown, MoreHorizontal, Search } from "lucide-react";
import { toast } from "sonner";

const TEAM_MEMBERS = [
    { id: 1, name: "Paarth Kothari", email: "paarth@moneyops.io", role: "owner", status: "active", joined: "Jan 2024" },
    { id: 2, name: "Sarah Chen", email: "sarah@company.com", role: "admin", status: "active", joined: "Feb 2024" },
    { id: 3, name: "Raj Patel", email: "raj@company.com", role: "member", status: "active", joined: "Mar 2024" },
    { id: 4, name: "Alex Kim", email: "alex@company.com", role: "member", status: "pending", joined: "Invited" },
];

const ROLE_STYLES = {
    owner: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    admin: "bg-[#60A5FA20] text-[#60A5FA] border-[#60A5FA40]",
    member: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};

const STATUS_STYLES = {
    active: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    pending: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
};

export default function TeamsPage() {
    const [members, setMembers] = useState(TEAM_MEMBERS);
    const [searchQuery, setSearchQuery] = useState("");
    const [inviteEmail, setInviteEmail] = useState("");
    const [showInvite, setShowInvite] = useState(false);

    const filtered = members.filter(
        (m) =>
            !searchQuery ||
            m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            m.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleInvite = () => {
        if (!inviteEmail.trim() || !inviteEmail.includes("@")) {
            toast.error("Please enter a valid email address");
            return;
        }
        toast.success(`Invitation sent to ${inviteEmail}`);
        setInviteEmail("");
        setShowInvite(false);
    };

    const roleIcon = (role) => {
        if (role === "owner") return <Crown className="h-3.5 w-3.5" />;
        if (role === "admin") return <UserCheck className="h-3.5 w-3.5" />;
        return null;
    };

    const initials = (name) =>
        name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .toUpperCase();

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Team</h1>
                    <p className="mo-text-secondary mt-1">Manage your workspace team members</p>
                </div>
                <button
                    onClick={() => setShowInvite(true)}
                    className="mo-btn-primary flex items-center gap-2"
                >
                    <Plus className="h-4 w-4" /> Invite Member
                </button>
            </div>

            {/* ── Stats ─────────────────────────────────────────────────────── */}
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
                        {members.filter((m) => m.status === "active").length}
                    </div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Pending Invitations</p>
                        <Mail className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-[#FFB300]">
                        {members.filter((m) => m.status === "pending").length}
                    </div>
                </div>
            </div>

            {/* ── Invite Box ────────────────────────────────────────────────── */}
            {showInvite && (
                <div className="mo-card border-[#4CBB1740]">
                    <h2 className="mo-h2 mb-4">Invite New Member</h2>
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
                        <button onClick={handleInvite} className="mo-btn-primary flex items-center gap-2">
                            <Mail className="h-4 w-4" /> Send Invite
                        </button>
                        <button onClick={() => setShowInvite(false)} className="mo-btn-secondary">
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* ── Search ────────────────────────────────────────────────────── */}
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

            {/* ── Members List ──────────────────────────────────────────────── */}
            <div className="mo-card !p-0 overflow-hidden">
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
                                        <p className="text-sm font-semibold text-white">{member.name}</p>
                                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md border font-medium ${ROLE_STYLES[member.role]}`}>
                                            {roleIcon(member.role)}
                                            {member.role}
                                        </span>
                                    </div>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">{member.email}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="text-right hidden sm:block">
                                    <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded-md border font-medium ${STATUS_STYLES[member.status]}`}>
                                        {member.status}
                                    </span>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Joined {member.joined}</p>
                                </div>
                                {member.role !== "owner" && (
                                    <button className="p-1.5 rounded-lg text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] transition-colors">
                                        <MoreHorizontal className="h-4 w-4" />
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
