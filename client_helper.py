"""
Client helper utilities for the LiveKit Streaming Platform
"""
import asyncio
import json
from typing import Dict, Optional, Callable
from datetime import datetime

from livekit import rtc

class StreamingClient:
    """Simplified client for connecting to streaming rooms"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.room: Optional[rtc.Room] = None
        self.connected = False
        self.callbacks: Dict[str, Callable] = {}
        
    def on_event(self, event_name: str, callback: Callable):
        """Register event callbacks"""
        self.callbacks[event_name] = callback
    
    async def create_room(self, name: str, max_participants: int = 100) -> Dict:
        """Create a new streaming room"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/rooms/create",
                json={
                    "name": name,
                    "max_participants": max_participants,
                    "audio_enabled": True,
                    "video_enabled": True
                }
            ) as response:
                return await response.json()
    
    async def join_room(self, room_name: str, participant_name: str, 
                       permissions: Optional[Dict] = None) -> Dict:
        """Join a streaming room"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/rooms/{room_name}/join",
                json={
                    "room_name": room_name,
                    "participant_name": participant_name,
                    "permissions": permissions or {}
                }
            ) as response:
                return await response.json()
    
    async def connect_to_room(self, token: str, url: str, room_name: str):
        """Connect to LiveKit room with token"""
        self.room = rtc.Room()
        
        # Set up event handlers
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            print(f"Participant connected: {participant.identity}")
            if "participant_joined" in self.callbacks:
                self.callbacks["participant_joined"](participant)
        
        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            print(f"Participant disconnected: {participant.identity}")
            if "participant_left" in self.callbacks:
                self.callbacks["participant_left"](participant)
        
        @self.room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            print(f"Track published: {publication.sid} from {participant.identity}")
            if "track_published" in self.callbacks:
                self.callbacks["track_published"](publication, participant)
        
        @self.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            print(f"Track subscribed: {track.sid}")
            if "track_subscribed" in self.callbacks:
                self.callbacks["track_subscribed"](track, publication, participant)
        
        # Connect to room
        await self.room.connect(url, token)
        self.connected = True
        
        if "connected" in self.callbacks:
            self.callbacks["connected"]()
    
    async def publish_camera(self):
        """Publish camera feed"""
        if not self.room:
            raise Exception("Not connected to room")
        
        # Create camera source
        source = rtc.VideoSource(1280, 720)
        track = rtc.LocalVideoTrack.create_video_track("camera", source)
        
        # Publish track
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA)
        await self.room.local_participant.publish_track(track, options)
        
        return track, source
    
    async def publish_microphone(self):
        """Publish microphone feed"""
        if not self.room:
            raise Exception("Not connected to room")
        
        # Create audio source
        source = rtc.AudioSource(48000, 2)
        track = rtc.LocalAudioTrack.create_audio_track("microphone", source)
        
        # Publish track
        options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await self.room.local_participant.publish_track(track, options)
        
        return track, source
    
    async def send_data(self, data: Dict, reliable: bool = True):
        """Send data to all participants"""
        if not self.room:
            raise Exception("Not connected to room")
        
        message = json.dumps(data)
        await self.room.local_participant.publish_data(
            message.encode(), 
            reliable=reliable
        )
    
    async def disconnect(self):
        """Disconnect from room"""
        if self.room:
            await self.room.disconnect()
            self.connected = False
    
    async def get_room_info(self, room_name: str) -> Dict:
        """Get room information"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/rooms/{room_name}") as response:
                return await response.json()
    
    async def list_rooms(self) -> Dict:
        """List all active rooms"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/rooms") as response:
                return await response.json()


# Example usage functions
async def simple_broadcaster_example():
    """Example: Simple broadcaster that creates a room and publishes video"""
    client = StreamingClient()
    
    # Create room
    room_result = await client.create_room("test-stream", max_participants=50)
    print(f"Room created: {room_result}")
    
    # Join as broadcaster
    join_result = await client.join_room("test-stream", "broadcaster")
    token = join_result["token"]
    url = join_result["url"]
    
    # Connect to room
    await client.connect_to_room(token, url, "test-stream")
    
    # Publish camera and microphone
    try:
        video_track, video_source = await client.publish_camera()
        audio_track, audio_source = await client.publish_microphone()
        
        print("Broadcasting started! Press Ctrl+C to stop...")
        
        # Keep alive
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("Stopping broadcast...")
    finally:
        await client.disconnect()

async def simple_viewer_example():
    """Example: Simple viewer that joins a room and receives streams"""
    client = StreamingClient()
    
    # Set up callbacks for received streams
    def on_track_subscribed(track, publication, participant):
        print(f"Receiving {track.kind} from {participant.identity}")
        # Handle received track (video/audio)
    
    client.on_event("track_subscribed", on_track_subscribed)
    
    # Join as viewer
    join_result = await client.join_room("test-stream", "viewer-1")
    token = join_result["token"]
    url = join_result["url"]
    
    # Connect to room
    await client.connect_to_room(token, url, "test-stream")
    
    try:
        print("Viewing stream! Press Ctrl+C to stop...")
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        print("Stopping viewer...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # Run broadcaster example
    asyncio.run(simple_broadcaster_example())