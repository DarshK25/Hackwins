import { useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/clerk-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
    Building2,
    Loader2,
    Mail,
    RefreshCw,
    Search,
    Shield,
    Trash2,
    UserPlus,
    Users,
    X,
} from "lucide-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { getTeamSecurityAttemptState } from "@/lib/teamSecurityAttempts";

const ROLE_OPTIONS = ["ADMIN", "MANAGER", "STAFF", "VIEWER"];

const ROLE_STYLES = {
    OWNER: "border-[#4CBB1740] bg-[#4CBB1720] text-[#4CBB17]",
    ADMIN: "border-[#60A5FA40] bg-[#60A5FA20] text-[#60A5FA]",
    MANAGER: "border-[#FFB30040] bg-[#FFB30020] text-[#FFB300]",
    STAFF: "border-[#A855F740] bg-[#A855F720] text-[#C084FC]",
    VIEWER: "border-[#A0A0A040] bg-[#A0A0A020] text-[#D4D4D4]",
};

const STATUS_STYLES = {
    ACTIVE: "border-[#4CBB1740] bg-[#4CBB1720] text-[#4CBB17]",
    PENDING: "border-[#FFB30040] bg-[#FFB30020] text-[#FFB300]",
    DISABLED: "border-[#F8717140] bg-[#F8717120] text-[#F87171]",
};

function initials(name) {
    if (!name) {
        return "??";
    }

    return name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase();
}

function formatDate(value) {
    if (!value) {
        return "--";
    }

    return new Date(value).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });
}

async function parseApiResponse(response, fallbackMessage) {
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => null);
        return payload?.message || payload?.error || payload?.data?.message || fallbackMessage;
    }

    const text = await response.text().catch(() => "");
    return text || fallbackMessage;
}

function LoadingSkeleton() {
    return (
        <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
                {[1, 2, 3].map((item) => (
                    <div key={item} className="mo-stat-card animate-pulse">
                        <div className="h-4 w-24 rounded bg-[#202020]" />
                        <div className="mt-4 h-8 w-20 rounded bg-[#202020]" />
                    </div>
                ))}
            </div>
            <div className="mo-card animate-pulse">
                <div className="h-6 w-48 rounded bg-[#202020]" />
                <div className="mt-6 space-y-3">
                    {[1, 2, 3, 4].map((item) => (
                        <div key={item} className="h-16 rounded-xl bg-[#141414]" />
                    ))}
                </div>
            </div>
        </div>
    );
}

