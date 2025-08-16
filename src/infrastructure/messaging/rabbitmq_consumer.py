"""
RabbitMQ implementation of MessageQueue
"""
import json
import logging
import asyncio
import uuid
from typing import Dict, Any, Callable, Optional
from datetime import datetime

import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

from ...application.interfaces import MessageQueue
from ...domain.entities import Message

logger = logging.getLogger(__name__)


class RabbitMQConsumer(MessageQueue):
    """RabbitMQ implementation for consuming messages"""
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        virtual_host: str,
        exchange_name: str,
        queue_prefix: str
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.exchange_name = exchange_name
        self.queue_prefix = queue_prefix
        
        self.connection = None
        self.channel = None
        self.consumer_tag = None
        self.handler = None
        self._consuming = False
    
    async def connect(self) -> None:
        """Connect to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            # Use blocking connection for simplicity (can be converted to async later)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            # Create an exclusive queue for this consumer
            result = self.channel.queue_declare(
                queue='', 
                exclusive=True,
                durable=True
            )
            queue_name = result.method.queue
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=queue_name,
                routing_key='speech.created'
            )
            
            # Set QoS
            self.channel.basic_qos(prefetch_count=1)
            
            # Store queue name
            self.queue_name = queue_name
            
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        try:
            if self.consumer_tag:
                self.channel.basic_cancel(self.consumer_tag)
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")
    
    async def consume(self, handler: Callable[[Message], None]) -> None:
        """Start consuming messages"""
        self.handler = handler
        self._consuming = True
        
        def callback(ch, method, properties, body):
            """Handle incoming message"""
            try:
                # Parse message
                data = json.loads(body.decode('utf-8'))
                
                # Log message structure for debugging
                logger.info(f"Received message with id: {data.get('id', 'unknown')}")
                logger.info(f"Full message content: {json.dumps(data, indent=2)}")
                
                # The actual message structure from rabbitmq_consumer_with_audio_chunked.py:
                # - 'id' instead of 'uuid'
                # - The data might not have 'event_type' at root level
                
                # Create Message entity with proper field mapping
                message = Message(
                    id=data.get('id', data.get('uuid', str(uuid.uuid4()))),
                    event_type=data.get('event_type', data.get('type', 'speech.created')),  # Default to speech.created
                    data=data.get('data', {}),
                    timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                    retry_count=data.get('retryCount', 0),
                    metadata=data.get('metadata', {})
                )
                
                # Call handler
                asyncio.create_task(self._handle_message(message))
                
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Reject message and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # Start consuming
        self.consumer_tag = self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        
        logger.info("Started consuming messages")
        
        # Keep consuming until stopped
        try:
            while self._consuming:
                self.connection.process_data_events(time_limit=1)
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self._consuming = False
    
    async def _handle_message(self, message: Message) -> None:
        """Handle message asynchronously"""
        if self.handler:
            try:
                await self.handler(message)
            except Exception as e:
                logger.error(f"Handler error: {str(e)}")
    
    async def publish(self, message: Message, routing_key: str) -> None:
        """Publish message to RabbitMQ"""
        try:
            # Convert message to dict
            message_dict = {
                'uuid': message.id,
                'event_type': message.event_type,
                'timestamp': message.timestamp.isoformat(),
                'data': message.data,
                'metadata': message.metadata
            }
            
            # Publish message
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=json.dumps(message_dict),
                properties=BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Published message with routing key: {routing_key}")
            
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
    
    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ"""
        return self.connection is not None and not self.connection.is_closed
    
    async def get_queue_size(self) -> int:
        """Get number of messages in queue"""
        try:
            method = self.channel.queue_declare(
                queue=self.queue_name,
                passive=True
            )
            return method.method.message_count
        except:
            return 0
    
    async def acknowledge(self, message_id: str) -> None:
        """Acknowledge message processing - handled in consume callback"""
        # In our implementation, acknowledgment is handled directly
        # in the consume callback, so this is a no-op
        logger.debug(f"Message {message_id} already acknowledged in callback")
    
    async def reject(self, message_id: str, requeue: bool = False) -> None:
        """Reject message - handled in consume callback"""
        # In our implementation, rejection is handled directly
        # in the consume callback, so this is a no-op
        logger.debug(f"Message {message_id} rejection handled in callback")