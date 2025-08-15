"""Threaded RabbitMQ message handler for processing tweets with sentiment analysis.

This module implements a threaded message processing pattern based on the Pika
threaded consumer example, where each message is processed in a separate thread
to handle potentially long-running sentiment analysis operations.
"""

import functools
import json
import os
import threading
import time
from typing import Any, List
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from ..config.logging_config import get_logger
from ..core.mq_subscriber import MQSubscriber
from ..models.schemas import TokenDetails, SnipeAction, SnipeActionParams, TradeAction, AlignmentData
from ..core.sentiment_analyzer import get_trade_action
from .tweet import handle_tweet_event

logger = get_logger(__name__)


def ack_message(channel: BlockingChannel, delivery_tag: int) -> None:
    """Acknowledge message in a thread-safe manner.
    
    Args:
        channel: RabbitMQ channel to acknowledge on
        delivery_tag: Delivery tag of the message to acknowledge
    """
    if channel.is_open:
        channel.basic_ack(delivery_tag)
        logger.debug("Message acknowledged", delivery_tag=delivery_tag)
    else:
        logger.warning(
            "Cannot acknowledge message - channel is closed",
            delivery_tag=delivery_tag
        )


def nack_message(channel: BlockingChannel, delivery_tag: int, requeue: bool = False) -> None:
    """Negative acknowledge message in a thread-safe manner.
    
    Args:
        channel: RabbitMQ channel to nack on
        delivery_tag: Delivery tag of the message to nack
        requeue: Whether to requeue the message
    """
    if channel.is_open:
        channel.basic_nack(delivery_tag, requeue=requeue)
        logger.debug("Message nacked", delivery_tag=delivery_tag, requeue=requeue)
    else:
        logger.warning(
            "Cannot nack message - channel is closed",
            delivery_tag=delivery_tag
        )


