"""Comprehensive test suite for MessageBuffer class."""

import os
import time
import threading
import pytest
from unittest.mock import patch
from src.core.message_buffer import MessageBuffer


class TestMessageBufferInitialization:
    """Test MessageBuffer initialization and configuration."""

    def test_default_initialization(self):
        """Test MessageBuffer with default parameters."""
        buffer = MessageBuffer()
        
        assert buffer.max_size == 10
        assert buffer.enabled is True
        assert buffer.size() == 0
        assert buffer.is_empty() is True
        assert buffer.is_full() is False

    def test_custom_initialization(self):
        """Test MessageBuffer with custom parameters."""
        buffer = MessageBuffer(max_size=5, enabled=False)
        
        assert buffer.max_size == 5
        assert buffer.enabled is False
        assert buffer.size() == 0

    def test_from_env_defaults(self):
        """Test MessageBuffer.from_env() with default environment values."""
        with patch.dict(os.environ, {}, clear=True):
            buffer = MessageBuffer.from_env()
            
            assert buffer.max_size == 10
            assert buffer.enabled is True

    def test_from_env_custom_values(self):
        """Test MessageBuffer.from_env() with custom environment values."""
        env_vars = {
            "MESSAGE_BUFFER_ENABLED": "false",
            "MESSAGE_BUFFER_SIZE": "20"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            buffer = MessageBuffer.from_env()
            
            assert buffer.max_size == 20
            assert buffer.enabled is False

    def test_from_env_various_enabled_values(self):
        """Test different string values for MESSAGE_BUFFER_ENABLED."""
        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("false", False),
            ("FALSE", False),
            ("False", False),
            ("invalid", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"MESSAGE_BUFFER_ENABLED": env_value}, clear=True):
                buffer = MessageBuffer.from_env()
                assert buffer.enabled is expected


class TestMessageBufferBasicOperations:
    """Test basic buffer operations."""

    def test_add_message_enabled(self):
        """Test adding message when buffering is enabled."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        message = {"event_type": "tweet", "content": "test message"}
        
        result = buffer.add_message(message)
        
        assert result is True
        assert buffer.size() == 1
        assert not buffer.is_empty()

    def test_add_message_disabled(self):
        """Test adding message when buffering is disabled."""
        buffer = MessageBuffer(max_size=3, enabled=False)
        message = {"event_type": "tweet", "content": "test message"}
        
        result = buffer.add_message(message)
        
        assert result is False
        assert buffer.size() == 0
        assert buffer.is_empty()

    def test_add_invalid_message_type(self):
        """Test adding non-dictionary message."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        result = buffer.add_message("invalid message")
        
        assert result is False
        assert buffer.size() == 0

    def test_pop_message(self):
        """Test popping message from buffer."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        message = {"event_type": "tweet", "content": "test message"}
        
        buffer.add_message(message)
        popped = buffer.pop_message()
        
        assert popped is not None
        assert popped["message"] == message
        assert "timestamp" in popped
        assert "buffer_sequence" in popped
        assert buffer.size() == 0

    def test_pop_message_empty_buffer(self):
        """Test popping from empty buffer."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        result = buffer.pop_message()
        
        assert result is None

    def test_get_pending_messages(self):
        """Test getting all pending messages without removing them."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        messages = [
            {"event_type": "tweet", "id": 1},
            {"event_type": "tweet", "id": 2}
        ]
        
        for msg in messages:
            buffer.add_message(msg)
        
        pending = buffer.get_pending_messages()
        
        assert len(pending) == 2
        assert buffer.size() == 2  # Messages still in buffer
        assert pending[0]["message"]["id"] == 1
        assert pending[1]["message"]["id"] == 2

    def test_clear_buffer(self):
        """Test clearing all messages from buffer."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        messages = [
            {"event_type": "tweet", "id": 1},
            {"event_type": "tweet", "id": 2}
        ]
        
        for msg in messages:
            buffer.add_message(msg)
        
        cleared_count = buffer.clear_buffer()
        
        assert cleared_count == 2
        assert buffer.size() == 0
        assert buffer.is_empty()

    def test_clear_empty_buffer(self):
        """Test clearing empty buffer."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        cleared_count = buffer.clear_buffer()
        
        assert cleared_count == 0


class TestMessageBufferCapacityManagement:
    """Test buffer capacity and overflow behavior."""

    def test_buffer_full_detection(self):
        """Test buffer full detection."""
        buffer = MessageBuffer(max_size=2, enabled=True)
        
        assert not buffer.is_full()
        
        buffer.add_message({"id": 1})
        assert not buffer.is_full()
        
        buffer.add_message({"id": 2})
        assert buffer.is_full()

    def test_buffer_overflow_removes_oldest(self):
        """Test that overflow removes oldest message."""
        buffer = MessageBuffer(max_size=2, enabled=True)
        
        # Fill buffer
        buffer.add_message({"id": 1, "data": "first"})
        buffer.add_message({"id": 2, "data": "second"})
        
        # Add third message (should remove first)
        buffer.add_message({"id": 3, "data": "third"})
        
        assert buffer.size() == 2
        pending = buffer.get_pending_messages()
        assert pending[0]["message"]["id"] == 2  # First message removed
        assert pending[1]["message"]["id"] == 3

    def test_multiple_overflow_cycles(self):
        """Test multiple overflow cycles."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        # Add 6 messages to a buffer of size 3
        for i in range(1, 7):
            buffer.add_message({"id": i})
        
        assert buffer.size() == 3
        pending = buffer.get_pending_messages()
        
        # Should contain messages 4, 5, 6 (oldest removed)
        message_ids = [msg["message"]["id"] for msg in pending]
        assert message_ids == [4, 5, 6]

    def test_fifo_order_maintained(self):
        """Test that FIFO order is maintained during normal operations."""
        buffer = MessageBuffer(max_size=5, enabled=True)
        
        # Add messages
        for i in range(1, 4):
            buffer.add_message({"id": i})
        
        # Pop messages and verify order
        first = buffer.pop_message()
        second = buffer.pop_message()
        third = buffer.pop_message()
        
        assert first["message"]["id"] == 1
        assert second["message"]["id"] == 2
        assert third["message"]["id"] == 3


