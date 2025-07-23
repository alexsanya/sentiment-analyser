"""RabbitMQ connection monitoring service with automatic reconnection."""

import os
import threading
import time
from typing import Optional
from logging_config import get_logger

logger = get_logger(__name__)


class RabbitMQConnectionMonitor:
    """Monitors RabbitMQ connection health and handles automatic reconnection."""
    
    def __init__(
        self,
        mq_messenger: 'MQMessenger',
        check_interval: int = 30,
        max_retry_attempts: int = 3,
        retry_delay: int = 5
    ) -> None:
        """Initialize RabbitMQ connection monitor.
        
        Args:
            mq_messenger: MQMessenger instance to monitor
            check_interval: Seconds between connection health checks
            max_retry_attempts: Maximum reconnection attempts before giving up
            retry_delay: Seconds to wait between reconnection attempts
        """
        self.mq_messenger = mq_messenger
        self.check_interval = check_interval
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay = retry_delay
        
        # Threading controls
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._is_running = False
        
        # Connection state tracking
        self._last_connection_status = True
        self._consecutive_failures = 0
        
        logger.info(
            "RabbitMQ connection monitor initialized",
            check_interval=check_interval,
            max_retry_attempts=max_retry_attempts,
            retry_delay=retry_delay
        )
    
    @classmethod
    def from_env(cls, mq_messenger: 'MQMessenger') -> 'RabbitMQConnectionMonitor':
        """Create monitor instance from environment variables."""
        return cls(
            mq_messenger=mq_messenger,
            check_interval=int(os.getenv("RABBITMQ_MONITOR_INTERVAL", "30")),
            max_retry_attempts=int(os.getenv("RABBITMQ_MAX_RETRY_ATTEMPTS", "3")),
            retry_delay=int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))
        )
    
    def start(self) -> None:
        """Start the connection monitoring in a background thread."""
        if self._is_running:
            logger.warning("Connection monitor is already running")
            return
        
        self._shutdown_event.clear()
        self._is_running = True
        
        # Create and start daemon thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="RabbitMQ-Monitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("RabbitMQ connection monitor started")
    
    def stop(self) -> None:
        """Stop the connection monitoring and wait for thread to finish."""
        if not self._is_running:
            return
        
        logger.info("Stopping RabbitMQ connection monitor...")
        self._shutdown_event.set()
        self._is_running = False
        
        # Wait for monitor thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            if self._monitor_thread.is_alive():
                logger.warning("Monitor thread did not stop gracefully within timeout")
        
        logger.info("RabbitMQ connection monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in background thread."""
        logger.info("Connection monitoring loop started")
        
        while not self._shutdown_event.is_set():
            try:
                self._check_and_handle_connection()
            except Exception as e:
                logger.error(
                    "Unexpected error in connection monitoring loop",
                    error=str(e),
                    error_type=type(e).__name__
                )
            
            # Wait for next check or shutdown signal
            if self._shutdown_event.wait(timeout=self.check_interval):
                break  # Shutdown was signaled
        
        logger.info("Connection monitoring loop ended")
    
    def _check_and_handle_connection(self) -> None:
        """Check connection health and handle reconnection if needed."""
        try:
            # Test connection using existing method
            is_connected = self.mq_messenger.is_connected()
            connection_test_passed = False
            
            if is_connected:
                # Perform actual connection test
                connection_test_passed = self.mq_messenger.test_connection()
            
            current_status = is_connected and connection_test_passed
            
            # Log status changes
            if current_status != self._last_connection_status:
                if current_status:
                    logger.info(
                        "RabbitMQ connection restored",
                        consecutive_failures=self._consecutive_failures
                    )
                    self._consecutive_failures = 0
                else:
                    logger.warning("RabbitMQ connection lost, initiating reconnection")
                
                self._last_connection_status = current_status
            
            # Handle connection failure
            if not current_status:
                self._consecutive_failures += 1
                self._attempt_reconnection()
            else:
                # Reset failure counter on successful connection
                self._consecutive_failures = 0
                
        except Exception as e:
            logger.error(
                "Error during connection health check",
                error=str(e),
                error_type=type(e).__name__
            )
            self._consecutive_failures += 1
            self._attempt_reconnection()
    
    def _attempt_reconnection(self) -> None:
        """Attempt to reconnect to RabbitMQ with retry logic."""
        if self._consecutive_failures > self.max_retry_attempts:
            logger.error(
                "Maximum reconnection attempts exceeded, connection monitoring continues",
                consecutive_failures=self._consecutive_failures,
                max_attempts=self.max_retry_attempts
            )
            return
        
        logger.info(
            "Attempting RabbitMQ reconnection",
            attempt=self._consecutive_failures,
            max_attempts=self.max_retry_attempts
        )
        
        try:
            # Use the reconnect method (to be implemented in MQMessenger)
            if hasattr(self.mq_messenger, 'reconnect'):
                success = self.mq_messenger.reconnect()
                if success:
                    logger.info("RabbitMQ reconnection successful")
                    self._consecutive_failures = 0
                    self._last_connection_status = True
                    return
            else:
                # Fallback to close and connect
                logger.warning("MQMessenger.reconnect() not available, using fallback method")
                self.mq_messenger.close()
                self.mq_messenger.connect()
                
                # Test the new connection
                if self.mq_messenger.test_connection():
                    logger.info("RabbitMQ reconnection successful (fallback method)")
                    self._consecutive_failures = 0
                    self._last_connection_status = True
                    return
                    
        except Exception as e:
            logger.error(
                "RabbitMQ reconnection attempt failed",
                error=str(e),
                error_type=type(e).__name__,
                attempt=self._consecutive_failures
            )
        
        # Wait before next attempt (unless shutting down)
        if not self._shutdown_event.wait(timeout=self.retry_delay):
            logger.info(f"Waiting {self.retry_delay} seconds before next reconnection attempt")
    
    def get_status(self) -> dict:
        """Get current monitor status information.
        
        Returns:
            dict: Monitor status including connection state and failure count
        """
        return {
            "is_running": self._is_running,
            "last_connection_status": self._last_connection_status,
            "consecutive_failures": self._consecutive_failures,
            "max_retry_attempts": self.max_retry_attempts,
            "check_interval": self.check_interval
        }