def process_message_work(
    channel: BlockingChannel,
    delivery_tag: int,
    body: bytes,
    mq_subscriber: MQSubscriber
) -> None:
    """Process a single message in a dedicated thread.
    
    This function performs the actual work of processing a tweet message,
    including sentiment analysis and publishing snipe actions when tokens
    are detected.
    
    Args:
        channel: RabbitMQ channel for acknowledgments
        delivery_tag: Message delivery tag for acknowledgment
        body: Raw message body
        mq_subscriber: MQSubscriber instance for publishing snipe actions
    """
    thread_id = threading.get_ident()
    start_time = time.time()
    
    logger.info(
        "Starting message processing in thread",
        thread_id=thread_id,
        delivery_tag=delivery_tag,
        message_size=len(body)
    )
    
    try:
        # Decode message body
        message = body.decode('utf-8')
        
        # Parse JSON message
        try:
            tweet_data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON message received",
                thread_id=thread_id,
                delivery_tag=delivery_tag,
                error=str(e),
                message=message[:500] + "..." if len(message) > 500 else message
            )
            # Nack message without requeue for invalid JSON
            cb = functools.partial(nack_message, channel, delivery_tag, False)
            channel.connection.add_callback_threadsafe(cb)
            return
        
        try:
            # Process tweet with topic-priority analysis - this may take time
            logger.debug(
                "Starting topic-priority analysis",
                thread_id=thread_id,
                delivery_tag=delivery_tag
            )
            
            tweet_output, alignment_data = handle_tweet_event(tweet_data)
            
            processing_time = time.time() - start_time
            logger.info(
                "Topic-priority analysis completed",
                thread_id=thread_id,
                delivery_tag=delivery_tag,
                processing_time_seconds=round(processing_time, 2),
                has_sentiment_result=tweet_output.sentiment_analysis is not None,
                has_alignment_data=alignment_data is not None,
                alignment_score=alignment_data.score if alignment_data else None
            )
            
            # Get actions queue name from environment
            actions_queue = os.getenv("ACTIONS_QUEUE_NAME", "actions_to_take")
            
            # Check for token detection (sentiment analysis result)
            if (tweet_output.sentiment_analysis and 
                isinstance(tweet_output.sentiment_analysis, TokenDetails)):
                
                token_details = tweet_output.sentiment_analysis
                
                logger.info(
                    "Token detected - preparing snipe action",
                    thread_id=thread_id,
                    delivery_tag=delivery_tag,
                    token_address=token_details.token_address,
                    chain_id=token_details.chain_id,
                    chain_name=token_details.chain_name
                )
                
                # Create snipe action message
                snipe_params = SnipeActionParams(
                    chain_id=token_details.chain_id,
                    chain_name=token_details.chain_name,
                    token_address=token_details.token_address
                )
                snipe_action = SnipeAction(params=snipe_params)
                
                # Publish snipe action to actions queue
                try:
                    if mq_subscriber.publish(snipe_action, queue_name=actions_queue):
                        logger.info(
                            "Snipe action published successfully",
                            thread_id=thread_id,
                            delivery_tag=delivery_tag,
                            token_address=token_details.token_address,
                            chain_id=token_details.chain_id,
                            chain_name=token_details.chain_name,
                            actions_queue=actions_queue
                        )
                    else:
                        logger.warning(
                            "Failed to publish snipe action",
                            thread_id=thread_id,
                            delivery_tag=delivery_tag,
                            token_address=token_details.token_address,
                            actions_queue=actions_queue
                        )
                except Exception as publish_error:
                    logger.error(
                        "Error publishing snipe action",
                        thread_id=thread_id,
                        delivery_tag=delivery_tag,
                        error=str(publish_error),
                        token_address=token_details.token_address,
                        actions_queue=actions_queue
                    )
            
            # Check for topic sentiment (alignment data result)
            elif alignment_data is not None:
                logger.info(
                    "Topic sentiment detected - preparing trade action",
                    thread_id=thread_id,
                    delivery_tag=delivery_tag,
                    alignment_score=alignment_data.score,
                    explanation=alignment_data.explanation
                )
                
                # Create trade action using mock function
                trade_action = get_trade_action(alignment_data.score)
                
                # Publish trade action to actions queue
                try:
                    if mq_subscriber.publish(trade_action, queue_name=actions_queue):
                        logger.info(
                            "Trade action published successfully",
                            thread_id=thread_id,
                            delivery_tag=delivery_tag,
                            alignment_score=alignment_data.score,
                            actions_queue=actions_queue
                        )
                    else:
                        logger.warning(
                            "Failed to publish trade action",
                            thread_id=thread_id,
                            delivery_tag=delivery_tag,
                            alignment_score=alignment_data.score,
                            actions_queue=actions_queue
                        )
                except Exception as publish_error:
                    logger.error(
                        "Error publishing trade action",
                        thread_id=thread_id,
                        delivery_tag=delivery_tag,
                        error=str(publish_error),
                        alignment_score=alignment_data.score,
                        actions_queue=actions_queue
                    )
            
            else:
                logger.debug(
                    "No actionable result detected in message",
                    thread_id=thread_id,
                    delivery_tag=delivery_tag
                )
            
            # Successfully processed - acknowledge message
            cb = functools.partial(ack_message, channel, delivery_tag)
            channel.connection.add_callback_threadsafe(cb)
            
            total_time = time.time() - start_time
            logger.info(
                "Message processing completed successfully",
                thread_id=thread_id,
                delivery_tag=delivery_tag,
                total_processing_time_seconds=round(total_time, 2)
            )
            
        except Exception as e:
            logger.error(
                "Error during sentiment analysis or publishing",
                thread_id=thread_id,
                delivery_tag=delivery_tag,
                error=str(e),
                error_type=type(e).__name__,
                processing_time_seconds=round(time.time() - start_time, 2)
            )
            # Nack message without requeue for processing errors
            cb = functools.partial(nack_message, channel, delivery_tag, False)
            channel.connection.add_callback_threadsafe(cb)
            
    except Exception as e:
        logger.error(
            "Unexpected error in message processing thread",
            thread_id=thread_id,
            delivery_tag=delivery_tag,
            error=str(e),
            error_type=type(e).__name__
        )
        # Nack message without requeue for unexpected errors
        cb = functools.partial(nack_message, channel, delivery_tag, False)
        channel.connection.add_callback_threadsafe(cb)


def on_message(
    channel: BlockingChannel,
    method: Basic.Deliver,
    properties: BasicProperties,
    body: bytes,
    args: tuple
) -> None:
    """Handle incoming message by spawning a processing thread.
    
    This callback is invoked by Pika when a message is received. It creates
    a new thread to handle the potentially long-running sentiment analysis
    while allowing the main consumer thread to continue processing other messages.
    
    Args:
        channel: RabbitMQ channel
        method: Message delivery method containing routing info
        properties: Message properties
        body: Raw message body
        args: Tuple containing (threads_list, mq_subscriber)
    """
    threads, mq_subscriber = args
    delivery_tag = method.delivery_tag
    
    logger.debug(
        "Received message - spawning processing thread",
        delivery_tag=delivery_tag,
        routing_key=method.routing_key,
        exchange=method.exchange,
        message_size=len(body)
    )
    
    # Create and start processing thread
    thread = threading.Thread(
        target=process_message_work,
        args=(channel, delivery_tag, body, mq_subscriber),
        daemon=True  # Allow program to exit even if threads are running
    )
    thread.start()
    threads.append(thread)
    
    logger.debug(
        "Processing thread started",
        delivery_tag=delivery_tag,
        thread_id=thread.ident,
        active_threads=len([t for t in threads if t.is_alive()])
    )


