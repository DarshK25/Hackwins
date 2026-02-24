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
  Cog
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
import { Bot } from "lucide-react";

function SidebarNav({ className, items, ...props }) {
  const { pathname } = useLocation();

  return (
    <nav className={cn("flex flex-col space-y-1", className)} {...props}>
      {items.map((item) => {
        const isActive = pathname === item.href || (item.href !== "/analytics" && pathname.startsWith(item.href));

        return (
          <Link
            key={`${item.href}-${item.title}`}
            to={item.href}
            className={cn(
              "group relative flex items-center justify-start rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 w-full",
              isActive
                ? "bg-gradient-to-r from-primary/20 to-accent/10 text-primary shadow-md shadow-primary/20"
                : "text-muted-foreground hover:bg-primary/5 hover:text-foreground",
              item.variant === "default" && "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            {/* Active indicator */}
            {isActive && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-1 rounded-r-full bg-gradient-to-b from-primary to-accent shadow-lg shadow-primary/50" />
            )}

            {/* Icon with glow */}
            <div className={cn(
              "mr-3 transition-all duration-200",
              isActive && "drop-shadow-[0_0_6px_rgba(34,197,94,0.4)]"
            )}>
              <div className={cn(
                "h-4 w-4 transition-all duration-200",
                isActive && "scale-110 text-primary"
              )}>
                {item.icon}
              </div>
            </div>

            {/* Text */}
            <span className={cn(
              "transition-all duration-200",
              isActive && "font-semibold"
            )}>
              {item.title}
            </span>

            {/* Hover effect */}
            {!isActive && (
              <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-primary/0 via-primary/5 to-accent/0 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
            )}

            {/* Active pulse */}
            {isActive && (
              <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-primary/5 to-accent/5 animate-pulse" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppSidebar(props) {
  const mainNavItems = [
    {
      href: "/analytics",
      title: "Overview",
      icon: <Home className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/finances",
      title: "Bank Accounts",
      icon: <CreditCard className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/transactions",
      title: "Transactions",
      icon: <FileText className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/invoices",
      title: "Invoices",
      icon: <FileText className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/clients",
      title: "Clients",
      icon: <Users className="h-4 w-4" />,
      variant: "ghost",
    },
  ];

  const agentNavItems = [
    {
      href: "/finance-intelligence",
      title: "Finance Agent",
      icon: <Calculator className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/sales-crm",
      title: "Sales Agent",
      icon: <TrendingUp className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/strategy-agent",
      title: "Strategy Agent",
      icon: <Brain className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/compliance",
      title: "Compliance Agent",
      icon: <Shield className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/customer-agent",
      title: "Customer Agent",
      icon: <Heart className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/growth-agent",
      title: "Growth Agent",
      icon: <Rocket className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/operations-agent",
      title: "Operations Agent",
      icon: <Cog className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/market-research",
      title: "Research Agent",
      icon: <Search className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/orchestrator",
      title: "Orchestrator",
      icon: <GitMerge className="h-4 w-4" />,
      variant: "ghost",
    },
  ];

  const utilityNavItems = [
    {
      href: "/teams",
      title: "Teams",
      icon: <Users className="h-4 w-4" />,
      variant: "ghost",
    },
    {
      href: "/settings",
      title: "Settings",
      icon: <Settings className="h-4 w-4" />,
      variant: "ghost",
    },
  ];

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground bg-gradient-to-br from-primary to-green-600">
            <Bot className="size-4" />
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-semibold">MoneyOps</span>
            <span className="truncate text-xs text-muted-foreground">Enterprise</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="flex-1">
        <ScrollArea className="flex-1 px-3">
          <div className="flex flex-col gap-6 py-4">
            <div className="flex flex-col gap-2">
              <h3 className="px-4 text-xs font-medium text-muted-foreground">Main</h3>
              <SidebarNav items={mainNavItems} />
            </div>
            <div className="flex flex-col gap-2">
              <h3 className="px-4 text-xs font-medium text-muted-foreground">Agents</h3>
              <SidebarNav items={agentNavItems} />
            </div>
            <div className="flex flex-col gap-2">
              <h3 className="px-4 text-xs font-medium text-muted-foreground">Utilities</h3>
              <SidebarNav items={utilityNavItems} />
            </div>
          </div>
        </ScrollArea>
      </SidebarContent>

      <SidebarFooter>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
