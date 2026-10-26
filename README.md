# Call Streaming Server

A Python FastAPI WebSocket relay server for real-time call audio streaming and transcription between **Call Transcriber** and **Call Listener** apps.

Deployed URL: `https://call-service-python.onrender.com`

## Architecture

```
Call Transcriber (Android) <--- WSS (PCM audio & JSON) ---> Render Relay Server <--- WSS (PCM audio & JSON) ---> Call Listener (Android / Companion)
```

The server acts as a low-latency WebSocket relay that forwards:
1. **Raw binary PCM16 audio chunks** (16 kHz mono) from caller microphone to listener speaker (`PcmPlayer`).
2. **Text JSON metadata** (caller details, call state, live diarized speech bubbles, VAD).

## API Endpoints

### HTTP Endpoints
- `GET /` - Health check & server status.
- `GET /users` - List all active/online users and their current call states (`online`, `in_call`, `peer_name`, `listeners_count`).
- `GET /session/create` - Legacy session creator.

### WebSocket Endpoints
- `WS /ws/transcriber/{user_id}` - Transcriber client connects here with their unique user ID to broadcast live audio and transcripts.
- `WS /ws/listener/{user_id}` - Listener client connects here to track a specific user's calls.
