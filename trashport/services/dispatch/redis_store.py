"""
Redis data access layer for the TrashPort dispatch engine.

Key schema (all in Redis DB 3):
  dispatch:queue                         → sorted set  (score=timestamp, member=request_id)
  dispatch:request:{request_id}          → hash        (full request snapshot)
  dispatch:collector:{collector_id}:pos  → hash        (lat, lng, updated_at)
  dispatch:collector:{collector_id}:load → integer     (active assignment count)
"""
import json
import time
from typing import Optional

from trashport.core.utils.redis_client import get_redis_client

QUEUE_KEY = "dispatch:queue"
REQUEST_TTL = 3600        # 1 hour — requests expire if not picked up
COLLECTOR_POS_TTL = 300   # 5 minutes — stale position data auto-expires


class DispatchRedisStore:
    """
    High-performance Redis store managing real-time dispatch queueing,
    ephemeral collector geolocation coordinates, and live concurrency loads.
    """

    def __init__(self):
        """Initialize Redis connection client via singleton pool."""
        self.redis = get_redis_client()

    # ------------------------------------------------------------------ #
    # Request queue                                                      #
    # ------------------------------------------------------------------ #

    def enqueue_request(self, request_id: str, payload: dict) -> None:
        """
        Push a pickup request onto the dispatch queue with current timestamp as score.
        Stores request attributes in a paired Redis Hash with 1-hour TTL.
        """
        score = time.time()
        pipe = self.redis.pipeline()
        pipe.zadd(QUEUE_KEY, {request_id: score})
        pipe.hset(
            f"dispatch:request:{request_id}",
            mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in payload.items()
            },
        )
        pipe.expire(f"dispatch:request:{request_id}", REQUEST_TTL)
        pipe.execute()

    def dequeue_next_request(self) -> Optional[tuple[str, dict]]:
        """
        Atomically pop the oldest unassigned request from the dispatch queue.
        Returns a tuple of (request_id, payload_dict) or None if the queue is empty.
        """
        result = self.redis.zpopmin(QUEUE_KEY, count=1)
        if not result:
            return None

        request_id = result[0][0]
        raw = self.redis.hgetall(f"dispatch:request:{request_id}")
        if not raw:
            return None

        payload = {}
        for k, v in raw.items():
            try:
                payload[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                payload[k] = v

        return request_id, payload

    def remove_request(self, request_id: str) -> None:
        """
        Purge a request from the sorted set queue and its associated hash snapshot
        after successful claim or completion.
        """
        pipe = self.redis.pipeline()
        pipe.zrem(QUEUE_KEY, request_id)
        pipe.delete(f"dispatch:request:{request_id}")
        pipe.execute()

    def get_queue_length(self) -> int:
        """Return the current count of queued pickup requests waiting for assignment."""
        return self.redis.zcard(QUEUE_KEY)

    # ------------------------------------------------------------------ #
    # Collector position                                                 #
    # ------------------------------------------------------------------ #

    def update_collector_position(
        self, collector_id: str, lat: float, lng: float
    ) -> None:
        """
        Update the ephemeral latitude and longitude for an active collector.
        Applies a 5-minute sliding TTL to prune inactive/offline collectors.
        """
        key = f"dispatch:collector:{collector_id}:pos"
        pipe = self.redis.pipeline()
        pipe.hset(key, mapping={
            "lat": str(lat),
            "lng": str(lng),
            "updated_at": str(time.time()),
        })
        pipe.expire(key, COLLECTOR_POS_TTL)
        pipe.execute()

    def get_collector_position(self, collector_id: str) -> Optional[dict]:
        """Fetch the most recent latitude, longitude, and timestamp for a single collector."""
        key = f"dispatch:collector:{collector_id}:pos"
        raw = self.redis.hgetall(key)
        if not raw:
            return None
        return {
            "lat": float(raw["lat"]),
            "lng": float(raw["lng"]),
            "updated_at": float(raw["updated_at"]),
        }

    def get_all_collector_positions(self, collector_ids: list[str]) -> dict:
        """Batch fetch positions for a list of collectors using a Redis pipelined request."""
        pipe = self.redis.pipeline()
        for cid in collector_ids:
            pipe.hgetall(f"dispatch:collector:{cid}:pos")
        results = pipe.execute()

        positions = {}
        for cid, raw in zip(collector_ids, results):
            if raw:
                positions[cid] = {
                    "lat": float(raw["lat"]),
                    "lng": float(raw["lng"]),
                    "updated_at": float(raw["updated_at"]),
                }
        return positions

    # ------------------------------------------------------------------ #
    # Collector workload (for least-busy algorithm)                      #
    # ------------------------------------------------------------------ #

    def increment_collector_load(self, collector_id: str) -> int:
        """Increment the count of active in-progress assignments for a collector."""
        key = f"dispatch:collector:{collector_id}:load"
        return self.redis.incr(key)

    def decrement_collector_load(self, collector_id: str) -> int:
        """Decrement active assignment count, clamping at zero to avoid negative loads."""
        key = f"dispatch:collector:{collector_id}:load"
        val = self.redis.decr(key)
        if val < 0:
            self.redis.set(key, 0)
            return 0
        return val

    def get_collector_load(self, collector_id: str) -> int:
        """Retrieve the number of active jobs currently claimed by a collector."""
        key = f"dispatch:collector:{collector_id}:load"
        val = self.redis.get(key)
        return int(val) if val else 0

    def get_all_collector_loads(self, collector_ids: list[str]) -> dict:
        """Batch fetch active assignment loads for multiple collectors via pipeline."""
        pipe = self.redis.pipeline()
        for cid in collector_ids:
            pipe.get(f"dispatch:collector:{cid}:load")
        results = pipe.execute()
        return {
            cid: int(val) if val else 0
            for cid, val in zip(collector_ids, results)
        }
