import json
from channels.generic.websocket import AsyncWebsocketConsumer


class LiveTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.pickup_id = self.scope["url_route"]["kwargs"].get("pickup_id")
        if self.pickup_id:
            self.room_group_name = f"pickup_tracking_{self.pickup_id}"
        else:
            self.room_group_name = "admin_live_map"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Broadcast location update to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "location_update",
                "data": data,
            }
        )

    async def location_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))