export default function TeamsPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { loading: onboardingLoading, userId, orgId } = useOnboardingStatus();

    const [organization, setOrganization] = useState(null);
    const [members, setMembers] = useState([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteForm, setInviteForm] = useState({ email: "", role: "STAFF", teamActionCode: "" });
    const [inviteResult, setInviteResult] = useState(null);
    const [sendingInvite, setSendingInvite] = useState(false);
    const [inviteCodeAttempts, setInviteCodeAttempts] = useState(0);
    const [removingMemberId, setRemovingMemberId] = useState(null);
    const [updatingRoleId, setUpdatingRoleId] = useState(null);
    const [securityCodeForm, setSecurityCodeForm] = useState({
        oldTeamActionCode: "",
        teamActionCode: "",
    });
    const [savingSecurityCode, setSavingSecurityCode] = useState(false);

    const hasContext = useMemo(() => Boolean(orgId && (userId || user?.id)), [orgId, userId, user?.id]);
    const currentUserId = userId || user?.id || null;

    const currentUserRole = useMemo(() => {
        return members.find((member) => member.id === userId)?.role || null;
    }, [members, userId]);

    const canManageMembers = currentUserRole === "OWNER" || currentUserRole === "ADMIN";
    const isOwner = currentUserRole === "OWNER";

    const filteredMembers = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) {
            return members;
        }

        return members.filter((member) => {
            return (
                member.name?.toLowerCase().includes(query) ||
                member.email?.toLowerCase().includes(query) ||
                member.role?.toLowerCase().includes(query)
            );
        });
    }, [members, searchQuery]);

    useEffect(() => {
        if (!onboardingLoading && hasContext) {
            loadData();
        } else if (!onboardingLoading && !hasContext) {
            setLoading(false);
            setError("");
        }
    }, [onboardingLoading, hasContext]);

    async function buildHeaders(extra = {}) {
        const token = await getToken();
        return {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(currentUserId ? { "X-User-Id": currentUserId } : {}),
            ...(orgId ? { "X-Org-Id": orgId } : {}),
            ...extra,
        };
    }

    async function loadData() {
        if (!orgId) {
            setLoading(false);
            setError("Organization context is missing.");
            return;
        }

        try {
            setLoading(true);
            setError("");

            const headers = await buildHeaders();
            const membersUrl = `/api/teams/members?orgId=${encodeURIComponent(orgId)}`;

            const [organizationResponse, membersResponse] = await Promise.all([
                fetch("/api/teams/organization", { headers }),
                fetch(membersUrl, { headers }),
            ]);

            if (!organizationResponse.ok) {
                throw new Error(await parseApiResponse(organizationResponse, "Failed to load organization"));
            }
            if (!membersResponse.ok) {
                throw new Error(await parseApiResponse(membersResponse, "Failed to load team members"));
            }

            const organizationPayload = await organizationResponse.json();
            const membersPayload = await membersResponse.json();

            setOrganization(organizationPayload?.data || null);
            setMembers(Array.isArray(membersPayload?.data) ? membersPayload.data : []);
        } catch (requestError) {
            console.error("Failed to load team data", requestError);
            setOrganization(null);
            setMembers([]);
            setError(requestError.message || "Failed to load team data");
        } finally {
            setLoading(false);
        }
    }

    async function handleInvite() {
        if (!inviteForm.email.trim() || !inviteForm.email.includes("@")) {
            toast.error("Enter a valid email address");
            return;
        }
        if (!inviteForm.teamActionCode.trim()) {
            toast.error("Team security code is required to send invites");
            return;
        }

        try {
            setSendingInvite(true);
            const headers = await buildHeaders({ "Content-Type": "application/json" });
            const response = await fetch("/api/teams/invite", {
                method: "POST",
                headers,
                body: JSON.stringify(inviteForm),
            });

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to send invite"));
            }

            const payload = await response.json();
            const invite = payload?.data || null;
            setInviteResult(invite);
            setInviteForm({ email: "", role: "STAFF", teamActionCode: "" });
            setInviteCodeAttempts(0);
            toast.success("Invite sent successfully");
            await loadData();
        } catch (requestError) {
            console.error("Failed to send invite", requestError);
            const attempt = getTeamSecurityAttemptState(requestError, inviteCodeAttempts);
            if (attempt.isSecurityCodeError) {
                toast.error(attempt.message);
                setInviteForm((current) => ({ ...current, teamActionCode: "" }));
                if (attempt.shouldCancel) {
                    closeInviteModal();
                    setInviteCodeAttempts(0);
                } else {
                    setInviteCodeAttempts(attempt.nextAttempts);
                }
                return;
            }
            toast.error(requestError.message || "Failed to send invite");
        } finally {
            setSendingInvite(false);
        }
    }

    async function handleSaveSecurityCode() {
        const newCode = securityCodeForm.teamActionCode.trim();
        const oldCode = securityCodeForm.oldTeamActionCode.trim();
        const hasExistingCode = Boolean(organization?.teamSecurityCodeConfigured);

        if (!newCode) {
            toast.error("Team security code is required");
            return;
        }
        if (newCode.length < 4) {
            toast.error("Team security code must be at least 4 characters");
            return;
        }
        if (hasExistingCode && !oldCode) {
            toast.error("Current team security code is required to update it");
            return;
        }

        try {
            setSavingSecurityCode(true);
            const headers = await buildHeaders({ "Content-Type": "application/json" });
            const response = await fetch(`/api/org/${orgId}/team-security-code`, {
                method: "PUT",
                headers,
                body: JSON.stringify({
                    teamActionCode: newCode,
                    oldTeamActionCode: hasExistingCode ? oldCode : undefined,
                }),
            });

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to update team security code"));
            }

            setSecurityCodeForm({ oldTeamActionCode: "", teamActionCode: "" });
            setOrganization((current) =>
                current
                    ? { ...current, teamSecurityCodeConfigured: true }
                    : { teamSecurityCodeConfigured: true }
            );
            toast.success(hasExistingCode ? "Team security code updated" : "Team security code configured");
            await loadData();
        } catch (requestError) {
            console.error("Failed to save team security code", requestError);
            toast.error(requestError.message || "Failed to save team security code");
        } finally {
            setSavingSecurityCode(false);
        }
    }

    async function handleRoleChange(memberId, role) {
        try {
            setUpdatingRoleId(memberId);
            const headers = await buildHeaders({ "Content-Type": "application/json" });
            const response = await fetch(`/api/teams/members/${memberId}/role`, {
                method: "PUT",
                headers,
                body: JSON.stringify({ role }),
            });

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to update team role"));
            }

            const payload = await response.json();
            const updatedMember = payload?.data;
            setMembers((current) =>
                current.map((member) => (member.id === memberId ? { ...member, ...updatedMember } : member))
            );
            toast.success("Role updated");
        } catch (requestError) {
            console.error("Failed to update role", requestError);
            toast.error(requestError.message || "Failed to update role");
            await loadData();
        } finally {
            setUpdatingRoleId(null);
        }
    }

    async function handleRemoveMember(member) {
        if (!window.confirm(`Remove ${member.name || member.email} from the organization?`)) {
            return;
        }

        try {
            setRemovingMemberId(member.id);
            const headers = await buildHeaders();
            const response = await fetch(`/api/teams/members/${member.id}`, {
                method: "DELETE",
                headers,
            });

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to remove team member"));
            }

            toast.success("Team member removed");
            setMembers((current) => current.filter((currentMember) => currentMember.id !== member.id));
        } catch (requestError) {
            console.error("Failed to remove member", requestError);
            toast.error(requestError.message || "Failed to remove team member");
        } finally {
            setRemovingMemberId(null);
        }
    }

    function closeInviteModal() {
        setInviteOpen(false);
        setInviteResult(null);
        setInviteForm({
            email: "",
            role: "STAFF",
            teamActionCode: "",
        });
        setInviteCodeAttempts(0);
    }

    function copyInviteLink(token) {
        const inviteLink = `${window.location.origin}/invite/${token}`;
        navigator.clipboard.writeText(inviteLink);
        toast.success("Invite link copied");
    }

    const activeMembers = members.filter((member) => member.status === "ACTIVE").length;
    const pendingMembers = members.filter((member) => member.status === "PENDING").length;
    const organizationName =
        organization?.tradingName || organization?.legalName || "Your organization";

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="mo-h1">Team</h1>
                    <p className="mo-text-secondary mt-1">
                        Manage organization members, roles, and workspace invitations.
                    </p>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={loadData}
                        disabled={loading || onboardingLoading || !hasContext}
                        className="mo-btn-secondary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </button>

                    {canManageMembers ? (
                        <button
                            onClick={() => {
                                setInviteResult(null);
                                setInviteForm({ email: "", role: "STAFF", teamActionCode: "" });
                                setInviteCodeAttempts(0);
                                setInviteOpen(true);
                            }}
                            className="mo-btn-primary flex items-center gap-2"
                        >
                            <UserPlus className="h-4 w-4" />
                            Invite Member
                        </button>
                    ) : null}
                </div>
            </div>

            {loading || onboardingLoading ? <LoadingSkeleton /> : null}

            {!loading && !onboardingLoading && !hasContext ? (
                <div className="mo-card rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-6 py-10 text-center">
                    <Building2 className="mx-auto mb-4 h-12 w-12 text-[#2F2F2F]" />
                    <div className="text-lg font-semibold text-white">Organization context is not ready</div>
                    <div className="mt-2 text-sm text-[#A0A0A0]">
                        The Teams page cannot load until onboarding resolves your internal user and organization IDs.
                    </div>
                </div>
            ) : null}

            {!loading && !onboardingLoading && hasContext && error ? (
                <div className="mo-card rounded-2xl border border-[#F8717140] bg-[#111111] px-6 py-10 text-center">
                    <div className="text-lg font-semibold text-white">Failed to load team data</div>
                    <div className="mt-2 text-sm text-[#A0A0A0]">{error}</div>
                    <button onClick={loadData} className="mo-btn-primary mt-5">
                        Retry
                    </button>
                </div>
            ) : null}

            {!loading && !onboardingLoading && hasContext && !error ? (
                <>
                    <div className="grid gap-4 lg:grid-cols-3">
                        <div className="mo-stat-card">
                            <div className="mb-2 flex items-center justify-between">
                                <div className="text-sm text-[#A0A0A0]">Workspace</div>
                                <Building2 className="h-4 w-4 text-[#A0A0A0]" />
                            </div>
                            <div className="text-xl font-bold text-white">{organizationName}</div>
                            <div className="mt-2 text-sm text-[#A0A0A0]">
                                {organization?.industry || organization?.businessType || "Business profile available"}
                            </div>
                        </div>

                        <div className="mo-stat-card">
                            <div className="mb-2 flex items-center justify-between">
                                <div className="text-sm text-[#A0A0A0]">Active Members</div>
                                <Users className="h-4 w-4 text-[#A0A0A0]" />
                            </div>
                            <div className="text-3xl font-bold text-white">{activeMembers}</div>
                            <div className="mt-2 text-sm text-[#A0A0A0]">{pendingMembers} pending invites</div>
                        </div>

                        <div className="mo-stat-card">
                            <div className="mb-2 flex items-center justify-between">
                                <div className="text-sm text-[#A0A0A0]">Security Code</div>
                                <Shield className="h-4 w-4 text-[#A0A0A0]" />
                            </div>
                            <div className="text-xl font-bold text-white">
                                {organization?.teamSecurityCodeConfigured ? "Configured" : "Not configured"}
                            </div>
                            <div className="mt-2 text-sm text-[#A0A0A0]">
                                {organization?.primaryEmail || "Workspace email not set"}
                            </div>
                        </div>
                    </div>

                    {isOwner ? (
                        <div className="mo-card">
                            <div className="flex flex-wrap items-start justify-between gap-4">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <Shield className="h-4 w-4 text-[#4CBB17]" />
                                        <h2 className="text-lg font-semibold text-white">Team Security Code</h2>
                                    </div>
                                    <p className="mt-2 max-w-2xl text-sm leading-6 text-[#A0A0A0]">
                                        This code is required for protected team actions like creating clients,
                                        creating invoices, and sending workspace invites.
                                    </p>
                                </div>
                                <span
                                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                                        organization?.teamSecurityCodeConfigured
                                            ? "border-[#4CBB1740] bg-[#4CBB1720] text-[#4CBB17]"
                                            : "border-[#FFB30040] bg-[#FFB30020] text-[#FFB300]"
                                    }`}
                                >
                                    {organization?.teamSecurityCodeConfigured ? "Configured" : "Not configured"}
                                </span>
                            </div>

                            <div className="mt-5 grid gap-4 md:grid-cols-2">
                                {organization?.teamSecurityCodeConfigured ? (
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">
                                            Current security code
                                        </label>
                                        <input
                                            type="password"
                                            autoComplete="new-password"
                                            value={securityCodeForm.oldTeamActionCode}
                                            onChange={(event) =>
                                                setSecurityCodeForm((current) => ({
                                                    ...current,
                                                    oldTeamActionCode: event.target.value,
                                                }))
                                            }
                                            className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none focus:border-[#4CBB17]"
                                            placeholder="Enter current code"
                                        />
                                    </div>
                                ) : null}

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">
                                        {organization?.teamSecurityCodeConfigured ? "New security code" : "Set security code"}
                                    </label>
                                    <input
                                        type="password"
                                        autoComplete="new-password"
                                        value={securityCodeForm.teamActionCode}
                                        onChange={(event) =>
                                            setSecurityCodeForm((current) => ({
                                                ...current,
                                                teamActionCode: event.target.value,
                                            }))
                                        }
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none focus:border-[#4CBB17]"
                                        placeholder="Minimum 4 characters"
                                    />
                                </div>
                            </div>

                            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                                <p className="text-xs leading-5 text-[#7A7A7A]">
                                    When updated, active team members are emailed the new code. The code is stored hashed server-side.
                                </p>
                                <button
                                    onClick={handleSaveSecurityCode}
                                    disabled={savingSecurityCode}
                                    className="mo-btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
                                >
                                    {savingSecurityCode ? <Loader2 className="h-4 w-4 animate-spin" /> : <Shield className="h-4 w-4" />}
                                    {organization?.teamSecurityCodeConfigured ? "Update Code" : "Set Code"}
                                </button>
                            </div>
                        </div>
                    ) : null}

                    <div className="flex items-center gap-3 rounded-xl border border-[#2A2A2A] bg-[#111111] px-4 py-3">
                        <Search className="h-4 w-4 text-[#A0A0A0]" />
                        <input
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            placeholder="Search members by name, email, or role"
                            className="w-full bg-transparent text-sm text-white outline-none placeholder:text-[#6F6F6F]"
                        />
                    </div>

                    <div className="mo-card !p-0 overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[860px] text-sm">
                                <thead className="bg-[#161616]">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Member
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Role
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Status
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Joined
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Last Active
                                        </th>
                                        <th className="px-4 py-3 text-right text-xs uppercase tracking-wide text-[#8F8F8F]">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>

                                <tbody className="divide-y divide-[#1F1F1F]">
                                    {filteredMembers.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="px-4 py-16 text-center text-[#A0A0A0]">
                                                No team members matched your search.
                                            </td>
                                        </tr>
                                    ) : (
                                        filteredMembers.map((member) => {
                                            const isCurrentUser = member.id === userId;
                                            const canEditRole =
                                                canManageMembers &&
                                                !member.pendingInvite &&
                                                member.role !== "OWNER" &&
                                                !isCurrentUser;
                                            const canRemove =
                                                canManageMembers &&
                                                !member.pendingInvite &&
                                                member.role !== "OWNER" &&
                                                !isCurrentUser;

                                            return (
                                                <tr key={member.id} className="bg-[#101010]">
                                                    <td className="px-4 py-4">
                                                        <div className="flex items-center gap-3">
                                                            <Avatar className="h-10 w-10 bg-[#1A1A1A]">
                                                                <AvatarFallback className="bg-[#4CBB1720] text-[#4CBB17]">
                                                                    {initials(member.name || member.email)}
                                                                </AvatarFallback>
                                                            </Avatar>

                                                            <div>
                                                                <div className="font-medium text-white">
                                                                    {member.name || "Pending invite"}
                                                                    {isCurrentUser ? (
                                                                        <span className="ml-2 text-xs text-[#4CBB17]">(You)</span>
                                                                    ) : null}
                                                                </div>
                                                                <div className="mt-1 text-xs text-[#A0A0A0]">
                                                                    {member.email}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>

                                                    <td className="px-4 py-4">
                                                        {canEditRole ? (
                                                            <div className="flex items-center gap-2">
                                                                <span
                                                                    className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${ROLE_STYLES[member.role] || ROLE_STYLES.VIEWER}`}
                                                                >
                                                                    {member.role}
                                                                </span>
                                                                <select
                                                                    value={member.role}
                                                                    onChange={(event) => handleRoleChange(member.id, event.target.value)}
                                                                    disabled={updatingRoleId === member.id}
                                                                    className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-2 py-1 text-xs text-white outline-none"
                                                                >
                                                                    {ROLE_OPTIONS.map((role) => (
                                                                        <option key={role} value={role}>
                                                                            {role}
                                                                        </option>
                                                                    ))}
                                                                </select>
                                                            </div>
                                                        ) : (
                                                            <span
                                                                className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${ROLE_STYLES[member.role] || ROLE_STYLES.VIEWER}`}
                                                            >
                                                                {member.role}
                                                            </span>
                                                        )}
                                                    </td>

                                                    <td className="px-4 py-4">
                                                        <span
                                                            className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${STATUS_STYLES[member.status] || STATUS_STYLES.ACTIVE}`}
                                                        >
                                                            {member.status}
                                                        </span>
                                                    </td>

                                                    <td className="px-4 py-4 text-[#A0A0A0]">{formatDate(member.joinedAt)}</td>
                                                    <td className="px-4 py-4 text-[#A0A0A0]">
                                                        {member.pendingInvite ? "Awaiting acceptance" : formatDate(member.lastLoginAt)}
                                                    </td>

                                                    <td className="px-4 py-4">
                                                        <div className="flex justify-end gap-2">
                                                            {updatingRoleId === member.id ? (
                                                                <div className="flex items-center text-[#A0A0A0]">
                                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                                </div>
                                                            ) : null}

                                                            {canRemove ? (
                                                                <button
                                                                    onClick={() => handleRemoveMember(member)}
                                                                    disabled={removingMemberId === member.id}
                                                                    className="rounded-lg border border-[#CD1C1840] p-2 text-[#CD1C18] transition hover:bg-[#CD1C1812] disabled:cursor-not-allowed disabled:opacity-60"
                                                                    title="Remove member"
                                                                >
                                                                    {removingMemberId === member.id ? (
                                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                                    ) : (
                                                                        <Trash2 className="h-4 w-4" />
                                                                    )}
                                                                </button>
                                                            ) : (
                                                                <span className="text-xs text-[#666666]">
                                                                    {member.pendingInvite ? "Invite pending" : "--"}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            ) : null}

            {inviteOpen ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
                    <div className="w-full max-w-xl rounded-2xl border border-[#2A2A2A] bg-[#0F0F0F] p-6 shadow-2xl">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-semibold text-white">Invite Team Member</h2>
                                <p className="mt-1 text-sm text-[#A0A0A0]">
                                    Send a workspace invite with the selected role.
                                </p>
                            </div>

                            <button
                                onClick={closeInviteModal}
                                className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] hover:text-white"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        {inviteResult ? (
                            <div className="mt-6 space-y-4 rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                                <div className="text-sm text-[#A0A0A0]">Invite sent to</div>
                                <div className="text-lg font-semibold text-white">{inviteResult.email}</div>
                                <div className="flex flex-wrap gap-2">
                                    <span
                                        className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${ROLE_STYLES[inviteResult.role] || ROLE_STYLES.STAFF}`}
                                    >
                                        {inviteResult.role}
                                    </span>
                                    <span
                                        className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${STATUS_STYLES[inviteResult.status] || STATUS_STYLES.PENDING}`}
                                    >
                                        {inviteResult.status}
                                    </span>
                                </div>
                                <div className="text-sm text-[#A0A0A0]">
                                    Expires {formatDate(inviteResult.expiresAt)}
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => copyInviteLink(inviteResult.token)}
                                        className="mo-btn-primary flex items-center gap-2"
                                    >
                                        <Mail className="h-4 w-4" />
                                        Copy Invite Link
                                    </button>
                                    <button onClick={closeInviteModal} className="mo-btn-secondary">
                                        Close
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="mt-6 space-y-4">
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Email</label>
                                    <input
                                        type="email"
                                        autoComplete="off"
                                        value={inviteForm.email}
                                        onChange={(event) =>
                                            setInviteForm((current) => ({ ...current, email: event.target.value }))
                                        }
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                        placeholder="teammate@company.com"
                                    />
                                </div>

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Role</label>
                                    <select
                                        value={inviteForm.role}
                                        onChange={(event) =>
                                            setInviteForm((current) => ({ ...current, role: event.target.value }))
                                        }
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                    >
                                        {ROLE_OPTIONS.map((role) => (
                                            <option key={role} value={role}>
                                                {role}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Team Security Code</label>
                                    <input
                                        type="password"
                                        autoComplete="new-password"
                                        data-lpignore="true"
                                        data-1p-ignore="true"
                                        value={inviteForm.teamActionCode}
                                        onChange={(event) =>
                                            setInviteForm((current) => ({
                                                ...current,
                                                teamActionCode: event.target.value,
                                            }))
                                        }
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none focus:border-[#4CBB17]"
                                        placeholder="Required to send invites"
                                    />
                                    <p className="text-xs text-[#7A7A7A]">
                                        The backend verifies this code before creating or emailing the invite.
                                    </p>
                                </div>

                                <div className="flex justify-end gap-2">
                                    <button onClick={closeInviteModal} className="mo-btn-secondary">
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleInvite}
                                        disabled={sendingInvite}
                                        className="mo-btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
                                    >
                                        {sendingInvite ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                                        {sendingInvite ? "Sending..." : "Send Invite"}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : null}
        </div>
    );
}
