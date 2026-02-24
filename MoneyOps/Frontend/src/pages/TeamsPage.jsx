import { useState, useEffect } from "react";
import { useAuth, useUser } from "@clerk/clerk-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Mail, Shield, Trash2, UserPlus, Copy, Check } from "lucide-react";
import { toast } from "sonner";

export default function TeamsPage() {
    const { getToken, userId, orgId } = useAuth();
    const { user: clerkUser } = useUser();
    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviting, setInviting] = useState(false);
    const [copied, setCopied] = useState(false);

    const fetchMembers = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/users", {
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId
                }
            });
            if (!res.ok) throw new Error("Failed to fetch team members");
            const data = await res.json();
            setMembers(data);
        } catch (err) {
            console.error("Fetch error:", err);
            toast.error("Failed to load team members");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (userId && orgId) {
            fetchMembers();
        }
    }, [userId, orgId]);

    const handleInvite = async () => {
        if (!inviteEmail.trim()) {
            toast.error("Please enter an email address");
            return;
        }

        setInviting(true);
        try {
            const token = await getToken();
            const res = await fetch("/api/users/invite", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId
                },
                body: JSON.stringify({
                    email: inviteEmail,
                    role: "STAFF"
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.message || "Failed to send invitation");
            }

            toast.success(`Invitation sent to ${inviteEmail}`);
            setInviteEmail("");
        } catch (err) {
            console.error("Invite error:", err);
            toast.error(err.message);
        } finally {
            setInviting(false);
        }
    };

    const handleCopyInviteCode = () => {
        if (!orgId) return;
        navigator.clipboard.writeText(orgId);
        setCopied(true);
        toast.success("Invite code copied to clipboard");
        setTimeout(() => setCopied(false), 2000);
    };

    const handleRemoveMember = async (targetId) => {
        if (!window.confirm("Are you sure you want to remove this member?")) return;

        try {
            const token = await getToken();
            const res = await fetch(`/api/users/${targetId}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId
                }
            });

            if (!res.ok) throw new Error("Failed to remove member");

            setMembers((prev) => prev.filter((m) => m.id !== targetId));
            toast.success("Member removed");
        } catch (err) {
            console.error("Delete error:", err);
            toast.error(err.message);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Teams</h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Manage your organization members and permissions
                    </p>
                </div>
                <div className="flex gap-2">
                    <Card className="flex items-center px-4 py-2 bg-slate-50 border-dashed">
                        <div className="flex flex-col mr-4">
                            <span className="text-[10px] uppercase font-bold text-slate-400">Invite Code</span>
                            <span className="text-sm font-mono font-medium">{orgId ? `${orgId.substring(0, 8)}...` : "Loading..."}</span>
                        </div>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopyInviteCode}>
                            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                        </Button>
                    </Card>
                    <Button onClick={() => document.getElementById("invite-email")?.focus()}>
                        <UserPlus className="mr-2 h-4 w-4" />
                        Add Member
                    </Button>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Invite New Member</CardTitle>
                    <CardDescription>Send an invitation to join your team via email</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-3 flex-wrap">
                        <Input
                            id="invite-email"
                            type="email"
                            placeholder="colleague@company.com"
                            value={inviteEmail}
                            onChange={(e) => setInviteEmail(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                            className="max-w-md"
                            disabled={inviting}
                        />
                        <Button onClick={handleInvite} disabled={inviting}>
                            <Mail className="mr-2 h-4 w-4" />
                            {inviting ? "Sending..." : "Send Invite"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Team Members</CardTitle>
                    <CardDescription>
                        {loading ? "Loading team members..." : `${members.length} ${members.length === 1 ? "person" : "people"} in this organization`}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="divide-y">
                        {loading ? (
                            <div className="py-8 text-center text-slate-400">Fetching team members...</div>
                        ) : members.length === 0 ? (
                            <div className="py-8 text-center text-slate-400">No members found.</div>
                        ) : (
                            members.map((member) => (
                                <div
                                    key={member.id}
                                    className="flex items-center justify-between py-4 first:pt-0 last:pb-0 gap-4"
                                >
                                    <div className="flex items-center gap-4 min-w-0">
                                        <Avatar>
                                            <AvatarFallback className="bg-blue-100 text-blue-700 font-bold">
                                                {member.name?.substring(0, 2).toUpperCase() || "U"}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="min-w-0">
                                            <p className="font-medium truncate">{member.name || "Unnamed User"}</p>
                                            <p className="text-sm text-slate-400 truncate">{member.email}</p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3 shrink-0">
                                        <Badge
                                            variant={member.status === "ACTIVE" ? "default" : "secondary"}
                                        >
                                            {member.status || "ACTIVE"}
                                        </Badge>
                                        <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full capitalize">
                                            <Shield className="h-3 w-3" />
                                            {member.role?.toLowerCase() || "staff"}
                                        </div>
                                        {member.role !== "OWNER" && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                                onClick={() => handleRemoveMember(member.id)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