class TestMessageBufferMetadata:
    """Test message metadata and sequencing."""

    def test_message_metadata_added(self):
        """Test that messages include timestamp and sequence metadata."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        message = {"event_type": "tweet", "content": "test"}
        
        start_time = time.time()
        buffer.add_message(message)
        end_time = time.time()
        
        pending = buffer.get_pending_messages()
        buffered_msg = pending[0]
        
        assert "message" in buffered_msg
        assert "timestamp" in buffered_msg
        assert "buffer_sequence" in buffered_msg
        assert buffered_msg["message"] == message
        assert start_time <= buffered_msg["timestamp"] <= end_time
        assert isinstance(buffered_msg["buffer_sequence"], int)

    def test_sequence_numbers_increment(self):
        """Test that sequence numbers increment correctly."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        buffer.add_message({"id": 1})
        buffer.add_message({"id": 2})
        buffer.add_message({"id": 3})
        
        pending = buffer.get_pending_messages()
        sequences = [msg["buffer_sequence"] for msg in pending]
        
        # Sequences should be consecutive
        assert sequences[1] == sequences[0] + 1
        assert sequences[2] == sequences[1] + 1


class TestMessageBufferStatus:
    """Test buffer status reporting."""

    def test_get_status_empty_buffer(self):
        """Test status for empty buffer."""
        buffer = MessageBuffer(max_size=5, enabled=True)
        
        status = buffer.get_status()
        
        expected_keys = {
            "enabled", "current_size", "max_size", "is_full", "is_empty",
            "oldest_message_timestamp", "newest_message_timestamp", "oldest_message_age_seconds"
        }
        assert set(status.keys()) == expected_keys
        assert status["enabled"] is True
        assert status["current_size"] == 0
        assert status["max_size"] == 5
        assert status["is_full"] is False
        assert status["is_empty"] is True
        assert status["oldest_message_timestamp"] is None
        assert status["newest_message_timestamp"] is None
        assert status["oldest_message_age_seconds"] is None

    def test_get_status_with_messages(self):
        """Test status with messages in buffer."""
        buffer = MessageBuffer(max_size=3, enabled=False)
        
        # Re-enable for testing
        buffer.enabled = True
        buffer.add_message({"id": 1})
        time.sleep(0.01)  # Small delay to ensure different timestamps
        buffer.add_message({"id": 2})
        
        status = buffer.get_status()
        
        assert status["enabled"] is True
        assert status["current_size"] == 2
        assert status["max_size"] == 3
        assert status["is_full"] is False
        assert status["is_empty"] is False
        assert status["oldest_message_timestamp"] is not None
        assert status["newest_message_timestamp"] is not None
        assert status["oldest_message_age_seconds"] is not None
        assert status["oldest_message_timestamp"] < status["newest_message_timestamp"]

    def test_get_status_full_buffer(self):
        """Test status for full buffer."""
        buffer = MessageBuffer(max_size=2, enabled=True)
        
        buffer.add_message({"id": 1})
        buffer.add_message({"id": 2})
        
        status = buffer.get_status()
        
        assert status["current_size"] == 2
        assert status["is_full"] is True
        assert status["is_empty"] is False


