import logging
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async
import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    pass

def _incr_and_expire(key, ttl):
    """
    Attempts to increment the key using django cache.
    Uses the add + incr pattern which is cross-compatible with LocMemCache and RedisCache.
    """
    added = cache.add(key, 1, timeout=ttl)
    if added:
        return 1
    try:
        val = cache.incr(key)
    except ValueError:
        # Fallback if key expired between add and incr
        cache.set(key, 1, timeout=ttl)
        val = 1
    return val

def _sync_check_rate_limit(user_id):
    rpm_key = f"chatbot:rpm:{user_id}"
    daily_key = f"chatbot:daily:{user_id}"
    global_key = "chatbot:global:rpm"

    rpm_val = _incr_and_expire(rpm_key, 60)
    if rpm_val > 5:
        raise RateLimitError("Rate limit exceeded: max 5 requests per minute.")

    daily_val = _incr_and_expire(daily_key, 86400)
    if daily_val > 100:
        raise RateLimitError("Daily rate limit exceeded: max 100 requests per day.")

    global_val = _incr_and_expire(global_key, 60)
    if global_val > 25:
        raise RateLimitError("Global rate limit exceeded: please try again in a minute.")

async def check_rate_limit(user_id):
    await sync_to_async(_sync_check_rate_limit)(user_id)

async def chat(messages: list[dict]) -> str:
    try:
        client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        response = await client.chat.completions.create(
            messages=messages,
            model=settings.CHATBOT_MODEL,
            max_tokens=settings.CHATBOT_MAX_TOKENS,
            temperature=0.3,
            stream=False,
        )
        return response.choices[0].message.content
    except openai.APIError as e:
        logger.error(f"Groq APIError: {e}")
        return '{"type": "text", "message": "Service unavailable. Please try again."}'
