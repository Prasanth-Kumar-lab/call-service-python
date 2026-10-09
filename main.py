from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import json
import uuid

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active sessions: session_id -> {transcriber_ws, listener_ws}
sessions: Dict[str, Dict] = {}

class ConnectionManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}

    async def connect_transcriber(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {"transcriber": None, "listeners": set()}
        self.active_sessions[session_id]["transcriber"] = websocket
        print(f"Transcriber connected to session: {session_id}")

    async def connect_listener(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {"transcriber": None, "listeners": set()}
        self.active_sessions[session_id]["listeners"].add(websocket)
        print(f"Listener connected to session: {session_id}")
        
        # Send hello to listener if transcriber is connected
        if self.active_sessions[session_id]["transcriber"]:
            await websocket.send_json({"type": "connected", "session_id": session_id})

    def disconnect_transcriber(self, session_id: str):
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["transcriber"] = None
            print(f"Transcriber disconnected from session: {session_id}")

    def disconnect_listener(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["listeners"].discard(websocket)
            if not self.active_sessions[session_id]["listeners"] and not self.active_sessions[session_id]["transcriber"]:
                del self.active_sessions[session_id]
            print(f"Listener disconnected from session: {session_id}")

    async def broadcast_to_listeners(self, session_id: str, message: str):
        if session_id in self.active_sessions:
            for listener in self.active_sessions[session_id]["listeners"]:
                try:
                    await listener.send_text(message)
                except:
                    # Remove disconnected listener
                    self.active_sessions[session_id]["listeners"].discard(listener)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Call Streaming Server - WebSocket Relay"}

@app.get("/session/create")
async def create_session():
    """Create a new session ID"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

@app.websocket("/ws/transcriber/{session_id}")
async def websocket_transcriber(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for call transcriber (sender)"""
    await manager.connect_transcriber(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast to all listeners in this session
            await manager.broadcast_to_listeners(session_id, data)
    except WebSocketDisconnect:
        manager.disconnect_transcriber(session_id)

@app.websocket("/ws/listener/{session_id}")
async def websocket_listener(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for call listener (receiver)"""
    await manager.connect_listener(websocket, session_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_listener(websocket, session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
