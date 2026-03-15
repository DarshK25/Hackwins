"""
Backend HTTP adapter: http client for backend core API
Handles all communication with Springboot backend
"""
from typing import Dict, Any, List, Optional, Literal
import httpx
import re
import datetime
import time
from pydantic import BaseModel, Field, field_validator
from rapidfuzz import process, fuzz

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class OrgIsolationError(Exception):
    """Raised when an operation violates organization isolation rules."""
    pass

class ClientRecord(BaseModel):
    id: str                          
    display_name: str                
    backend_name: str                
    email: Optional[str] = None
    status: Literal["ACTIVE", "INACTIVE"]
    org_id: str                      

class BackendResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int

class BackendHttpAdapter:
    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None):
        self.base_url = base_url or settings.BACKEND_BASE_URL
        self.timeout = getattr(settings, "BACKEND_TIMEOUT", 30)
        self.auth_token = auth_token
        
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent":  "MoneyOps-AI-Gateway/1.0",
            "X-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
        }
        
        if self.auth_token:
            default_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=default_headers
        )
        
        self._onboarding_cache: Dict[str, tuple[bool, float]] = {}
        self._org_uuid_cache: Dict[str, str] = {}
        self._ONBOARDING_TTL = 300
        
        logger.info("backend_adapter_initialized", base_url=self.base_url)

    async def resolve_org_uuid(self, clerk_id: str) -> Optional[str]:
        if not clerk_id or clerk_id == "unknown": return None
        if clerk_id in self._org_uuid_cache: return self._org_uuid_cache[clerk_id]
        
        resp = await self.get_onboarding_status(clerk_id)
        if resp.success and resp.data:
            data = resp.data.get("data") if isinstance(resp.data, dict) and "data" in resp.data else resp.data
            org_uuid = data.get("orgId") or data.get("orgUuid") or data.get("organizationId")
            if org_uuid:
                self._org_uuid_cache[clerk_id] = org_uuid
                return org_uuid
        return None

    async def _get_headers(self, org_id: Optional[str] = None, user_id: Optional[str] = None, extra_headers: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Build headers with resolved internal org UUID."""
        headers = self.client.headers.copy()
        
        if org_id:
            internal_uuid = org_id
            if org_id.startswith("org_") or org_id.startswith("user_"):
                # Use user_id for resolution if available, fallback to org_id
                resolution_key = user_id or org_id
                resolved = await self.resolve_org_uuid(resolution_key)
                if resolved:
                    internal_uuid = resolved
            headers["X-Org-Id"] = internal_uuid

        if user_id:
            headers["X-User-Id"] = user_id
            
        if extra_headers:
            headers.update(extra_headers)
            
        return headers

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, 
                      params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None,
                      org_id: Optional[str] = None, user_id: Optional[str] = None) -> BackendResponse:
        url = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        req_headers = await self._get_headers(org_id, user_id, headers)

        try:
            response = await self.client.request(method=method, url=url, json=data, params=params, headers=req_headers)
            success = 200 <= response.status_code < 300
            
            try:
                response_data = response.json() if response.text else None
            except:
                response_data = {"text": response.text}
            
            error_msg = response_data.get("message") or response_data.get("error") if isinstance(response_data, dict) else None
            if not success and not error_msg:
                error_msg = f"Backend error: {response.status_code}"
                
            return BackendResponse(success=success, data=response_data, status_code=response.status_code, error=error_msg)
        except Exception as e:
            logger.error("backend_request_error", endpoint=endpoint, error=str(e))
            return BackendResponse(success=False, error=str(e), status_code=500)

    async def get_onboarding_status(self, clerk_id: str) -> BackendResponse:
        if clerk_id in self._onboarding_cache:
            status, ts = self._onboarding_cache[clerk_id]
            if time.time() - ts < self._ONBOARDING_TTL:
                return BackendResponse(success=True, data={"onboarded": status}, status_code=200)

        resp = await self._request("GET", "/api/onboarding/status", params={"clerkId": clerk_id})
        if resp.success and resp.data:
            data = resp.data.get("data") if isinstance(resp.data, dict) and "data" in resp.data else resp.data
            onboarded = data.get("onboardingComplete", False) or data.get("orgId") is not None
            self._onboarding_cache[clerk_id] = (bool(onboarded), time.time())
            resp.data = data
        return resp

    async def create_invoice_direct(self, org_id: str, user_id: str, payload: Dict[str, Any]) -> BackendResponse:
        return await self._request("POST", "/api/invoices", data=payload, org_id=org_id, user_id=user_id)

    async def get_clients(self, org_id: str, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        resp = await self._request("GET", "/api/clients", params={"limit": limit}, org_id=org_id, user_id=user_id)
        if resp.success and resp.data:
            return resp.data if isinstance(resp.data, list) else resp.data.get("clients", [])
        return []

    async def get_finance_metrics(self, business_id: int, org_id: str, user_id: Optional[str] = None) -> BackendResponse:
        return await self._request("GET", "/api/finance-intelligence/metrics", params={"businessId": business_id}, org_id=org_id, user_id=user_id)

    def set_auth_token(self, token: str):
        self.auth_token = token
        self.client.headers["Authorization"] = f"Bearer {token}"

_backend_adapter_instance = None
def get_backend_adapter(auth_token: Optional[str] = None) -> BackendHttpAdapter:
    global _backend_adapter_instance
    if _backend_adapter_instance is None:
        _backend_adapter_instance = BackendHttpAdapter(auth_token=auth_token)
    elif auth_token:
        _backend_adapter_instance.set_auth_token(auth_token)
    return _backend_adapter_instance
