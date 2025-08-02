import json
import os
import signal
import time
from typing import Any, Optional
from dotenv import load_dotenv
from src.config.logging_config import setup_logging, get_logger
from src.config.logfire_config import initialize_logfire
from src.core.mq_subscriber import MQSubscriber
from src.core.rabbitmq_monitor import RabbitMQConnectionMonitor
from src.handlers.tweet import handle_tweet_event
from src.models.schemas import TokenDetails, SnipeAction, SnipeActionParams

# Initialize module-level logger
setup_logging()  # Auto-detects environment
logger = get_logger(__name__)
# Global shutdown flag
shutdown_requested = False


def initialize_rabbitmq() -> MQSubscriber:
    """Initialize and test RabbitMQ connection at startup.
    
    Returns:
        MQSubscriber: Successfully connected and validated MQSubscriber instance
        
    Raises:
        SystemExit: If RabbitMQ connection cannot be established or validated
    """
    try:
        logger.info("Initializing RabbitMQ connection...")
        subscriber = MQSubscriber.from_env(connect_on_init=True)
        
        # Test the connection
        if not subscriber.test_connection():
            logger.error("RabbitMQ connection test failed - shutting down")
            raise Exception("RabbitMQ connection validation failed")
        
        logger.info("RabbitMQ connection validated successfully")
        return subscriber
        
    except Exception as e:
        logger.error(
            "Failed to establish RabbitMQ connection at startup",
            error=str(e)
        )
        raise SystemExit(1)

def initialize_rabbitmq_monitor(mq_subscriber: MQSubscriber) -> Optional[RabbitMQConnectionMonitor]:
    """Initialize RabbitMQ connection monitor if enabled."""
    if os.getenv("RABBITMQ_MONITOR_ENABLED", "true").lower() == "true":
        connection_monitor = RabbitMQConnectionMonitor.from_env(mq_subscriber)
        connection_monitor.start()
        logger.info("RabbitMQ connection monitoring enabled")
        return connection_monitor
    else:
        logger.info("RabbitMQ connection monitoring disabled")
        return None

def create_message_handler(mq_subscriber: MQSubscriber):
    """Factory function that creates a message handler with MQSubscriber dependency injected.
    
    Args:
        mq_subscriber: MQSubscriber instance for publishing snipe actions
        
    Returns:
        Configured message handler function
    """
    def message_handler(channel, method, properties, body):
        """Message handler that processes tweets and publishes snipe actions for token detections."""
        try:
            message = body.decode('utf-8')
            logger.info(
                "Received message from RabbitMQ",
                routing_key=method.routing_key,
                exchange=method.exchange,
                message_size=len(message),
                message_preview=message[:200] + "..." if len(message) > 200 else message
            )

            try:
                # Parse JSON message to dictionary
                tweet_data = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(
                    "Invalid JSON message received",
                    error=str(e),
                    message=message[:500] + "..." if len(message) > 500 else message
                )
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
                
            try:
                # Analyze the tweet sentiment
                tweet_output = handle_tweet_event(tweet_data)
                
                # Check if sentiment analysis detected token details
                if (tweet_output.sentiment_analysis and 
                    isinstance(tweet_output.sentiment_analysis, TokenDetails)):
                    
                    token_details = tweet_output.sentiment_analysis
                    
                    # Create snipe action message
                    snipe_params = SnipeActionParams(
                        chain_id=token_details.chain_id,
                        chain_name=token_details.chain_name,
                        token_address=token_details.token_address
                    )
                    snipe_action = SnipeAction(params=snipe_params)
                    
                    # Get actions queue name from environment
                    actions_queue = os.getenv("ACTIONS_QUEUE_NAME", "actions_to_take")
                    
                    # Publish snipe action to actions queue using injected mq_subscriber
                    try:
                        if mq_subscriber.publish(snipe_action, queue_name=actions_queue):
                            logger.info(
                                "Snipe action published successfully",
                                token_address=token_details.token_address,
                                chain_id=token_details.chain_id,
                                chain_name=token_details.chain_name,
                                actions_queue=actions_queue
                            )
                        else:
                            logger.warning(
                                "Failed to publish snipe action",
                                token_address=token_details.token_address,
                                actions_queue=actions_queue
                            )
                    except Exception as publish_error:
                        logger.error(
                            "Error publishing snipe action",
                            error=str(publish_error),
                            token_address=token_details.token_address,
                            actions_queue=actions_queue
                        )
                
                channel.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(
                    "Error analyzing tweet sentiment",
                    error=str(e),
                    message=message[:500] + "..." if len(message) > 500 else message
                )
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(
                "Error processing message",
                error=str(e),
                routing_key=method.routing_key
            )
            # Reject the message without requeue to avoid infinite loops
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    return message_handler

def shutdown_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info("Shutdown signal received, cleaning up...")
    shutdown_requested = True

def main() -> None:
    """Main application entry point."""
    global shutdown_requested
    
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info("Starting RabbitMQ message processor", environment=environment)
    
    # Initialize and test RabbitMQ connection at startup
    mq_subscriber = initialize_rabbitmq()
    
    # Initialize RabbitMQ connection monitor
    connection_monitor: Optional[RabbitMQConnectionMonitor] = initialize_rabbitmq_monitor(mq_subscriber)
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    logger.info("Signal handlers registered for graceful shutdown")
    
    try:
        # Create message handler with MQSubscriber dependency injected
        handler = create_message_handler(mq_subscriber)
        
        # Set up message handler and start consuming
        mq_subscriber.set_message_handler(handler)
        mq_subscriber.start_consuming()
        
        logger.info("Application started and consuming messages. Press Ctrl+C to shutdown.")
        
        while not shutdown_requested:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_requested = True
    
    finally:
        logger.info("Application shutting down")
        
        # Cleanup resources
        if connection_monitor:
            connection_monitor.stop()
        if mq_subscriber:
            mq_subscriber.close()

if __name__ == "__main__":
    load_dotenv()
    # Initialize Logfire observability
    initialize_logfire()
    main()
