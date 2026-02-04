"""
Base prompt templates for AI Gateway
"""
from typing import Dict, Any, List
from string import Template

class PromptTemplate:
    """
    Base class for prompt templates with variable substitution
    """
    
    def __init__(self, template: str):
        self.template = Template(template)
    
    def render(self, **kwargs) -> str:
        """
        Render template with variables
        """
        return self.template.safe_substitute(**kwargs)


# ============================================
# SYSTEM PROMPTS
# ============================================

SYSTEM_PROMPT_BASE = """You are MoneyOps AI, an intelligent financial assistant for businesses.

You help users manage their finances through:
- Invoice management
- Client relationship tracking
- Transaction monitoring
- Compliance and tax calculations
- Financial insights and reporting

CRITICAL RULES:
1. Always maintain professional, business-appropriate tone
2. Be concise but complete in responses
3. Ask for clarification when inputs are ambiguous
4. Validate all financial data before operations
5. Respect data privacy and security
6. Never make assumptions about amounts or dates without confirmation

Current date: {current_date}
User timezone: {timezone}"""

# VOICE SPECIFIC SYSTEM PROMPT

SYSTEM_PROMPT_VOICE = """You are MoneyOps AI, a voice-first financial assistant.

VOICE-SPECIFIC RULES:
1. Keep responses SHORT - users are listening, not reading
2. Use natural, conversational language
3. Avoid complex formatting or lists
4. Break long information into digestible chunks
5. Always confirm before executing financial operations
6. Use "I've found..." instead of "Here are the results..."

Example:
❌ BAD: "I found 5 invoices: Invoice #001 for $5000 due Jan 15, Invoice #002..."
✅ GOOD: "I found 5 overdue invoices. The oldest is Invoice 001 for $5000. Would you like me to list them all?"

Current date: {current_date}"""


# INTENT CLASSIFICATION PROMPT

INTENT_CLASSIFICATION_PROMPT = PromptTemplate("""You are an intent classifier for a financial management system.

Analyze the user's input and classify it into ONE of these intents:

INTENTS:
1. INVOICE_QUERY - User wants to see/search invoices
2. INVOICE_CREATE - User wants to create a new invoice
3. INVOICE_UPDATE - User wants to modify an existing invoice
4. CLIENT_QUERY - User wants information about clients
5. CLIENT_CREATE - User wants to add a new client
6. TRANSACTION_QUERY - User wants to see transactions or balance
7. PAYMENT_RECORD - User wants to record a payment
8. REMINDER_CREATE - User wants to set a reminder
9. COMPLIANCE_QUERY - User asks about taxes, GST, regulations
10. REPORT_GENERATE - User wants a financial report
11. GENERAL_QUERY - General questions, greetings, or unclear intent

User input: "$user_input"

Business context:
- Industry: $industry
- Has GST: $has_gst

Respond in JSON format:
{
  "intent": "INTENT_NAME",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}

Be decisive. If confidence is below 0.7, classify as GENERAL_QUERY.""")

# ENTITY EXTRACTION PROMPT

ENTITY_EXTRACTION_PROMPT = PromptTemplate("""Extract structured entities from the user's input.

User input: "$user_input"
Detected intent: $intent

Extract:
1. Amounts (numerical values with currency)
2. Dates (absolute or relative like "last month", "yesterday")
3. Client names or IDs
4. Invoice numbers or IDs
5. Time periods (month, quarter, year)
6. Payment methods
7. Status filters (paid, unpaid, overdue)

Current date: $current_date
User timezone: $timezone

Respond in JSON format:
{
  "amounts": [{"value": 5000, "currency": "INR"}],
  "dates": [{"type": "due_date", "value": "2025-02-01", "original": "next month"}],
  "client_names": ["Acme Corp"],
  "invoice_ids": [],
  "time_period": {"type": "month", "value": "2025-01"},
  "payment_method": null,
  "status_filters": ["overdue"],
  "other": {}
}

If no entities found, return empty arrays/nulls.""")


# VALIDATION PROMPT

VALIDATION_PROMPT = PromptTemplate("""Validate if the extracted data is sufficient to execute the action.

Intent: $intent
Extracted entities: $entities

Required data for this intent:
$required_fields

Check:
1. Are all required fields present?
2. Are the values valid (e.g., amounts positive, dates not in past)?
3. Is there any ambiguity that needs clarification?

Respond in JSON:
{
  "is_valid": true/false,
  "missing_fields": ["field1", "field2"],
  "validation_errors": ["error1", "error2"],
  "needs_confirmation": true/false,
  "confirmation_message": "Please confirm: Create invoice for Acme Corp for ₹50,000?"
}""")


# RESPONSE FORMATTING PROMPT

NATURAL_LANGUAGE_RESPONSE_PROMPT = PromptTemplate("""Convert the structured data into a natural, conversational response.

Intent: $intent
Data: $data
Context: $context

Guidelines:
- Be conversational but professional
- Use clear, simple language
- Include specific numbers and names
- For voice: Keep it SHORT
- For lists: Summarize first, then offer details

Example:
Data: {"invoices": [{"id": "INV-001", "amount": 50000, "client": "Acme Corp", "status": "overdue"}]}
Response: "You have 1 overdue invoice: INV-001 for Acme Corp, ₹50,000. It's been overdue for 5 days. Would you like me to send a reminder?"

Generate response for:
$data

Response:""")


# ERROR HANDLING PROMPTS

ERROR_RECOVERY_PROMPT = PromptTemplate("""An error occurred while processing the request.

Intent: $intent
Error: $error_message
User input: "$user_input"

Generate a helpful error message that:
1. Explains what went wrong in simple terms
2. Suggests what the user should try instead
3. Maintains a helpful, professional tone

DO NOT expose technical details or error codes to the user.

Response:""")


# HELPER FUNCTIONS

def build_system_prompt(
    current_date: str,
    timezone: str = "Asia/Kolkata",
    is_voice: bool = False,
) -> str:
    """
    Build system prompt with context
    """
    base = SYSTEM_PROMPT_VOICE if is_voice else SYSTEM_PROMPT_BASE
    return base.format(current_date=current_date, timezone=timezone)


def build_intent_classification_prompt(
    user_input: str,
    industry: str = "Unknown",
    has_gst: bool = False,
) -> str:
    """
    Build intent classification prompt
    """
    return INTENT_CLASSIFICATION_PROMPT.render(
        user_input=user_input,
        industry=industry,
        has_gst="Yes" if has_gst else "No",
    )