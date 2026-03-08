// CLEANUP: removed Customer Agent, Growth Agent, Operations Agent, Strategy Agent, added Command Center, Sales & CRM — June 2025
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  CreditCard,
  FileText,
  Home,
  Users,
  Settings,
  Calculator,
  TrendingUp,
  Search,
  Shield,
  GitMerge,
  Brain,
  Heart,
  Rocket,
  Cog,
  Bell,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { useState, useEffect } from "react";

function SidebarNav({ items }) {
  const { pathname } = useLocation();

  return (
    <nav className="flex flex-col gap-0.5">
      {items.map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/analytics" && pathname.startsWith(item.href));

        return (
          <Link
            key={`${item.href}-${item.title}`}
            to={item.href}
            className={cn(
              "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
              isActive
                ? "bg-[#4CBB1715] text-[#4CBB17]"
                : "text-[#A0A0A0] hover:bg-[#1A1A1A] hover:text-white"
            )}
          >
            {/* Active left border indicator */}
            {isActive && (
              <span
                className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r bg-[#4CBB17]"
                aria-hidden="true"
              />
            )}
            <span
              className={cn(
                "flex-shrink-0 transition-colors",
                isActive ? "text-[#4CBB17]" : "text-[#A0A0A0]"
              )}
            >
              {item.icon}
            </span>
            <span>{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function AppSidebar(props) {
  const { orgId, userId } = useOnboardingStatus();
  const [orgName, setOrgName] = useState("MoneyOps");

  useEffect(() => {
    const fetchOrgName = async () => {
      if (!userId) return;
      try {
        const response = await fetch(`/api/org/my`, {
          headers: { "X-User-Id": userId }
        });
        if (response.ok) {
          const result = await response.json();
          const data = result.data;
          setOrgName(data.legalName || "MoneyOps");
        }
      } catch (err) {
        console.error("Failed to fetch org name", err);
      }
    };
    fetchOrgName();
  }, [orgId, userId]);

  const mainNavItems = [
    {
      href: "/analytics",
      title: "Overview",
      icon: <Home className="h-4 w-4" />,
    },

    {
      href: "/invoices",
      title: "Invoices",
      icon: <FileText className="h-4 w-4" />,
    },
    {
      href: "/clients",
      title: "Clients",
      icon: <Users className="h-4 w-4" />,
    },
    {
      href: "/cashflow",
      title: "Cash Flow",
      icon: <BarChart3 className="h-4 w-4" />,
    },
    {
      href: "/documents",
      title: "Documents",
      icon: <FileText className="h-4 w-4" />,
    },
  ];

  const agentNavItems = [
    {
      href: "/finance-agent",
      title: "Finance Agent",
      icon: <Calculator className="h-4 w-4" />,
    },
    {
      href: "/sales-crm",
      title: "Sales CRM",
      icon: <TrendingUp className="h-4 w-4" />,
    },
    {
      href: "/compliance",
      title: "Compliance",
      icon: <Shield className="h-4 w-4" />,
    },
    {
      href: "/market-intelligence",
      title: "Market Agent",
      icon: <Search className="h-4 w-4" />,
    },
    {
      href: "/orchestrator",
      title: "Orchestrator",
      icon: <GitMerge className="h-4 w-4" />,
    },
  ];

  const utilityNavItems = [
    {
      href: "/teams",
      title: "Teams",
      icon: <Users className="h-4 w-4" />,
    },{
      href: "/settings",
      title: "Settings",
      icon: <Settings className="h-4 w-4" />,
    },
  ];

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      {/* Logo */}
      <SidebarHeader className="border-b border-[#2A2A2A] px-4 py-4">
        <div className="flex items-center gap-3">
          {/* MoneyOps logo mark */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#4CBB17] flex-shrink-0 overflow-hidden">
            <svg viewBox="0 0 32 32" width="22" height="22" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Lightning bolt / zigzag path */}
              <path d="M10 22 L14 14 L18 18 L22 10" stroke="#000" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              {/* Arrow tip pointing up-right */}
              <path d="M19 10 L22 10 L22 13" stroke="#000" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-bold text-white truncate">{orgName}</span>
            <span className="text-xs text-[#A0A0A0] truncate">MoneyOps Workspace</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="flex-1 bg-[#111111]">
        <ScrollArea className="flex-1 px-3 py-4">
          <div className="flex flex-col gap-6">
            {/* Finance */}
            <div>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[#A0A0A0]">
                Finance
              </p>
              <SidebarNav items={mainNavItems} />
            </div>

            {/* Agents */}
            <div>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[#A0A0A0]">
                AI Agents
              </p>
              <SidebarNav items={agentNavItems} />
            </div>

            {/* Utilities */}
            <div>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[#A0A0A0]">
                Workspace
              </p>
              <SidebarNav items={utilityNavItems} />
            </div>
          </div>
        </ScrollArea>
      </SidebarContent>

      <SidebarFooter className="border-t border-[#2A2A2A] px-4 py-3 bg-[#111111]">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#4CBB17] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#4CBB17]" />
          </span>
          <span className="text-xs text-[#A0A0A0]">All systems operational</span>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
