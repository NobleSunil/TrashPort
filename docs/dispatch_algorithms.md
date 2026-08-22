# TrashPort Dispatch Algorithms

TrashPort supports three pluggable routing algorithms in `trashport.dispatch.algorithms`:

## 1. Nearest Collector Dispatch (`NearestCollectorDispatch`)
- Calculates Euclidean / Haversine distance between the pickup location and all active collectors.
- Assigns each pickup to the collector with the minimum physical distance.

## 2. Least Busy Collector Dispatch (`LeastBusyCollectorDispatch`)
- Balances workforce load by evaluating the current number of active (`PENDING` or `ASSIGNED`) tasks assigned to each collector.
- Assigns new tasks to the collector with the lowest queue depth.

## 3. Zone-Based Dispatch (`ZoneBasedDispatch`)
- Partitions regions into fixed service zones and assigns tasks based on collector sector allocations.
