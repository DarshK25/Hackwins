"""
gRPC Server for MoneyOps.
Implements the gRPC services defined in moneyops.proto.
Acts as a proxy to the HTTP backend if needed, or can be integrated directly.
"""
import asyncio
import grpc
from typing import Dict, Any, List
from datetime import datetime

from app.grpc.gen import moneyops_pb2, moneyops_pb2_grpc
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrganizationServicer(moneyops_pb2_grpc.OrganizationServiceServicer):
    """Implementation of OrganizationService."""

    async def GetOnboardingStatus(
        self,
        request: moneyops_pb2.ClerkIdRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetOnboardingStatusResponse:
        """Get onboarding status for a clerk ID."""
        try:
            # TODO: Actually call backend HTTP API or database
            # For now, return a placeholder response
            return moneyops_pb2.GetOnboardingStatusResponse(
                success=True,
                data=moneyops_pb2.OnboardingStatus(
                    onboarding_complete=False,
                    org_id="",
                    org_uuid="",
                    organization_id="",
                )
            )
        except Exception as e:
            logger.error("GetOnboardingStatus error", error=str(e))
            return moneyops_pb2.GetOnboardingStatusResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def GetOrganization(
        self,
        request: moneyops_pb2.OrgIdRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetOrganizationResponse:
        """Get organization by ID."""
        try:
            return moneyops_pb2.GetOrganizationResponse(
                success=True,
                data=moneyops_pb2.Organization(
                    id=request.org_id,
                    name="",
                    clerk_id="",
                    gst_number="",
                    status="ACTIVE",
                    created_at=datetime.utcnow().isoformat(),
                )
            )
        except Exception as e:
            logger.error("GetOrganization error", error=str(e))
            return moneyops_pb2.GetOrganizationResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )


class ClientServicer(moneyops_pb2_grpc.ClientServiceServicer):
    """Implementation of ClientService."""

    async def GetClients(
        self,
        request: moneyops_pb2.GetClientsRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetClientsResponse:
        """Get clients for an organization."""
        try:
            return moneyops_pb2.GetClientsResponse(
                success=True,
                clients=[]
            )
        except Exception as e:
            logger.error("GetClients error", error=str(e))
            return moneyops_pb2.GetClientsResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def CreateClient(
        self,
        request: moneyops_pb2.CreateClientRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.CreateClientResponse:
        """Create a new client."""
        try:
            return moneyops_pb2.CreateClientResponse(
                success=True,
                client=moneyops_pb2.Client(
                    id="new-client-id",
                    display_name=request.name,
                    backend_name=request.name,
                    email=request.email or "",
                    status="ACTIVE",
                    org_id=request.org_id,
                )
            )
        except Exception as e:
            logger.error("CreateClient error", error=str(e))
            return moneyops_pb2.CreateClientResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )


class InvoiceServicer(moneyops_pb2_grpc.InvoiceServiceServicer):
    """Implementation of InvoiceService."""

    async def GetInvoices(
        self,
        request: moneyops_pb2.GetInvoicesRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetInvoicesResponse:
        """Get invoices for an organization."""
        try:
            return moneyops_pb2.GetInvoicesResponse(
                success=True,
                invoices=[]
            )
        except Exception as e:
            logger.error("GetInvoices error", error=str(e))
            return moneyops_pb2.GetInvoicesResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def GetInvoice(
        self,
        request: moneyops_pb2.GetInvoiceRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetInvoiceResponse:
        """Get a specific invoice."""
        try:
            return moneyops_pb2.GetInvoiceResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="NOT_IMPLEMENTED",
                    message="GetInvoice not yet implemented"
                )
            )
        except Exception as e:
            logger.error("GetInvoice error", error=str(e))
            return moneyops_pb2.GetInvoiceResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def CreateInvoice(
        self,
        request: moneyops_pb2.CreateInvoiceRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.CreateInvoiceResponse:
        """Create a new invoice."""
        try:
            return moneyops_pb2.CreateInvoiceResponse(
                success=True,
                invoice=moneyops_pb2.Invoice(
                    id="new-invoice-id",
                    invoice_number="INV-001",
                    client_id=request.client_id,
                    org_id=request.org_id,
                    total_amount=request.total_amount,
                    status="DRAFT",
                    due_date=request.due_date,
                    created_at=datetime.utcnow().isoformat(),
                    description=request.description or "",
                    items=request.items or [],
                )
            )
        except Exception as e:
            logger.error("CreateInvoice error", error=str(e))
            return moneyops_pb2.CreateInvoiceResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def MarkPaid(
        self,
        request: moneyops_pb2.MarkPaidRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.MarkPaidResponse:
        """Mark an invoice as paid."""
        try:
            return moneyops_pb2.MarkPaidResponse(
                success=True,
                invoice=moneyops_pb2.Invoice(
                    id=request.invoice_id,
                    status="PAID",
                    invoice_number="",
                    client_id="",
                    org_id=request.org_id,
                    total_amount=request.amount,
                    due_date="",
                    created_at="",
                    description=request.description or "",
                    items=[],
                )
            )
        except Exception as e:
            logger.error("MarkPaid error", error=str(e))
            return moneyops_pb2.MarkPaidResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )


class FinanceServicer(moneyops_pb2_grpc.FinanceServiceServicer):
    """Implementation of FinanceService."""

    async def GetFinanceMetrics(
        self,
        request: moneyops_pb2.FinanceMetricsRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetFinanceMetricsResponse:
        """Get finance metrics for an organization."""
        try:
            return moneyops_pb2.GetFinanceMetricsResponse(
                success=True,
                data=moneyops_pb2.FinanceMetrics(
                    total_revenue=0,
                    total_expenses=0,
                    net_profit=0,
                    cash_balance=0,
                    outstanding_invoices=0,
                    outstanding_amount=0,
                )
            )
        except Exception as e:
            logger.error("GetFinanceMetrics error", error=str(e))
            return moneyops_pb2.GetFinanceMetricsResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )

    async def GetFinancialSummary(
        self,
        request: moneyops_pb2.FinancialSummaryRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.GetFinancialSummaryResponse:
        """Get financial summary for an organization."""
        try:
            return moneyops_pb2.GetFinancialSummaryResponse(
                success=True,
                data=moneyops_pb2.FinancialSummary(
                    total_income=0,
                    total_expense=0,
                    recent_transactions=[],
                )
            )
        except Exception as e:
            logger.error("GetFinancialSummary error", error=str(e))
            return moneyops_pb2.GetFinancialSummaryResponse(
                success=False,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )


class NotificationServicer(moneyops_pb2_grpc.NotificationServiceServicer):
    """Implementation of NotificationService."""

    async def SendCollectionEmail(
        self,
        request: moneyops_pb2.SendCollectionEmailRequest,
        context: grpc.aio.ServicerContext
    ) -> moneyops_pb2.SendCollectionEmailResponse:
        """Send a collection email."""
        try:
            return moneyops_pb2.SendCollectionEmailResponse(
                success=True,
                sent=True,
                recipient=request.client_email,
            )
        except Exception as e:
            logger.error("SendCollectionEmail error", error=str(e))
            return moneyops_pb2.SendCollectionEmailResponse(
                success=False,
                sent=False,
                recipient=request.client_email,
                error=moneyops_pb2.ErrorResponse(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )


async def serve(port: int = 50051):
    """Start the gRPC server."""
    server = grpc.aio.server(options=[
        ('grpc.max_send_message_length', 50 * 1024 * 1024),
        ('grpc.max_receive_message_length', 50 * 1024 * 1024),
    ])

    # Register all services
    moneyops_pb2_grpc.add_OrganizationServiceServicer_to_server(
        OrganizationServicer(), server
    )
    moneyops_pb2_grpc.add_ClientServiceServicer_to_server(
        ClientServicer(), server
    )
    moneyops_pb2_grpc.add_InvoiceServiceServicer_to_server(
        InvoiceServicer(), server
    )
    moneyops_pb2_grpc.add_FinanceServiceServicer_to_server(
        FinanceServicer(), server
    )
    moneyops_pb2_grpc.add_NotificationServiceServicer_to_server(
        NotificationServicer(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("grpc_server_starting", port=port)

    await server.start()
    logger.info("grpc_server_started", port=port)

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("grpc_server_stopping")
        await server.stop(5)


if __name__ == "__main__":
    asyncio.run(serve())