class ThreadedMessageProcessor:
    """Threaded message processor that manages consumer threads and graceful shutdown."""
    
    def __init__(self, mq_subscriber: MQSubscriber):
        """Initialize threaded message processor.
        
        Args:
            mq_subscriber: MQSubscriber instance for publishing and connection management
        """
        self.mq_subscriber = mq_subscriber
        self.threads: List[threading.Thread] = []
        self.is_consuming = False
        
        logger.info("ThreadedMessageProcessor initialized")
    
    def create_message_handler(self):
        """Create a message handler function configured for threaded processing.
        
        Returns:
            Message handler function suitable for use with MQSubscriber
        """
        # Prepare callback arguments
        callback_args = (self.threads, self.mq_subscriber)
        
        # Create the callback with arguments bound
        message_callback = functools.partial(on_message, args=callback_args)
        
        logger.info("Threaded message handler created")
        return message_callback
    
    def start_processing(self):
        """Start the threaded message processing system."""
        if self.is_consuming:
            logger.warning("Threaded message processor is already running")
            return
        
        # Clear any old threads
        self.cleanup_finished_threads()
        
        # Create and set the message handler
        handler = self.create_message_handler()
        self.mq_subscriber.set_message_handler(handler)
        
        # Start consuming
        self.mq_subscriber.start_consuming()
        self.is_consuming = True
        
        logger.info("Threaded message processing started")
    
    def stop_processing(self, timeout: float = 30.0):
        """Stop processing and wait for all threads to complete.
        
        Args:
            timeout: Maximum time to wait for threads to complete (seconds)
        """
        if not self.is_consuming:
            logger.info("Threaded message processor is not running")
            return
        
        logger.info("Stopping threaded message processing...")
        
        # Stop consuming new messages
        self.mq_subscriber.stop_consuming()
        self.is_consuming = False
        
        # Wait for all processing threads to complete
        self.wait_for_threads(timeout)
        
        logger.info("Threaded message processing stopped")
    
    def cleanup_finished_threads(self):
        """Remove finished threads from the threads list."""
        before_count = len(self.threads)
        self.threads = [t for t in self.threads if t.is_alive()]
        after_count = len(self.threads)
        
        if before_count != after_count:
            logger.debug(
                "Cleaned up finished threads",
                removed_count=before_count - after_count,
                active_count=after_count
            )
    
    def wait_for_threads(self, timeout: float = 30.0):
        """Wait for all processing threads to complete.
        
        Args:
            timeout: Maximum time to wait for threads to complete (seconds)
        """
        active_threads = [t for t in self.threads if t.is_alive()]
        
        if not active_threads:
            logger.info("No active processing threads to wait for")
            return
        
        logger.info(
            "Waiting for processing threads to complete",
            active_thread_count=len(active_threads),
            timeout_seconds=timeout
        )
        
        start_time = time.time()
        
        for thread in active_threads:
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time <= 0:
                logger.warning(
                    "Timeout reached while waiting for threads",
                    remaining_threads=len([t for t in active_threads if t.is_alive()])
                )
                break
            
            thread.join(timeout=remaining_time)
            
            if thread.is_alive():
                logger.warning(
                    "Processing thread did not complete within timeout",
                    thread_id=thread.ident
                )
        
        # Final cleanup
        self.cleanup_finished_threads()
        
        final_active = len([t for t in self.threads if t.is_alive()])
        if final_active == 0:
            logger.info("All processing threads completed successfully")
        else:
            logger.warning(
                "Some processing threads are still active after timeout",
                active_count=final_active
            )
    
    def get_status(self) -> dict:
        """Get current status of the threaded processor.
        
        Returns:
            Dictionary with processor status information
        """
        self.cleanup_finished_threads()
        
        return {
            "is_consuming": self.is_consuming,
            "active_threads": len([t for t in self.threads if t.is_alive()]),
            "total_threads_created": len(self.threads),
            "mq_consumer_active": self.mq_subscriber.is_consuming(),
            "mq_publisher_connected": self.mq_subscriber.is_publisher_connected()
        }


def create_threaded_message_handler(mq_subscriber: MQSubscriber) -> ThreadedMessageProcessor:
    """Factory function to create a threaded message processor.
    
    Args:
        mq_subscriber: MQSubscriber instance for message processing
        
    Returns:
        Configured ThreadedMessageProcessor instance
    """
    processor = ThreadedMessageProcessor(mq_subscriber)
    logger.info("Threaded message handler factory created processor")
    return processor