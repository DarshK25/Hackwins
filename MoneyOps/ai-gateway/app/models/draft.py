from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict
from enum import Enum
import uuid
import time

@dataclass
class AgentResponse:
    text: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    ui_event: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None
    error: Optional[str] = None
    intent: Optional[str] = None

@dataclass
class InvoiceDraft:
    draft_id: str
    session_id: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    client_query: Optional[str] = None
    item_type: Optional[str] = None
    item_description: Optional[str] = None
    quantity: Optional[int] = None
    amount: Optional[float] = None
    gst_percent: Optional[float] = None
    gst_applicable: Optional[bool] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    team_action_code: Optional[str] = None
    confirmed: bool = False
    line_items: List[Any] = field(default_factory=list)
    current_stage: str = "COLLECT_INITIAL"
    last_question_asked: Optional[str] = None
    locked_intent: Optional[str] = "INVOICE_CREATE"
    turn_count: int = 0
    team_code_attempts: int = 0
    awaiting_team_code: bool = False
    awaiting_confirmation: bool = False
    last_summary: Optional[str] = None
    
    def missing_required_fields(self) -> List[str]:
        missing = []
        if not self.client_id: missing.append("client")
        if not self.item_type: missing.append("item_type")
        if not self.item_description: missing.append("item_description")
        if self.amount is None: missing.append("amount")
        if self.item_type == "PRODUCT" and (self.quantity is None or self.quantity <= 0):
            missing.append("quantity")
        if self.gst_applicable is None: missing.append("gst")
        if not self.due_date: missing.append("due_date")
        return missing
    
    def is_ready_to_create(self) -> bool:
        return len(self.missing_required_fields()) == 0