class TestMessageBufferThreadSafety:
    """Test thread safety of buffer operations."""

    def test_concurrent_add_operations(self):
        """Test concurrent add operations are thread-safe."""
        buffer = MessageBuffer(max_size=100, enabled=True)
        num_threads = 10
        messages_per_thread = 10
        
        def add_messages(thread_id):
            for i in range(messages_per_thread):
                buffer.add_message({"thread_id": thread_id, "message_id": i})
        
        threads = []
        for thread_id in range(num_threads):
            thread = threading.Thread(target=add_messages, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert buffer.size() == num_threads * messages_per_thread

    def test_concurrent_add_and_pop_operations(self):
        """Test concurrent add and pop operations."""
        buffer = MessageBuffer(max_size=50, enabled=True)
        add_count = 0
        pop_count = 0
        stop_flag = threading.Event()
        
        def add_messages():
            nonlocal add_count
            while not stop_flag.is_set():
                buffer.add_message({"id": add_count})
                add_count += 1
                time.sleep(0.001)
        
        def pop_messages():
            nonlocal pop_count
            while not stop_flag.is_set():
                if buffer.pop_message():
                    pop_count += 1
                time.sleep(0.001)
        
        add_thread = threading.Thread(target=add_messages)
        pop_thread = threading.Thread(target=pop_messages)
        
        add_thread.start()
        pop_thread.start()
        
        time.sleep(0.1)  # Run for 100ms
        stop_flag.set()
        
        add_thread.join()
        pop_thread.join()
        
        # Verify operations completed without errors
        assert add_count > 0
        assert pop_count >= 0
        assert buffer.size() >= 0

    def test_concurrent_status_operations(self):
        """Test concurrent status queries are thread-safe."""
        buffer = MessageBuffer(max_size=10, enabled=True)
        
        def query_status():
            for _ in range(50):
                status = buffer.get_status()
                assert isinstance(status, dict)
                assert "current_size" in status
        
        def modify_buffer():
            for i in range(20):
                buffer.add_message({"id": i})
                if i % 5 == 0:
                    buffer.pop_message()
        
        status_thread = threading.Thread(target=query_status)
        modify_thread = threading.Thread(target=modify_buffer)
        
        status_thread.start()
        modify_thread.start()
        
        status_thread.join()
        modify_thread.join()
        
        # Should complete without errors


class TestMessageBufferSpecialMethods:
    """Test special methods (__len__, __bool__)."""

    def test_len_method(self):
        """Test __len__ method returns current size."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        assert len(buffer) == 0
        
        buffer.add_message({"id": 1})
        assert len(buffer) == 1
        
        buffer.add_message({"id": 2})
        assert len(buffer) == 2

    def test_bool_method(self):
        """Test __bool__ method returns True if buffer has messages."""
        buffer = MessageBuffer(max_size=3, enabled=True)
        
        assert not bool(buffer)  # Empty buffer is False
        
        buffer.add_message({"id": 1})
        assert bool(buffer)  # Non-empty buffer is True
        
        buffer.clear_buffer()
        assert not bool(buffer)  # Cleared buffer is False