"""
Twilio WhatsApp/SMS Integration for Collections Engine.
Works instantly - no Meta Business Account approval needed.
"""
from typing import Optional, Dict, Any, List
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TwilioManager:
    """
    Manages Twilio WhatsApp and SMS sending.
    Instant setup - no approval delays.
    """

    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.sms_from = getattr(settings, "TWILIO_SMS_FROM", "")

        if self.account_sid and self.auth_token:
            self.client = TwilioClient(self.account_sid, self.auth_token)
            logger.info("twilio_initialized", has_whatsapp=bool(self.whatsapp_from), has_sms=bool(self.sms_from))
        else:
            self.client = None
            logger.warning("twilio_not_configured", message="Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")

    async def send_whatsapp(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send WhatsApp message via Twilio.
        to: Phone number with country code (e.g., +911234567890)
        """
        if not self.client:
            return {"success": False, "error": "Twilio not configured"}

        # Ensure whatsapp: prefix
        to_formatted = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        from_formatted = self.whatsapp_from

        try:
            message = self.client.messages.create(
                from_=from_formatted,
                body=message,
                to=to_formatted
            )
            logger.info("whatsapp_sent", to=to, message_sid=message.sid)
            return {"success": True, "message_sid": message.sid, "status": message.status}
        except TwilioRestException as e:
            logger.error("whatsapp_error", code=e.code, message=e.msg)
            return {"success": False, "error": f"Twilio error {e.code}: {e.msg}"}
        except Exception as e:
            logger.error("whatsapp_exception", error=str(e))
            return {"success": False, "error": str(e)}

    async def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Twilio (higher open rate, instant).
        to: Phone number with country code (e.g., +911234567890)
        """
        if not self.client:
            return {"success": False, "error": "Twilio not configured"}

        if not self.sms_from:
            return {"success": False, "error": "TWILIO_SMS_FROM not configured"}

        try:
            message = self.client.messages.create(
                from_=self.sms_from,
                body=message,
                to=to
            )
            logger.info("sms_sent", to=to, message_sid=message.sid)
            return {"success": True, "message_sid": message.sid, "status": message.status}
        except TwilioRestException as e:
            logger.error("sms_error", code=e.code, message=e.msg)
            return {"success": False, "error": f"Twilio error {e.code}: {e.msg}"}
        except Exception as e:
            logger.error("sms_exception", error=str(e))
            return {"success": False, "error": str(e)}

    async def send_bulk_reminders(
        self,
        reminders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send bulk reminders for collections.
        reminders: [{"phone": "+911234567890", "client": "Acme Corp", "amount": 5000, ...}]
        """
        results = {"sent": 0, "failed": 0, "errors": []}

        for reminder in reminders:
            phone = reminder.get("phone", "")
            client = reminder.get("client", "Client")
            amount = reminder.get("amount", 0)
            days = reminder.get("days_overdue", 0)

            if not phone:
                results["failed"] += 1
                continue

            message = f"Hi {client}, your invoice of ₹{amount:,.0f} is overdue by {days} days. Please pay now to avoid escalation. Thank you!"

            # Try WhatsApp first, fallback to SMS
            result = await self.send_whatsapp(phone, message)
            if not result["success"] and self.sms_from:
                result = await self.send_sms(phone, message)

            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{client}: {result.get('error')}")

        return results


# Singleton instance
twilio_manager = TwilioManager()
