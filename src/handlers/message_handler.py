"""RabbitMQ message handler for processing tweets and publishing snipe actions."""

import json
import os
from typing import Any
from ..config.logging_config import get_logger
from ..core.mq_subscriber import MQSubscriber
from ..models.schemas import TokenDetails, SnipeAction, SnipeActionParams
from .tweet import handle_tweet_event

logger = get_logger(__name__)


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