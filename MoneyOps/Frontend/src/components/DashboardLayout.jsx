
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/AppSidebar"
import { Outlet } from "react-router-dom"
import { VoiceCallAgent } from "./VoiceCallAgent"
import { Separator } from "@/components/ui/separator"
import { useCallback } from "react"

export default function DashboardLayout() {
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
            <SidebarInset>
                <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12 px-4">
                    <SidebarTrigger className="-ml-1" />
                    <Separator orientation="vertical" className="mr-2 h-4" />
                </header>
                <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
                    <Outlet />
                </div>
                <VoiceCallAgent onActionExec={handleVoiceAction} />
            </SidebarInset>
        </SidebarProvider>
    )
}
