import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/AppSidebar"
import { Outlet, useLocation } from "react-router-dom"
import { VoiceCallAgent } from "./VoiceCallAgent"
import { Separator } from "@/components/ui/separator"
import { useCallback } from "react"

const PAGE_TITLES = {
    "/analytics": "Overview",
    "/finances": "Bank Accounts",
    "/transactions": "Transactions",
    "/invoices": "Invoices",
    "/clients": "Clients",
    "/cashflow": "Cash Flow",
    "/documents": "Documents",
    "/finance-intelligence": "Finance Agent",
    "/sales-crm": "Sales Agent",
    "/strategy-agent": "Strategy Agent",
    "/market-research": "Research Agent",
    "/compliance": "Compliance Agent",
    "/alerts": "Alert Agent",
    "/customer-agent": "Customer Agent",
    "/growth-agent": "Growth Agent",
    "/operations-agent": "Operations Agent",
    "/orchestrator": "Orchestrator",
    "/teams": "Teams",
    "/settings": "Settings",
    "/onboarding": "Onboarding",
};

export default function DashboardLayout() {
    const { pathname } = useLocation();
    const pageTitle = Object.entries(PAGE_TITLES).find(([key]) => pathname.startsWith(key))?.[1] ?? "Dashboard";

    // Fired by VoiceCallAgent when an invoice is successfully created via voice.
    // Dispatches a custom window event so any mounted page (e.g. InvoicesPage)
    // can refresh its data without needing prop-drilling.
    const handleVoiceAction = useCallback((action) => {
        if (action.type === "invoice_created") {
            window.dispatchEvent(new CustomEvent("voice:invoice-created"));
        } else if (action.type === "client_created") {
            window.dispatchEvent(new CustomEvent("voice:client-created"));
        }
    }, []);

    return (
        <SidebarProvider>
            <AppSidebar />
            <SidebarInset className="bg-black">
                {/* Top bar */}
                <header className="flex h-14 shrink-0 items-center gap-3 border-b border-[#2A2A2A] bg-black px-4 sticky top-0 z-40">
                    <SidebarTrigger className="text-[#A0A0A0] hover:text-[#4CBB17] hover:bg-transparent -ml-1 transition-colors" />
                    <Separator orientation="vertical" className="h-4 bg-[#2A2A2A]" />
                    <span className="text-sm font-medium text-[#A0A0A0]">{pageTitle}</span>
                </header>

                {/* Page content */}
                <div className="flex flex-1 flex-col bg-black min-h-screen">
                    <div className="p-6 max-w-[1200px] w-full mx-auto">
                        <Outlet />
                    </div>
                </div>

                {/* Floating voice agent */}
                <VoiceCallAgent onActionExec={handleVoiceAction} />
            </SidebarInset>
        </SidebarProvider>
    )
}
