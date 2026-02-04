"""
Backend HTTP adapter: http client for backend core API
Handles all communication with Springboot backend
"""

from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class BackendResponse(BaseModel):
    """Standard response from backend core"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int

class BackendHttpAdapter:
    """
    Http client for backend core api
    Handles auth, retries, and error handling
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.BACKEND_BASE_URL
        self.timeout = getattr(settings, "BACKEND_TIMEOUT", 30)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent":  "MoneyOps-AI-Gateway/1.0"
            }
        )
        
        logger.info("backend_adatper_initialized", base_url=self.base_url)
        
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]]=  None,
        headers: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> BackendResponse:
        """
        Make http req to backend core
        Args: 
            method: Http method,
            endpoint: API endpoint
            data: Req body,
            params: Query params
            headers: Additional headers

        Returns: 
            BackendResponse
        """
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        # Merge headers
        req_headers = self.client.headers.copy()
        if headers:
            req_headers.update(headers)
        if context and context.get("auth_token"):
            req_headers["Authorization"] = f"Bearer {context['auth_token']}"

        try:
            logger.debug(
                "backend_request",
                method=method,
                endpoint=endpoint,
                has_data=bool(data)
            )

            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=req_headers
            )

            #parse response
            response_data = None
            if response.text:
                try:
                    response_data = response.json()
                except:
                    response_data = {"text": response.text}
            
            success = 200 <= response.status_code < 300

            if not success:
                logger.warning(
                    "backend_request_failed",
                    status_code=response.status_code,
                    endpoint=endpoint
                )

            return BackendResponse(
                success=success,
                data=response_data,
                status_code=response.status_code,
                error=response_data.get("error") or response_data.get("message") if isinstance(response_data, dict) else None
            )
 
        except httpx.TimeoutException as e:
            logger.error("backend_timeout", endpoint=endpoint, error=str(e))
            return BackendResponse(
                success=False,
                error="Backend service timeout",
                status_code=504
            )
        
        except httpx.ConnectError as e:
            logger.error("backend_connection_error", endpoint=endpoint, error=str(e))
            return BackendResponse(
                success=False,
                error="Cannot connect to backend service",
                status_code=503
            )

        except Exception as e:
            logger.error("backend_request_error", endpoint=endpoint, error=str(e))
            return BackendResponse(
                success=False,
                error=str(e),
                status_code=500
            )            
        
    #===========================
    #Invoice ops
    #===========================
    async def create_invoice(
        self,
        org_id:str,
        client_name: str,
        items: List[Dict[str, Any]],
        subtotal: float,
        tax: float,
        total:float,
        due_date:Optional[str] = None,
        notes: Optional[str] = None    
    ) -> BackendResponse:
        """Create a new invoice"""
        payload = {
            "organizationId" : org_id,
            "clientName"  : client_name,
            "items" : items,
            "subtotal" : subtotal,
            "tax" : tax,
            "total": total,
            "dueDate" : due_date,
            "notes": notes
        }

        return await self._request("POST", "/api/v1/invoices", data=payload)
    

    async def get_invoices(
        self,
        org_id: str,
        status: Optional[str] = None,
        client_name: Optional[str] = None,
        limit: int = 50
    ) -> BackendResponse:
        """Get invoices with optional filters"""
        params = {
            "organizationId" : org_id,
            "limit" : limit
        }

        if status:
            params["status"] = status
        if client_name:
            params["clientName"] = client_name

        return await self._request("GET", "api/v1/invoices", params=params)
    
    async def get_invoice_by_id(self, invoice_id: str) -> BackendResponse:
        """Get a specific invoice"""
        return await self._request("GET", f"api/v1/invoices/{invoice_id}")
 
    async def update_invoice(
        self,
        invoice_id: str,
        updates: Dict[str, Any]
    ) -> BackendResponse:
        """Update an invoice"""
        return await self._request("PATCH", f"api/v1/invoices/{invoice_id}", data=updates)
    
    async def delete_invoice(self, invoice_id: str) -> BackendResponse:
        """Delete an invoice"""
        return await self._request("DELETE", f"api/v1/invoices/{invoice_id}")

    # ========================================
    # CLIENT OPERATIONS
    # ========================================

    async def create_client(
        self,
        org_id: str,
        name: str,
        email: str,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        gst_number: Optional[str] = None
    ) -> BackendResponse:
        """Create a new client"""
        payload = {
            "organizationId": org_id,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "gstNumber": gst_number
        }

        return await self._request("POST", "/api/v1/clients", data=payload)

    async def get_clients(
        self,
        org_id: str,
        search: Optional[str] = None,
        limit: int = 50
    ) -> BackendResponse:
        """Get clients with optional search"""
        params = {
            "organizationId": org_id,
            "limit": limit
        }
        
        if search:
            params["search"] = search
        
        return await self._request("GET", "/api/v1/clients", params=params)


    async def get_client_by_name(self, org_id: str, name: str) -> BackendResponse:
        """Get client by name"""
        return await self._request(
            "GET",
            "/api/v1/clients/search",
            params={"organizationId": org_id, "name": name}
        )

    # ========================================
    # PAYMENT OPERATIONS
    # ========================================
    
    async def record_payment(
        self,
        org_id: str,
        invoice_id: str,
        amount: float,
        payment_method: str = "BANK_TRANSFER",
        payment_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> BackendResponse:
        """Record a payment for an invoice"""
        payload = {
            "organizationId": org_id,
            "invoiceId": invoice_id,
            "amount": amount,
            "paymentMethod": payment_method,
            "paymentDate": payment_date,
            "notes": notes
        }
        
        return await self._request("POST", "/api/v1/payments", data=payload)
    
    async def get_payments(
        self,
        org_id: str,
        invoice_id: Optional[str] = None,
        limit: int = 50
    ) -> BackendResponse:
        """Get payments"""
        params = {
            "organizationId": org_id,
            "limit": limit
        }

        if invoice_id:
            params["invoiceId"] = invoice_id
        
        return await self._request("GET", "/api/v1/payments", params=params)
    
    # ========================================
    # TRANSACTION OPERATIONS
    # ========================================
    
    async def get_transactions(
        self,
        org_id: str,
        transaction_type: Optional[str] = None,
        limit: int = 50
    ) -> BackendResponse:
        """Get transactions"""
        params = {
            "organizationId": org_id,
            "limit": limit
        }
        
        if transaction_type:
            params["type"] = transaction_type
        
        return await self._request("GET", "/api/v1/transactions", params=params)
    
    async def get_balance(self, org_id: str, context: Optional[Dict[str, Any]] = None) -> BackendResponse:
        """Get account balance by calling transactions summary and returning netProfit as balance"""
        # Transactions summary endpoint expects X-Org-Id header
        summary_resp = await self._request(
            "GET",
            "/api/transactions/summary",
            headers={"X-Org-Id": org_id},
            context=context
        )

        if not summary_resp.success:
            return summary_resp

        # Map backend summary to a balance-like response for compatibility
        summary_data = summary_resp.data or {}
        balance = summary_data.get("netProfit")

        return BackendResponse(
            success=True,
            data={"balance": balance if balance is not None else 0, "summary": summary_data},
            status_code=summary_resp.status_code,
            error=None
        )
    
# ========================================
    # ANALYTICS (for v2.0)
    # ========================================
    
    async def get_revenue_by_period(
        self,
        org_id: str,
        period: str = "MONTH"
    ) -> BackendResponse:
        """Get revenue breakdown by period"""
        return await self._request(
            "GET",
            "/api/v1/analytics/revenue",
            params={"organizationId": org_id, "period": period}
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("backend_adapter_closed")


# Lazy singleton accessor
_backend_adapter_instance = None

def get_backend_adapter() -> BackendHttpAdapter:
    """Return a singleton BackendHttpAdapter instance (lazy init)."""
    global _backend_adapter_instance
    if _backend_adapter_instance is None:
        _backend_adapter_instance = BackendHttpAdapter()
    return _backend_adapter_instance

