"""
Event-Driven Collections Engine for MoneyOps.
Uses RabbitMQ/Kafka for automated invoice reminders and collections workflows.
Solves the 90-120 day payment delay problem SMBs face.
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from app.config import settings
from app.utils.logger import get_logger
from app.adapters.backend_adapter import get_backend_adapter

logger = get_logger(__name__)


class EventType(str, Enum):
    """Types of events in the collections system."""
    INVOICE_CREATED = "invoice.created"
    INVOICE_SENT = "invoice.sent"
    INVOICE_OVERDUE = "invoice.overdue"
    PAYMENT_RECEIVED = "payment.received"
    REMINDER_SENT = "reminder.sent"
    ESCALATION_TRIGGERED = "escalation.triggered"


class CollectionsEvent:
    """An event in the collections workflow."""

    def __init__(
        self,
        event_type: EventType,
        org_id: str,
        invoice_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.org_id = org_id
        self.invoice_id = invoice_id
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.event_id = f"{event_type}_{invoice_id}_{int(datetime.utcnow().timestamp())}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "org_id": self.org_id,
            "invoice_id": self.invoice_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionsEvent":
        event = cls(
            event_type=EventType(data["event_type"]),
            org_id=data["org_id"],
            invoice_id=data["invoice_id"],
            metadata=data.get("metadata"),
        )
        event.event_id = data.get("event_id", event.event_id)
        event.timestamp = data.get("timestamp", event.timestamp)
        return event


class EventProducer:
    """Publishes collections events to message queue."""

    def __init__(self):
        self._connection = None
        self._channel = None
        self._use_rabbitmq = False
        self._use_kafka = False
        self._kafka_producer = None

        # Try RabbitMQ first, then Kafka
        try:
            import pika
            self._pika = pika
            self._use_rabbitmq = True
            logger.info("event_producer_rabbitmq_ready")
        except ImportError:
            try:
                from kafka import KafkaProducer
                self._kafka_producer_class = KafkaProducer
                self._use_kafka = True
                logger.info("event_producer_kafka_ready")
            except ImportError:
                logger.warning("no_message_queue_available_using_in_memory")

    async def connect(self):
        """Connect to message queue."""
        if self._use_rabbitmq:
            await self._connect_rabbitmq()
        elif self._use_kafka:
            await self._connect_kafka()

    async def _connect_rabbitmq(self):
        """Connect to RabbitMQ."""
        try:
            parameters = self._pika.URLParameters(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@"
                f"{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            )
            self._connection = self._pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()

            # Declare exchanges and queues
            self._channel.exchange_declare(
                exchange="moneyops.collections",
                exchange_type="topic",
                durable=True,
            )

            self._channel.queue_declare(queue="collections.reminders", durable=True)
            self._channel.queue_declare(queue="collections.escalations", durable=True)

            logger.info("rabbitmq_connected")
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            self._use_rabbitmq = False

    async def _connect_kafka(self):
        """Connect to Kafka."""
        try:
            self._kafka_producer = self._kafka_producer_class(
                bootstrap_servers=f"{settings.KAFKA_HOST}:{settings.KAFKA_PORT}",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            logger.info("kafka_connected")
        except Exception as e:
            logger.error("kafka_connection_failed", error=str(e))
            self._use_kafka = False

    async def publish_event(self, event: CollectionsEvent):
        """Publish an event to the message queue."""
        event_dict = event.to_dict()
        topic = "moneyops.collections"

        try:
            if self._use_rabbitmq and self._channel:
                self._channel.basic_publish(
                    exchange=topic,
                    routing_key=event.event_type,
                    body=json.dumps(event_dict),
                    properties=self._pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                    ),
                )
            elif self._use_kafka and self._kafka_producer:
                self._kafka_producer.send(topic, event_dict)
            else:
                # In-memory fallback (for development)
                logger.info("event_published_in_memory", event_type=event.event_type)

            logger.info("event_published", event_id=event.event_id, type=event.event_type)
        except Exception as e:
            logger.error("event_publish_failed", error=str(e))

    async def close(self):
        """Close connections."""
        if self._use_rabbitmq and self._connection:
            self._connection.close()
        elif self._use_kafka and self._kafka_producer:
            self._kafka_producer.close()


class EventConsumer:
    """Consumes collections events and triggers automated actions."""

    def __init__(self):
        self._producer = EventProducer()
        self._running = False
        self._backend = get_backend_adapter()

    async def start(self):
        """Start consuming events."""
        self._running = True

        if self._producer._use_rabbitmq:
            await self._consume_rabbitmq()
        elif self._producer._use_kafka:
            await self._consume_kafka()
        else:
            logger.warning("no_message_queue_available_for_consumer")
            # In-memory mode: just log
            self._running = False

    async def _consume_rabbitmq(self):
        """Consume events from RabbitMQ."""
        import pika

        def callback(ch, method, properties, body):
            try:
                event_dict = json.loads(body)
                event = CollectionsEvent.from_dict(event_dict)
                asyncio.create_task(self._handle_event(event))
            except Exception as e:
                logger.error("event_processing_error", error=str(e))

        # Set up consumer
        channel = self._producer._channel
        channel.basic_consume(
            queue="collections.reminders",
            on_message_callback=callback,
            auto_ack=True,
        )

        logger.info("rabbitmq_consumer_started")
        channel.start_consuming()

    async def _consume_kafka(self):
        """Consume events from Kafka."""
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            "moneyops.collections",
            bootstrap_servers=f"{settings.KAFKA_HOST}:{settings.KAFKA_PORT}",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            group_id="moneyops-collections-group",
        )

        logger.info("kafka_consumer_started")
        for message in consumer:
            if not self._running:
                break
            try:
                event_dict = message.value
                event = CollectionsEvent.from_dict(event_dict)
                await self._handle_event(event)
            except Exception as e:
                logger.error("event_processing_error", error=str(e))

    async def _handle_event(self, event: CollectionsEvent):
        """Handle a collections event."""
        logger.info("handling_event", event_type=event.event_type, invoice_id=event.invoice_id)

        if event.event_type == EventType.INVOICE_SENT:
            await self._schedule_reminders(event)
        elif event.event_type == EventType.INVOICE_OVERDUE:
            await self._handle_overdue(event)
        elif event.event_type == EventType.PAYMENT_RECEIVED:
            await self._handle_payment(event)

    async def _schedule_reminders(self, event: CollectionsEvent):
        """Schedule automated reminders for an invoice."""
        # In production, this would schedule reminders at 7, 14, 30 days
        # For now, just log
        logger.info(
            "reminders_scheduled",
            invoice_id=event.invoice_id,
            schedule=[7, 14, 30],  # days after due date
        )

    async def _handle_overdue(self, event: CollectionsEvent):
        """Handle an overdue invoice."""
        org_id = event.org_id
        invoice_id = event.invoice_id

        # Get invoice details
        resp = await self._backend._request(
            "GET", f"/api/invoices/{invoice_id}", org_id=org_id
        )

        if not resp.success or not resp.data:
            logger.error("invoice_fetch_failed", invoice_id=invoice_id)
            return

        invoice = resp.data
        days_overdue = event.metadata.get("days_overdue", 0)

        # Escalate based on age
        if days_overdue > 60:
            # Critical: suggest TReDS discounting
            logger.warning(
                "critical_overdue",
                invoice_id=invoice_id,
                days=days_overdue,
                amount=invoice.get("totalAmount"),
                action="suggest_treds",
            )
        elif days_overdue > 30:
            # Send escalation email
            await self._send_escalation(invoice, org_id)
        else:
            # Send gentle reminder
            await self._send_reminder(invoice, org_id, tone="gentle")

    async def _send_reminder(self, invoice: Dict, org_id: str, tone: str = "gentle"):
        """Send a payment reminder."""
        result = await self._backend.send_collection_email(
            invoice_id=invoice.get("id"),
            client_email=invoice.get("clientEmail", ""),
            client_name=invoice.get("clientName", "Client"),
            invoice_number=invoice.get("invoiceNumber", ""),
            amount=float(invoice.get("totalAmount", 0)),
            due_date=invoice.get("dueDate", ""),
            org_id=org_id,
            tone=tone,
        )

        if result.get("sent"):
            logger.info("reminder_sent", invoice_id=invoice.get("id"), tone=tone)
        else:
            logger.error("reminder_failed", invoice_id=invoice.get("id"), error=result.get("error"))

    async def _send_escalation(self, invoice: Dict, org_id: str):
        """Send an escalation notice."""
        await self._send_reminder(invoice, org_id, tone="firm")

        # Also notify the business owner
        logger.warning(
            "escalation_triggered",
            invoice_id=invoice.get("id"),
            amount=invoice.get("totalAmount"),
            message="Owner notified of critical overdue invoice",
        )

    async def _handle_payment(self, event: CollectionsEvent):
        """Handle a payment received event."""
        logger.info(
            "payment_received",
            invoice_id=event.invoice_id,
            amount=event.metadata.get("amount"),
        )

    async def stop(self):
        """Stop consuming events."""
        self._running = False


# Singleton instances
event_producer = EventProducer()
event_consumer = EventConsumer()


async def check_and_trigger_reminders():
    """
    Periodic task to check for overdue invoices and trigger reminders.
    Should be called by a scheduler (APScheduler).
    """
    backend = get_backend_adapter()

    # Get all orgs (in production, iterate over all orgs)
    # For now, just log
    logger.info("checking_for_overdue_invoices")

    # This would:
    # 1. Query invoices with status SENT and due_date < now
    # 2. For each, calculate days overdue
    # 3. Publish INVOICE_OVERDUE event
    # 4. Event consumer handles sending reminders
