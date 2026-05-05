"""
gRPC Client for MoneyOps.
Replaces HTTP calls in backend_adapter.py with low-latency gRPC.
"""
from typing import Optional, Any, Dict, List
import grpc
import asyncio

# Import generated gRPC stubs
from app.grpc.gen import moneyops_pb2, moneyops_pb2_grpc
from app.grpc.gen.moneyops_pb2 import (  # noqa: F401
    GetInvoicesRequest,
    CreateInvoiceRequest,
    MarkPaidRequest,
    InvoiceItem as GrpcInvoiceItem,
    InvoiceStatus,
)


class GRPCClient:
    """
    gRPC client for communicating with Core Backend.
    Uses protocol buffers for efficient serialization.
    """

    def __init__(self, host: str = "127.0.0.1:50051"):
        self.host = host
        self.channel = None
        self._connect()

    def _connect(self):
        """Create gRPC channel with connection pooling"""
        self.channel = grpc.aio.insecure_channel(
            self.host,
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
            ]
        )

    async def get_invoices(
        self,
        org_id: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get invoices via gRPC.
        Replaces HTTP call in backend_adapter.py
        """
        try:
            stub = moneyops_pb2_grpc.InvoiceServiceStub(self.channel)

            # Map status string to enum
            status_enum = InvoiceStatus.INVOICE_STATUS_UNSPECIFIED
            if status:
                status_map = {
                    "DRAFT": InvoiceStatus.DRAFT,
                    "SENT": InvoiceStatus.SENT,
                    "OVERDUE": InvoiceStatus.OVERDUE,
                    "PAID": InvoiceStatus.PAID,
                    "CANCELLED": InvoiceStatus.CANCELLED,
                }
                status_enum = status_map.get(status.upper(), InvoiceStatus.INVOICE_STATUS_UNSPECIFIED)

            request = GetInvoicesRequest(
                org_id=org_id,
                status=status_enum,
                limit=100,
            )
            response = await stub.GetInvoices(request, timeout=30)

            if response.success:
                invoices = []
                for inv in response.invoices:
                    invoices.append({
                        "id": inv.id,
                        "invoiceNumber": inv.invoice_number,
                        "clientId": inv.client_id,
                        "orgId": inv.org_id,
                        "totalAmount": inv.total_amount,
                        "status": inv.status,
                        "dueDate": inv.due_date,
                        "createdAt": inv.created_at,
                        "description": inv.description,
                    })
                return {
                    "success": True,
                    "data": invoices,
                    "source": "grpc",
                }
            else:
                error_msg = response.error.message if response.error else "Unknown error"
                return {
                    "success": False,
                    "error": f"gRPC error: {error_msg}",
                    "source": "grpc",
                }
        except grpc.RpcError as e:
            return {
                "success": False,
                "error": f"gRPC error: {e.code()}: {e.details()}",
                "source": "grpc",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "grpc",
            }

    async def mark_invoice_paid(
        self,
        invoice_id: str,
        org_id: str,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mark invoice as paid via gRPC"""
        try:
            stub = moneyops_pb2_grpc.InvoiceServiceStub(self.channel)

            request = MarkPaidRequest(
                invoice_id=invoice_id,
                org_id=org_id,
                amount=payment_data.get("amount", 0),
                description=payment_data.get("description", ""),
                payment_date=payment_data.get("paymentDate", ""),
            )
            response = await stub.MarkPaid(request, timeout=30)

            if response.success:
                inv = response.invoice
                return {
                    "success": True,
                    "data": {
                        "id": inv.id,
                        "status": inv.status,
                        "invoiceNumber": inv.invoice_number,
                    },
                    "source": "grpc",
                }
            else:
                error_msg = response.error.message if response.error else "Unknown error"
                return {
                    "success": False,
                    "error": f"gRPC error: {error_msg}",
                    "source": "grpc",
                }
        except grpc.RpcError as e:
            return {
                "success": False,
                "error": f"gRPC error: {e.code()}: {e.details()}",
                "source": "grpc",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "grpc",
            }

    async def create_invoice(self, org_id: str, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice via gRPC"""
        try:
            stub = moneyops_pb2_grpc.InvoiceServiceStub(self.channel)

            # Convert items if present
            items = []
            if "items" in invoice_data:
                for item in invoice_data["items"]:
                    items.append(GrpcInvoiceItem(
                        description=item.get("description", ""),
                        quantity=item.get("quantity", 1),
                        unit_price=item.get("unitPrice", 0),
                        amount=item.get("amount", 0),
                    ))

            request = CreateInvoiceRequest(
                org_id=org_id,
                client_id=invoice_data.get("clientId", ""),
                total_amount=invoice_data.get("totalAmount", 0),
                due_date=invoice_data.get("dueDate", ""),
                description=invoice_data.get("description", ""),
                items=items,
            )
            response = await stub.CreateInvoice(request, timeout=30)

            if response.success:
                inv = response.invoice
                return {
                    "success": True,
                    "data": {
                        "id": inv.id,
                        "invoiceNumber": inv.invoice_number,
                        "status": inv.status,
                        "totalAmount": inv.total_amount,
                    },
                    "source": "grpc",
                }
            else:
                error_msg = response.error.message if response.error else "Unknown error"
                return {
                    "success": False,
                    "error": f"gRPC error: {error_msg}",
                    "source": "grpc",
                }
        except grpc.RpcError as e:
            return {
                "success": False,
                "error": f"gRPC error: {e.code()}: {e.details()}",
                "source": "grpc",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "grpc",
            }

    async def send_collection_email(
        self,
        invoice_id: str,
        client_email: str,
        client_name: str,
        invoice_number: str,
        amount: float,
        due_date: str,
        org_id: Optional[str] = None,
        tone: str = "gentle",
    ) -> Dict[str, Any]:
        """Send collection email via gRPC"""
        try:
            stub = moneyops_pb2_grpc.NotificationServiceStub(self.channel)

            request = moneyops_pb2.SendCollectionEmailRequest(
                invoice_id=invoice_id,
                client_email=client_email,
                client_name=client_name,
                invoice_number=invoice_number,
                amount=amount,
                due_date=due_date,
                org_id=org_id or "",
                tone=tone,
            )
            response = await stub.SendCollectionEmail(request, timeout=30)

            return {
                "success": response.success,
                "sent": response.sent,
                "recipient": response.recipient,
                "error": response.error.message if response.error else None,
                "source": "grpc",
            }
        except grpc.RpcError as e:
            return {
                "success": False,
                "error": f"gRPC error: {e.code()}: {e.details()}",
                "source": "grpc",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "grpc",
            }

    async def close(self):
        """Close gRPC channel"""
        if self.channel:
            await self.channel.close()


# Singleton instance
grpc_client = GRPCClient()
