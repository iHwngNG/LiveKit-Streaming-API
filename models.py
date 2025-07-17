from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime

class CreateRoomRequest(BaseModel):
    name: str
    max_participants: int = 100
    empty_timeout: int = 300  # 5 minutes
    audio_enabled: bool = True
    video_enabled: bool = True

class JoinRoomRequest(BaseModel):
    participant_name: str
    is_host: bool = False
    permissions: Optional[Dict[str, bool]] = None

class RoomInfo(BaseModel):
    name: str
    sid: str
    num_participants: int
    max_participants: int
    creation_time: datetime
    metadata: Optional[str] = None

class ParticipantInfo(BaseModel):
    identity: str
    name: str
    room_name: str
    joined_at: datetime
    permissions: Dict[str, bool]