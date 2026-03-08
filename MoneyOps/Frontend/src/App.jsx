import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import LandingPage from "@/pages/LandingPage";
import SignInPage from "@/pages/SignInPage";
import SignUpPage from "@/pages/SignUpPage";
import OnboardingPage from "@/pages/OnboardingPage";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import ClientsPage from "@/pages/ClientsPage";
import CashflowPage from "@/pages/CashflowPage";
import FinancesPage from "@/pages/FinancesPage";
import InvoicesPage from "@/pages/InvoicesPage";
import NewInvoicePage from "@/pages/NewInvoicePage";
import InvoiceDetailPage from "@/pages/InvoiceDetailPage";
import SettingsPage from "@/pages/SettingsPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import TransactionsPage from "@/pages/TransactionsPage";
import TeamsPage from "@/pages/TeamsPage";
import DocumentsPage from "@/pages/DocumentsPage";
import SalesCRMPage from "@/pages/SalesCRMPage";
import MarketResearchPage from "@/pages/MarketResearchPage";
import FinanceIntelligencePage from "@/pages/FinanceIntelligencePage";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";
import { OrchestratorDashboard } from "@/components/OrchestratorDashboard";
import DashboardLayout from "@/components/DashboardLayout";

export default function App() {
    return (
        <>
            {/* Global toast notifications (sonner) */}
            <Toaster position="top-right" richColors />

            <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/sign-in/*" element={<SignInPage />} />
                <Route path="/sign-up/*" element={<SignUpPage />} />

                {/* Onboarding — protected (must be signed in) but no sidebar */}
                <Route
                    path="/onboarding"
                    element={
                        <ProtectedRoute>
                            <OnboardingPage />
                        </ProtectedRoute>
                    }
                />

                {/* Dashboard Routes (Sidebar + Voice Agent) */}
                <Route
                    element={
                        <ProtectedRoute>
                            <DashboardLayout />
                        </ProtectedRoute>
                    }
                >
                    <Route path="/clients" element={<ClientsPage />} />
                    <Route path="/cashflow" element={<CashflowPage />} />
                    <Route path="/finances" element={<FinancesPage />} />
                    <Route path="/invoices" element={<InvoicesPage />} />
                    <Route path="/invoices/new" element={<NewInvoicePage />} />
                    <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/analytics" element={<AnalyticsPage />} />
                    <Route path="/transactions" element={<TransactionsPage />} />
                    <Route path="/documents" element={<DocumentsPage />} />
                    
                    {/* 5 Core Agents */}
                    <Route path="/finance-agent" element={<FinanceIntelligencePage />} />
                    <Route path="/sales-crm" element={<SalesCRMPage />} />
                    <Route path="/market-intelligence" element={<MarketResearchPage />} />
                    <Route path="/compliance" element={<ComplianceDashboard />} />
                    <Route path="/orchestrator" element={<OrchestratorDashboard />} />
                    <Route path="/teams" element={<TeamsPage />} />
                </Route>
            </Routes>
        </>
    );
}
