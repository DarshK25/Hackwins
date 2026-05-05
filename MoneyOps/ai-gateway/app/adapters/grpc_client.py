"""
gRPC Client for MoneyOps.
Replaces HTTP calls in backend_adapter.py with low-latency gRPC.
"""
from typing import Optional, Any, Dict
import grpc
import asyncio
from concurrent import futures

# Will generate from .proto files
# from app.grpc.gen import invoices_pb2, invoices_pb2_grpc


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
            # TODO: Import generated stubs after .proto compilation
            # stub = invoices_pb2_grpc.InvoiceServiceStub(self.channel)
            # request = invoices_pb2.GetInvoicesRequest(
            #     org_id=org_id,
            #     status=status or ""
            # )
            # response = await stub.GetInvoices(request, timeout=30)
            
            # Placeholder - returns structure matching HTTP response
            return {
                "success": True,
                "data": [],  # Will be populated from gRPC response
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
            # stub = invoices_pb2_grpc.InvoiceServiceStub(self.channel)
            # request = invoices_pb2.MarkPaidRequest(
            #     invoice_id=invoice_id,
            #     org_id=org_id,
            #     amount=payment_data.get("amount", 0),
            #     description=payment_data.get("description", "")
            # )
            # response = await stub.MarkPaid(request, timeout=30)
            
            return {
                "success": True,
                "data": {"status": "PAID"},
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
            # stub = invoices_pb2_grpc.InvoiceServiceStub(self.channel)
            # request = invoices_pb2.CreateInvoiceRequest(
            #     org_id=org_id,
            #     client_id=invoice_data.get("clientId"),
            #     total_amount=invoice_data.get("totalAmount", 0),
            #     due_date=invoice_data.get("dueDate", ""),
            #     description=invoice_data.get("description", "")
            # )
            # response = await stub.CreateInvoice(request, timeout=30)
            
            return {
                "success": True,
                "data": {"id": "new-invoice-id"},
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
