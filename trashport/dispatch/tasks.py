from celery import shared_task
from waste_management.models import PickupRequest
from trashport.dispatch.redis_store import DispatchRedisStore

# A basic/dummy helper for dispatch algorithm
def run_dispatch_algorithm(payload: dict) -> int:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    collectors = list(User.objects.filter(role=User.Roles.COLLECTOR, is_active=True))
    if not collectors:
        raise ValueError("No active collectors found")
    # For now, return the first active collector
    return collectors[0].id

@shared_task(bind=True, max_retries=3)
def process_dispatch_queue(self):
    store = DispatchRedisStore()

    result = store.dequeue_next_request()
    if result is None:
        return "Queue empty"

    request_id, payload = result

    try:
        # --- Run your chosen algorithm here ---
        # nearest:    use store.get_all_collector_positions(collector_ids)
        # least-busy: use store.get_all_collector_loads(collector_ids)
        # zone-based: use payload["ward"] to filter, then fallback

        assigned_collector_id = run_dispatch_algorithm(payload)

        store.increment_collector_load(assigned_collector_id)
        store.remove_request(request_id)

        # Persist assignment to Postgres/SQLite
        PickupRequest.objects.filter(id=request_id).update(
            collector_id=assigned_collector_id,
            status="ASSIGNED",
        )

    except Exception as exc:
        # Re-enqueue on failure
        store.enqueue_request(request_id, payload)
        raise self.retry(exc=exc, countdown=10)
