"""
WebSocket consumers for real-time geolocation tracking.

Provides low-latency GPS streaming over WebSockets:
- Specific pickup tracking (`pickup_tracking_<id>`): for citizens monitoring an en-route collector.
- Global administrative map (`admin_live_map`): for city managers monitoring all fleet positions.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class LiveTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer handling real-time GPS coordinates propagation.

    Allows collectors to broadcast coordinate updates and connected clients
    (citizens or administrators) to receive live marker position adjustments.
    """

    async def connect(self):
        """
        Accept incoming WebSocket connection and subscribe to the appropriate channel group.

        If a `pickup_id` is supplied in the URL path, joins the channel group for that specific
        pickup request; otherwise joins the global administrative live map channel.
        """
        self.pickup_id = self.scope["url_route"]["kwargs"].get("pickup_id")
        if self.pickup_id:
            self.room_group_name = f"pickup_tracking_{self.pickup_id}"
        else:
            self.room_group_name = "admin_live_map"

        # Join the channel layer group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """
        Unsubscribe consumer from the channel layer group upon disconnection.
        """
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Process incoming WebSocket payload from client.

        Broadcasts received GPS telemetry to all peers subscribed to the room group.
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        # Broadcast location update to room group members
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "location_update",
                "data": data,
            },
        )

    async def location_update(self, event):
        """
        Channel layer event handler invoked when a peer broadcasts a 'location_update'.

        Transmits the JSON coordinate payload directly down the client WebSocket.
        """
        await self.send(text_data=json.dumps(event["data"]))
