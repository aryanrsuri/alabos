"""
Kafka event producer for Galactus.
"""

import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from kafka import KafkaProducer
from kafka.errors import KafkaError

from ..database.config import db_settings
from ..models.base import EventBase, EventType

logger = logging.getLogger(__name__)


class EventProducer:
    """Kafka event producer for Galactus events."""

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=db_settings.kafka_bootstrap_servers.split(','),
            client_id=db_settings.kafka_client_id,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda v: str(v).encode('utf-8') if v else None,
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            retry_backoff_ms=1000,
        )
        self.topic_prefix = "galactus."

    def _get_topic_name(self, entity_type: str, event_type: str) -> str:
        """Generate topic name from entity and event type."""
        return f"{self.topic_prefix}{entity_type}.{event_type}"

    def send_event(
        self,
        event_type: str,
        entity_id: UUID,
        entity_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Send an event to Kafka.

        Args:
            event_type: Type of event (e.g., 'created', 'started', 'completed')
            entity_id: ID of the entity this event relates to
            entity_type: Type of entity ('task', 'workflow', 'device', etc.)
            data: Event payload data
            key: Optional message key for partitioning

        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        try:
            # Create event object
            event = EventBase(
                event_type=event_type,
                entity_id=entity_id,
                entity_type=entity_type,
                data=data
            )

            # Determine topic
            topic = self._get_topic_name(entity_type, event_type)

            # Send to Kafka
            future = self.producer.send(
                topic=topic,
                key=key or str(entity_id),
                value=event.dict()
            )

            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Event sent successfully: {event_type} for {entity_type} {entity_id} "
                f"to topic {topic} at offset {record_metadata.offset}"
            )

            return True

        except KafkaError as e:
            logger.error(f"Failed to send event {event_type} for {entity_type} {entity_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending event: {e}")
            return False

    def send_task_event(
        self,
        task_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send a task-related event."""
        return self.send_event(event_type, task_id, "task", data, key)

    def send_workflow_event(
        self,
        workflow_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send a workflow-related event."""
        return self.send_event(event_type, workflow_id, "workflow", data, key)

    def send_device_event(
        self,
        device_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send a device-related event."""
        return self.send_event(event_type, device_id, "device", data, key)

    def send_sample_event(
        self,
        sample_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send a sample-related event."""
        return self.send_event(event_type, sample_id, "sample", data, key)

    def send_job_event(
        self,
        job_id: UUID,
        event_type: str,
        data: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """Send a job-related event."""
        return self.send_event(event_type, job_id, "job", data, key)

    def flush(self):
        """Flush all pending messages."""
        try:
            self.producer.flush(timeout=10)
            logger.info("All pending messages flushed")
        except Exception as e:
            logger.error(f"Error flushing messages: {e}")

    def close(self):
        """Close the producer."""
        try:
            self.flush()
            self.producer.close(timeout=10)
            logger.info("Event producer closed")
        except Exception as e:
            logger.error(f"Error closing producer: {e}")


# Global event producer instance
event_producer = EventProducer()
