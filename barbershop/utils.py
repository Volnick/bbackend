from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_appointment_update(payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "appointments",
        {
            "type": "appointment.update",  # muss zu Consumer-Methode passen!
            "data": payload,
        },
    )