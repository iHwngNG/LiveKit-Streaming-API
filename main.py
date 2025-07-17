# ----- Importing -----
import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from fastapi import FastAPI, HTTPException, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from models import *

from livekit import api
from livekit.protocol import room as room_proto
from livekit import protocol as proto

# ----- Core -----
load_dotenv()

# *Uitlize the API
app = FastAPI(title="LiveKit Streaming Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

livekit_api = api.LiveKitAPI(
    url=LIVEKIT_URL,
    api_key=LIVEKIT_API_KEY,
    api_secret=LIVEKIT_API_SECRET,
)

active_rooms: Dict[str, Dict] = {}
room_participants: Dict[str, List[str]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the streaming platform"""
    print(f"🚀 LiveKit Streaming Platform API starting...")
    print(f"📡 LiveKit Server: {LIVEKIT_URL}")
    
    # Test connection to LiveKit server
    try:
        list_request = room_proto.ListRoomsRequest()
        rooms_response = await livekit_api.room.list_rooms(list_request)
        print(f"✅ Connected to LiveKit server - {len(rooms_response.rooms)} rooms active")
    except Exception as e:
        print(f"❌ Failed to connect to LiveKit server: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "LiveKit Streaming Platform API",
        "status": "active",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/rooms/create")
async def create_room(request: CreateRoomRequest):
    """Create a new streaming room"""
    try:
        # Create room configuration
        room_config = room_proto.CreateRoomRequest(
            name=request.name,
            max_participants=request.max_participants,
            empty_timeout=request.empty_timeout,
            metadata=json.dumps({
                "audio_enabled": request.audio_enabled,
                "video_enabled": request.video_enabled,
                "created_at": datetime.now().isoformat()
            })
        )
        
        # Create room via LiveKit API
        room = await livekit_api.room.create_room(room_config)
        
        # Store room info
        active_rooms[request.name] = {
            "sid": room.sid,
            "name": room.name,
            "max_participants": request.max_participants,
            "created_at": datetime.now(),
            "audio_enabled": request.audio_enabled,
            "video_enabled": request.video_enabled
        }
        print(active_rooms)
        room_participants[request.name] = []
        
        return {
            "success": True,
            "room": {
                "name": room.name,
                "sid": room.sid,
                "max_participants": request.max_participants,
                "created_at": datetime.now().isoformat()
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create room: {str(e)}")

@app.post("/rooms/{room_name}/join")
async def join_room(room_name: str, request: JoinRoomRequest):
    """Generate join token for a participant"""
    try:
        if room_name not in active_rooms:
            raise HTTPException(status_code=404, detail="Room not found")
        
        room_info = active_rooms[room_name]
        
        # Check participant limit
        current_participants = len(room_participants.get(room_name, []))
        if current_participants >= room_info["max_participants"]:
            raise HTTPException(status_code=400, detail="Room is full")
        
        # Set default permissions   
        video_grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=request.is_host,
            can_subscribe=True,
            can_publish_data=request.is_host,
        )
        
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)
        token.with_grants(video_grants)

        jwt_token = token.to_jwt()
        
        # Add participant to room
        if room_name not in room_participants:
            room_participants[room_name] = []
        
        if request.participant_name not in room_participants[room_name]:
            room_participants[room_name].append(request.participant_name)

        jwt_token = token.to_jwt()
        
        return {
            "success": True,
            "token": jwt_token,
            "url": LIVEKIT_URL,
            "room_name": room_name,
            "participant_name": request.participant_name,
            "permissions": video_grants
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to join room: {str(e)}")

@app.get("/rooms", response_model=List[RoomInfo])
async def list_rooms():
    """List all active rooms"""
    try:
        # Create the request object for listing rooms
        list_request = room_proto.ListRoomsRequest()
        rooms_response = await livekit_api.room.list_rooms(list_request)
        
        room_list = []
        for room in rooms_response.rooms:
            room_data = active_rooms.get(room.name, {})
            room_list.append(RoomInfo(
                name=room.name,
                sid=room.sid,
                num_participants=room.num_participants,
                max_participants=room_data.get("max_participants", 100),
                creation_time=room_data.get("created_at", datetime.now()),
                metadata=room.metadata
            ))
        
        return room_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list rooms: {str(e)}")

@app.get("/rooms/{room_name}")
async def get_room_info(room_name: str):
    """Get detailed information about a specific room"""
    try:
        list_request = room_proto.ListRoomsRequest()
        rooms_response = await livekit_api.room.list_rooms(list_request)
        room = next((r for r in rooms_response.rooms if r.name == room_name), None)
        
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Get participants
        participants_request = room_proto.ListParticipantsRequest(room=room_name)
        participants_response = await livekit_api.room.list_participants(participants_request)
        
        participant_list = []
        for p in participants_response.participants:
            participant_list.append({
                "identity": p.identity,
                "name": p.name,
                "joined_at": datetime.fromtimestamp(p.joined_at / 1000).isoformat(),
                "is_publisher": len(p.tracks) > 0,
                "track_count": len(p.tracks)
            })
        
        room_data = active_rooms.get(room_name, {})
        
        return {
            "room": {
                "name": room.name,
                "sid": room.sid,
                "num_participants": room.num_participants,
                "max_participants": room_data.get("max_participants", 100),
                "creation_time": room.creation_time,
                "metadata": room.metadata
            },
            "participants": participant_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get room info: {str(e)}")

@app.delete("/rooms/{room_name}")
async def delete_room(room_name: str):
    """Delete a room and disconnect all participants"""
    try:
        delete_request = room_proto.DeleteRoomRequest(room=room_name)
        await livekit_api.room.delete_room(delete_request)
        
        # Clean up local storage
        if room_name in active_rooms:
            del active_rooms[room_name]
        if room_name in room_participants:
            del room_participants[room_name]
        
        return {"success": True, "message": f"Room {room_name} deleted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete room: {str(e)}")

@app.post("/rooms/{room_name}/participants/{participant_identity}/kick")
async def kick_participant(room_name: str, participant_identity: str):
    """Remove a participant from the room"""
    try:
        remove_request = room_proto.RoomParticipantIdentity(
            room=room_name,
            identity=participant_identity
        )
        # --------------------------------------------------

        # Hàm remove_participant của bạn mong muốn nhận đối tượng này
        await livekit_api.room.remove_participant(remove_request)
        
        # Update local storage
        if room_name in room_participants:
            room_participants[room_name] = [
                p for p in room_participants[room_name] 
                if p != participant_identity
            ]
        
        return {"success": True, "message": f"Participant {participant_identity} removed"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to kick participant: {str(e)}")

@app.post("/rooms/{room_name}/participants/{participant_identity}/mute")
async def mute_participant(room_name: str, participant_identity: str, mute_audio: bool = True):
    """Mute/unmute a participant"""
    try:
        mute_request = room_proto.MuteRoomTrackRequest(
            room=room_name,
            identity=participant_identity,
            track_sid="",  # Empty for all tracks
            muted=mute_audio
        )
        await livekit_api.room.mute_published_track(mute_request)
        
        action = "muted" if mute_audio else "unmuted"
        return {"success": True, "message": f"Participant {participant_identity} {action}"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to mute participant: {str(e)}")

@app.websocket("/ws/rooms/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    """WebSocket endpoint for real-time room updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send periodic room updates
            list_request = room_proto.ListRoomsRequest()
            rooms_response = await livekit_api.room.list_rooms(list_request)
            room = next((r for r in rooms_response.rooms if r.name == room_name), None)
            
            if room:
                await websocket.send_json({
                    "type": "room_update",
                    "data": {
                        "name": room.name,
                        "num_participants": room.num_participants,
                        "timestamp": datetime.now().isoformat()
                    }
                })
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=os.getenv("API_HOST", "localhost"), 
        port=int(os.getenv("API_PORT", 8000)),
        log_level="info"
    )