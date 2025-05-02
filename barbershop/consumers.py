from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.layers import get_channel_layer

class AppointmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Füge den WebSocket-Client der Gruppe "appointments" hinzu
        self.group_name = "appointments"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Entferne den WebSocket-Client aus der Gruppe "appointments"
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def appointment_update(self, event):
        # Empfange die Nachricht und sende sie an den WebSocket-Client
        await self.send(text_data=json.dumps(event["data"]))

    async def send_test_message(self):
        # Beispiel für das manuelle Senden einer Nachricht an alle verbundenen WebSockets in der Gruppe "appointments"
        channel_layer = get_channel_layer()
        await channel_layer.send(
            self.group_name, 
            {
                "type": "appointment_update", 
                "data": "Test data"
            }
        )