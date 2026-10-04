"""
WebSocket handler for Twilio Media Streams
Requires Django Channels or similar WebSocket support
"""
import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from .media_stream_handler import MediaStreamHandler


class TwilioMediaStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for Twilio Media Streams
    Handles bidirectional audio streaming with ElevenLabs
    """

    async def connect(self):
        """Accept WebSocket connection from Twilio"""
        self.call_sid = self.scope.get('url_route', {}).get('kwargs', {}).get('call_sid', '')
        self.handler = MediaStreamHandler(self.call_sid)

        await self.accept()
        print(f"Media Stream connected for call: {self.call_sid}")

    async def disconnect(self, close_code):
        """Handle disconnection"""
        if hasattr(self, 'handler') and self.handler.conversation_id:
            self.handler.elevenlabs_client.end_conversation(self.handler.conversation_id)
        print(f"Media Stream disconnected: {close_code}")

    async def receive(self, text_data):
        """Handle incoming messages from Twilio"""
        try:
            message = json.loads(text_data)
            response = self.handler.handle_message(message)

            if response:
                await self.send(text_data=json.dumps(response))
        except Exception as e:
            print(f"Error handling message: {e}")

