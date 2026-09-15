"""
Sliding window rate limiter for the TrashPort chatbot.
Uses a Redis sorted set per user UID.
Key pattern: chatbot:ratelimit:{uid}
Score: Unix timestamp (float)
Members: UUID message IDs (unique per message)
"""
import logging
import time
import uuid

from django.conf import settings

from trashport.core.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ChatbotRateLimiter:
    def __init__(self):
        try:
            self.redis = get_redis_client()
        except Exception as e:
            logger.warning(f"Could not connect to Redis for rate limiter: {e}")
            self.redis = None
        self.max_messages = getattr(settings, "CHATBOT_RATE_LIMIT_MAX", 20)
        self.window_seconds = getattr(settings, "CHATBOT_RATE_LIMIT_WINDOW", 60)

    def is_allowed(self, uid: str) -> tuple[bool, int]:
        """
        Check if the user is within rate limits.

        Returns:
            (allowed: bool, remaining: int)
            - allowed: True if the message can proceed
            - remaining: number of messages left in current window
        """
        if not self.redis:
            return True, self.max_messages

        try:
            key = f"chatbot:ratelimit:{uid}"
            now = time.time()
            window_start = now - self.window_seconds

            pipe = self.redis.pipeline()
            # Remove timestamps outside the sliding window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # Count current messages in window
            pipe.zcard(key)
            # Add this attempt with current timestamp
            pipe.zadd(key, {str(uuid.uuid4()): now})
            # Set TTL so keys auto-expire
            pipe.expire(key, self.window_seconds * 2)
            results = pipe.execute()

            current_count = results[1]  # count before adding this message

            if current_count >= self.max_messages:
                # Undo the zadd â€” we're rejecting this message
                self.redis.zpopmax(key)
                remaining = 0
                return False, remaining

            remaining = self.max_messages - current_count - 1
            return True, remaining
        except Exception as e:
            logger.warning(f"Redis rate limiter exception (allowed fallback): {e}")
            return True, self.max_messages

    def get_retry_after(self, uid: str) -> int:
        """
        Returns seconds until the oldest message in the window expires.
        Call this when is_allowed returns False.
        """
        if not self.redis:
            return 0

        try:
            key = f"chatbot:ratelimit:{uid}"
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            if not oldest:
                return 0
            oldest_timestamp = oldest[0][1]
            retry_after = int(oldest_timestamp + self.window_seconds - time.time())
            return max(retry_after, 1)
        except Exception as e:
            logger.warning(f"Redis get_retry_after exception: {e}")
            return 5

