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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Mail, Shield, Trash2, UserPlus } from "lucide-react";
import { toast } from "sonner";

// ── Mock seed data ─────────────────────────────────────────────────────────────
const INITIAL_MEMBERS = [
    {
        id: 1,
        name: "Archa",
        email: "archa@example.com",
        role: "Owner",
        status: "Active",
        avatar: "/avatars/01.png",
    },
    {
        id: 2,
        name: "John Doe",
        email: "john@example.com",
        role: "Admin",
        status: "Active",
        avatar: "/avatars/02.png",
    },
    {
        id: 3,
        name: "Jane Smith",
        email: "jane@example.com",
        role: "Viewer",
        status: "Pending",
        avatar: "/avatars/03.png",
    },
];

export default function TeamsPage() {
    const [members, setMembers] = useState(INITIAL_MEMBERS);
    const [inviteEmail, setInviteEmail] = useState("");

    // ── Handlers ──────────────────────────────────────────────────────────────

    const handleInvite = () => {
        if (!inviteEmail.trim()) {
            toast.error("Please enter an email address");
            return;
        }
        toast.success(`Invitation sent to ${inviteEmail}`);
        setInviteEmail("");
    };

    const handleRemoveMember = (id) => {
        if (!window.confirm("Are you sure you want to remove this member?")) return;
        setMembers((prev) => prev.filter((m) => m.id !== id));
        toast.success("Member removed");
    };

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Teams</h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Manage your organization members and permissions
                    </p>
                </div>
                <Button onClick={() => document.getElementById("invite-email")?.focus()}>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Add Member
                </Button>
            </div>

            {/* ── Invite Card ────────────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle>Invite New Member</CardTitle>
                    <CardDescription>Send an invitation to join your team</CardDescription>
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
                        />
                        <Button onClick={handleInvite}>
                            <Mail className="mr-2 h-4 w-4" />
                            Send Invite
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* ── Members List ───────────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle>Team Members</CardTitle>
                    <CardDescription>
                        {members.length} {members.length === 1 ? "person" : "people"} with
                        access to this workspace
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="divide-y">
                        {members.map((member) => (
                            <div
                                key={member.id}
                                className="flex items-center justify-between py-4 first:pt-0 last:pb-0 gap-4"
                            >
                                {/* Avatar + info */}
                                <div className="flex items-center gap-4 min-w-0">
                                    <Avatar>
                                        <AvatarImage src={member.avatar} alt={member.name} />
                                        <AvatarFallback>
                                            {member.name.substring(0, 2).toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="min-w-0">
                                        <p className="font-medium truncate">{member.name}</p>
                                        <p className="text-sm text-slate-400 truncate">{member.email}</p>
                                    </div>
                                </div>

                                {/* Status + role + remove */}
                                <div className="flex items-center gap-3 shrink-0">
                                    <Badge
                                        variant={member.status === "Active" ? "default" : "secondary"}
                                    >
                                        {member.status}
                                    </Badge>
                                    <div className="flex items-center gap-1.5 text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                                        <Shield className="h-3 w-3" />
                                        {member.role}
                                    </div>
                                    {/* Owner can't be removed */}
                                    {member.role !== "Owner" && (
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                                            onClick={() => handleRemoveMember(member.id)}
                                            aria-label={`Remove ${member.name}`}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
