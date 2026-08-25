"""
Central Redis client factory for TrashPort.
Used by chatbot rate limiter and dispatch engine.
Connects to DB 3 (shared store for rate limiting + dispatch).
"""
import redis
from django.conf import settings


def get_redis_client() -> redis.Redis:
    """
    Returns a Redis client connected to DB 3.
    Uses connection pooling via django-redis internals is not used here
    because dispatch and chatbot need raw Redis commands (sorted sets, pipelines).
    """
    return redis.Redis.from_url(
        settings.REDIS_DISPATCH_DB,
        decode_responses=True,
    )
