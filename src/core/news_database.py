"""In-memory news database for duplicate detection and storage."""

import threading
from typing import List, Optional
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class NewsDatabase:
    """
    Thread-safe in-memory database for storing news items and preventing duplicates.
    
    This class provides a simple storage mechanism for news items with thread-safe
    operations to support concurrent access from multiple processing threads.
    """
    
    def __init__(self, existing_news: Optional[List[str]] = None):
        """
        Initialize the news database.
        
        Args:
            existing_news: Optional list of existing news items to initialize with
        """
        self._news_items = existing_news or []
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        
        logger.debug(
            "NewsDatabase initialized",
            initial_count=len(self._news_items)
        )
    
    def get_existing_news(self) -> List[str]:
        """
        Get a copy of all existing news items.
        
        Returns:
            List of all news items currently stored
        """
        with self._lock:
            return self._news_items.copy()
    
    def add_news(self, news: str) -> bool:
        """
        Add new news item to database if it doesn't already exist.
        
        Args:
            news: News item text to add
            
        Returns:
            True if news was added (was unique), False if already existed
        """
        if not news or not news.strip():
            logger.warning("Attempted to add empty news item")
            return False
            
        news = news.strip()
        
        with self._lock:
            if news not in self._news_items:
                self._news_items.append(news)
                logger.debug(
                    "News item added to database",
                    news_preview=news[:100] + "..." if len(news) > 100 else news,
                    total_count=len(self._news_items)
                )
                return True
            else:
                logger.debug(
                    "News item already exists in database",
                    news_preview=news[:100] + "..." if len(news) > 100 else news
                )
                return False
    
    def size(self) -> int:
        """
        Get the number of news items currently stored.
        
        Returns:
            Number of news items in database
        """
        with self._lock:
            return len(self._news_items)
    
    def clear(self) -> None:
        """
        Clear all news items from the database.
        """
        with self._lock:
            count = len(self._news_items)
            self._news_items.clear()
            logger.info(
                "NewsDatabase cleared",
                items_removed=count
            )
    
    def contains(self, news: str) -> bool:
        """
        Check if news item exists in database.
        
        Args:
            news: News item text to check
            
        Returns:
            True if news exists, False otherwise
        """
        if not news or not news.strip():
            return False
            
        news = news.strip()
        
        with self._lock:
            return news in self._news_items
    
    def get_recent(self, count: int = 10) -> List[str]:
        """
        Get the most recently added news items.
        
        Args:
            count: Maximum number of recent items to return
            
        Returns:
            List of most recent news items (up to count)
        """
        with self._lock:
            return self._news_items[-count:] if self._news_items else []
    
    def __len__(self) -> int:
        """Return the number of news items (for len() function)."""
        return self.size()
    
    def __contains__(self, news: str) -> bool:
        """Check if news exists (for 'in' operator)."""
        return self.contains(news)
    
    def __str__(self) -> str:
        """String representation of the database."""
        return f"NewsDatabase(size={self.size()})"
    
    def __repr__(self) -> str:
        """Detailed representation of the database."""
        with self._lock:
            preview = []
            for item in self._news_items[:3]:  # Show first 3 items
                truncated = item[:50] + "..." if len(item) > 50 else item
                preview.append(f"'{truncated}'")
            
            if len(self._news_items) > 3:
                preview.append(f"... and {len(self._news_items) - 3} more")
            
            return f"NewsDatabase(size={len(self._news_items)}, items=[{', '.join(preview)}])"


# Global instance for application-wide use
_global_news_db: Optional[NewsDatabase] = None
_db_lock = threading.Lock()


def get_global_news_database() -> NewsDatabase:
    """
    Get the global NewsDatabase instance (singleton pattern).
    
    Returns:
        Global NewsDatabase instance
    """
    global _global_news_db
    
    with _db_lock:
        if _global_news_db is None:
            _global_news_db = NewsDatabase()
            logger.info("Global NewsDatabase instance created")
        
        return _global_news_db


def reset_global_news_database() -> None:
    """
    Reset the global NewsDatabase instance (useful for testing).
    """
    global _global_news_db
    
    with _db_lock:
        if _global_news_db is not None:
            old_size = _global_news_db.size()
            _global_news_db = None
            logger.info(
                "Global NewsDatabase instance reset",
                previous_size=old_size
            )


def initialize_global_news_database(existing_news: Optional[List[str]] = None) -> NewsDatabase:
    """
    Initialize the global NewsDatabase with existing news items.
    
    Args:
        existing_news: Optional list of existing news to initialize with
        
    Returns:
        Initialized global NewsDatabase instance
    """
    global _global_news_db
    
    with _db_lock:
        _global_news_db = NewsDatabase(existing_news)
        logger.info(
            "Global NewsDatabase initialized with existing news",
            initial_count=_global_news_db.size()
        )
        
        return _global_news_db