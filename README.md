# Call Streaming Server

A Python FastAPI WebSocket relay server for real-time call streaming between Call Transcriber and Call Listener apps.

## Architecture

```
Call Transcriber (Android) <---> Python Server (Render) <---> Call Listener (Android)
```

The server acts as a WebSocket relay, allowing devices to connect from anywhere on the internet without being on the same WiFi network.

## Deployment on Render

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/call-streaming-server.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com)
   - Create a new Web Service
   - Connect your GitHub repository
   - Build settings:
     - Runtime: Python 3
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Click Deploy

3. **Get your Render URL**
   - After deployment, Render will provide a URL like: `https://call-streaming-server.onrender.com`

## API Endpoints

### HTTP Endpoints

- `GET /` - Health check
- `GET /session/create` - Create a new session ID (returns `{"session_id": "uuid"}`)

### WebSocket Endpoints

- `WS /ws/transcriber/{session_id}` - Connect as transcriber (sender)
- `WS /ws/listener/{session_id}` - Connect as listener (receiver)

## Usage

### For Flutter Apps

Update the server URL in both Flutter apps:

**call_transcriber/lib/data/python_stream.dart:**
```dart
static const String _serverUrl = 'https://your-render-app.onrender.com';
```

**call_listener/lib/python_listener.dart:**
```dart
static const String _serverUrl = 'https://your-render-app.onrender.com';
```

### Flow

1. Call Transcriber creates a session ID via `/session/create`
2. Call Transcriber connects to `/ws/transcriber/{session_id}`
3. User shares the session ID with the listener
4. Call Listener connects to `/ws/listener/{session_id}`
5. Server relays all messages from transcriber to listener

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at `http://localhost:8000`
"# call-service-python" 
