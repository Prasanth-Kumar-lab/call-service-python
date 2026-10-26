from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, Union, Optional
import json
import uuid
import os

app = FastAPI(title="Call Streaming WebSocket Relay")

PORT = int(os.getenv("PORT", 8000))

# Enable CORS for web and client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.transcriber: Optional[WebSocket] = None
        self.listeners: Set[WebSocket] = set()
        self.latest_state: dict = {
            "phase": "idle",
            "peerName": None,
            "peerNumber": None,
            "youName": "You",
            "outgoing": False,
            "startedAt": 0,
            "language": "auto",
        }

class ConnectionManager:
    def __init__(self):
        self.active_sessions: Dict[str, UserSession] = {}

    def get_or_create(self, user_id: str) -> UserSession:
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = UserSession(user_id)
        return self.active_sessions[user_id]

    async def connect_transcriber(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        session = self.get_or_create(user_id)
        session.transcriber = websocket
        print(f"[Transcriber Connected] User: {user_id}")

    async def connect_listener(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        session = self.get_or_create(user_id)
        session.listeners.add(websocket)
        print(f"[Listener Connected] User: {user_id} (Total listeners: {len(session.listeners)})")
        
        # Send initial snapshot immediately to the listener
        hello_data = {
            "type": "hello",
            "user_id": user_id,
            "online": session.transcriber is not None,
            **session.latest_state,
        }
        await websocket.send_text(json.dumps(hello_data))

    def disconnect_transcriber(self, user_id: str):
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session.transcriber = None
            session.latest_state["phase"] = "idle"
            print(f"[Transcriber Disconnected] User: {user_id}")

    def disconnect_listener(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            session.listeners.discard(websocket)
            print(f"[Listener Disconnected] User: {user_id}")
            if not session.listeners and session.transcriber is None:
                del self.active_sessions[user_id]

    async def broadcast_to_listeners(self, user_id: str, message: Union[str, bytes]):
        session = self.active_sessions.get(user_id)
        if not session or not session.listeners:
            return
        dead = []
        for listener in list(session.listeners):
            try:
                if isinstance(message, str):
                    await listener.send_text(message)
                else:
                    await listener.send_bytes(message)
            except Exception:
                dead.append(listener)
        for listener in dead:
            session.listeners.discard(listener)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Call Streaming Relay",
        "active_users_count": len(manager.active_sessions)
    }

@app.get("/users")
async def list_users():
    """List all active users/sessions and their live call status."""
    users_list = []
    for user_id, session in manager.active_sessions.items():
        state = session.latest_state
        users_list.append({
            "user_id": user_id,
            "online": session.transcriber is not None,
            "in_call": state.get("phase") == "active",
            "phase": state.get("phase", "idle"),
            "peer_name": state.get("peerName") or state.get("name"),
            "peer_number": state.get("peerNumber") or state.get("number"),
            "you_name": state.get("youName", "You"),
            "listeners_count": len(session.listeners),
        })
    return {"users": users_list}

@app.get("/session/create")
async def create_session():
    """Legacy helper for session creation."""
    return {"session_id": str(uuid.uuid4())}

@app.websocket("/ws/transcriber/{user_id}")
async def websocket_transcriber(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for Call Transcriber (sender). Supports both PCM audio bytes and text JSON."""
    await manager.connect_transcriber(websocket, user_id)
    session = manager.get_or_create(user_id)
    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg:
                text_content = msg["text"]
                try:
                    data = json.loads(text_content)
                    msg_type = data.get("type")
                    if msg_type in ("call", "state", "hello"):
                        for key in ("phase", "peerName", "peerNumber", "name", "number", "youName", "language", "outgoing", "startedAt"):
                            if key in data:
                                session.latest_state[key] = data[key]
                except Exception:
                    pass
                # Broadcast JSON text to listeners
                await manager.broadcast_to_listeners(user_id, text_content)
            elif "bytes" in msg:
                # Broadcast raw binary audio chunks (PCM16) to listeners
                await manager.broadcast_to_listeners(user_id, msg["bytes"])
    except WebSocketDisconnect:
        manager.disconnect_transcriber(user_id)
        # Inform listeners that call phase is idle
        idle_msg = json.dumps({"type": "state", "phase": "idle", "online": False})
        await manager.broadcast_to_listeners(user_id, idle_msg)

@app.websocket("/ws/listener/{user_id}")
async def websocket_listener(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for Call Listener (receiver)."""
    await manager.connect_listener(websocket, user_id)
    try:
        while True:
            # Keep listener connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_listener(websocket, user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
