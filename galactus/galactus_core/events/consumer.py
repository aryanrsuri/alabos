"""
Kafka event consumer for Galactus.
"""

import json
import logging
import threading
from typing import Callable, Dict, List, Optional
from uuid import UUID

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..database.config import db_settings
from ..models.base import EventBase, KafkaEvent
from ..database.connection import get_db_session_sync

logger = logging.getLogger(__name__)


class EventConsumer:
    """Kafka event consumer for Galactus events."""

    def __init__(self):
        self.consumer = KafkaConsumer(
            bootstrap_servers=db_settings.kafka_bootstrap_servers.split(','),
            group_id=db_settings.kafka_group_id,
            client_id=db_settings.kafka_client_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda m: m.decode('utf-8') if m else None,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            consumer_timeout_ms=1000,
        )
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.consumer_thread: Optional[threading.Thread] = None

    def subscribe_to_topics(self, topics: List[str]):
        """Subscribe to Kafka topics."""
        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            logger.error(f"Error subscribing to topics {topics}: {e}")

    def subscribe_to_entity_events(self, entity_type: str, event_types: List[str]):
        """Subscribe to events for a specific entity type."""
        topics = [f"galactus.{entity_type}.{event_type}" for event_type in event_types]
        self.subscribe_to_topics(topics)

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register an event handler.

        Args:
            event_type: Type of event to handle (e.g., "task.created", "workflow.completed")
            handler: Function to handle the event. Should accept (event: EventBase) -> None
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    def _handle_message(self, message):
        """Handle a single Kafka message."""
        try:
            # Parse event
            event_data = message.value
            event = EventBase(**event_data)

            # Log to TimescaleDB
            self._log_event_to_db(event)

            # Find and execute handlers
            event_type_key = f"{event.entity_type}.{event.event_type}"
            handlers = self.handlers.get(event_type_key, [])

            if handlers:
                for handler in handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type_key}: {e}")
            else:
                logger.debug(f"No handlers found for event type: {event_type_key}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _log_event_to_db(self, event: EventBase):
        """Log event to TimescaleDB for time-series analysis."""
        try:
            with get_db_session_sync() as session:
                kafka_event = KafkaEvent(
                    event_type=event.event_type,
                    entity_id=event.entity_id,
                    entity_type=event.entity_type,
                    payload=event.data
                )
                session.add(kafka_event)
                session.commit()
        except Exception as e:
            logger.error(f"Error logging event to database: {e}")

    def _consume_messages(self):
        """Main consumer loop."""
        logger.info("Starting event consumer loop")

        try:
            for message in self.consumer:
                if not self.running:
                    break

                self._handle_message(message)

                # Manual commit after successful processing
                self.consumer.commit()

        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            logger.info("Event consumer loop ended")

    def start(self):
        """Start the consumer in a background thread."""
        if self.running:
            logger.warning("Consumer is already running")
            return

        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self.consumer_thread.start()
        logger.info("Event consumer started")

    def stop(self):
        """Stop the consumer."""
        if not self.running:
            logger.warning("Consumer is not running")
            return

        logger.info("Stopping event consumer...")
        self.running = False

        if self.consumer_thread:
            self.consumer_thread.join(timeout=10)

        self.consumer.close()
        logger.info("Event consumer stopped")

    def health_check(self) -> bool:
        """Check if the consumer is healthy."""
        return self.running and self.consumer_thread and self.consumer_thread.is_alive()
