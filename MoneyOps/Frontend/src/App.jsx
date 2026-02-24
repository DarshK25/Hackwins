import { Routes, Route } from "react-router-dom";
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
import AlertAgentPage from "@/pages/AlertAgentPage";
import ComplianceAgentPage from "@/pages/ComplianceAgentPage";
import FinanceIntelligencePage from "@/pages/FinanceIntelligencePage";
import OrchestratorPage from "@/pages/OrchestratorPage";
import MarketResearchPage from "@/pages/MarketResearchPage";
import SalesCRMPage from "@/pages/SalesCRMPage";
import StrategyAgentPage from "@/pages/StrategyAgentPage";
import CustomerAgentPage from "@/pages/CustomerAgentPage";
import GrowthAgentPage from "@/pages/GrowthAgentPage";
import OperationsAgentPage from "@/pages/OperationsAgentPage";
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
                    <Route path="/teams" element={<TeamsPage />} />
                    <Route path="/documents" element={<DocumentsPage />} />
                    <Route path="/alerts" element={<AlertAgentPage />} />
                    <Route path="/compliance" element={<ComplianceAgentPage />} />
                    <Route path="/finance-intelligence" element={<FinanceIntelligencePage />} />
                    <Route path="/orchestrator" element={<OrchestratorPage />} />
                    <Route path="/market-research" element={<MarketResearchPage />} />
                    <Route path="/sales-crm" element={<SalesCRMPage />} />
                    <Route path="/strategy-agent" element={<StrategyAgentPage />} />
                    <Route path="/customer-agent" element={<CustomerAgentPage />} />
                    <Route path="/growth-agent" element={<GrowthAgentPage />} />
                    <Route path="/operations-agent" element={<OperationsAgentPage />} />
                </Route>
            </Routes>
        </>
    );
}
