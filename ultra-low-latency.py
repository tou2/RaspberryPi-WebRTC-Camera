#!/usr/bin/env python3
"""
Ultra-low-latency WebRTC video streaming server for Raspberry Pi camera.
Optimized for minimal latency and efficient resource usage.
"""

import asyncio
import logging
import subprocess
import time
import threading
from typing import Set, Optional
from collections import deque
import cv2
from aiohttp import web, web_runner
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCConfiguration,
    RTCIceServer,
)
from av import VideoFrame
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration - optimized for ultra-low latency
CONFIG = {
    "camera_index": 0,
    "width": 320,       # Reduced resolution for lower latency
    "height": 240,      # Reduced resolution
    "fps": 60,          # Higher FPS for smoother streaming
    "bitrate": 1000000, # Higher bitrate for quality
    "host": "0.0.0.0",
    "port": 8080,
    "ice_servers": [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"}
    ],
    "buffer_size": 1,   # Minimal buffer for ultra-low latency
    "queue_size": 2,    # Minimal frame queue
    "jpeg_quality": 85, # JPEG quality (0-100)
}

# Global variables for ultra-low latency
frame_queue = deque(maxlen=CONFIG["queue_size"])
frame_lock = threading.Lock()
frame_available = threading.Event()
camera_process = None
camera_thread = None
camera_running = False

def camera_reader():
    """Ultra-low-latency camera reader thread."""
    global camera_process, camera_running, frame_queue, frame_lock, frame_available
    
    while camera_running:
        try:
            if not camera_process or camera_process.poll() is not None:
                setup_camera_process()
                time.sleep(0.1)
                continue
                
            # Read MJPEG frame directly
            frame_data = read_mjpeg_frame(camera_process.stdout)
            if frame_data:
                # Decode JPEG to numpy array
                arr = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Add to queue (overwrite oldest if full)
                    with frame_lock:
                        if len(frame_queue) >= CONFIG["queue_size"]:
                            frame_queue.popleft()
                        frame_queue.append(frame)
                        frame_available.set()
                        
        except Exception as e:
            logger.error(f"Camera reader error: {e}")
            time.sleep(0.01)

def setup_camera_process():
    """Setup ultra-low-latency camera process."""
    global camera_process
    
    if camera_process:
        try:
            camera_process.terminate()
            camera_process.wait(timeout=1)
        except:
            camera_process.kill()
        camera_process = None
    
    try:
        # Ultra-low-latency rpicam-vid command
        rpicam_cmd = [
            "rpicam-vid",
            "-t", "0",                    # Run forever
            "-n",                         # No preview
            "--width", str(CONFIG["width"]),
            "--height", str(CONFIG["height"]),
            "--framerate", str(CONFIG["fps"]),
            "--brightness", "0.0",        # Neutral brightness
            "--contrast", "1.0",          # Normal contrast
            "--saturation", "1.0",        # Normal saturation
            "--sharpness", "1.0",         # Normal sharpness
            "--quality", str(CONFIG["jpeg_quality"]),  # JPEG quality
            "--codec", "mjpeg",           # MJPEG output
            "--flush",                    # Flush buffers immediately
            "--save-pts", "0",            # No timestamp saving
            "--verbose", "0",             # No verbose output
            "-o", "-"                     # Output to stdout
        ]
        
        logger.info(f"Starting camera with command: {' '.join(rpicam_cmd)}")
        camera_process = subprocess.Popen(
            rpicam_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Suppress stderr for performance
            bufsize=CONFIG["buffer_size"] * 1024 * 1024  # Buffer in MB
        )
        
        # Wait for process to start
        time.sleep(0.2)
        if camera_process.poll() is not None:
            raise RuntimeError("Camera process failed to start")
            
        logger.info("Camera process started successfully")
        
    except FileNotFoundError:
        logger.error("rpicam-vid not found. Install with: sudo apt install rpicam-apps")
        raise
    except Exception as e:
        logger.error(f"Failed to start camera: {e}")
        raise

def read_mjpeg_frame(stream):
    """Ultra-fast MJPEG frame reader."""
    buffer = b''
    
    # Find start marker
    while True:
        data = stream.read(1024)
        if not data:
            return None
        buffer += data
        start_idx = buffer.find(b'\xff\xd8')
        if start_idx != -1:
            buffer = buffer[start_idx:]
            break
    
    # Find end marker
    while True:
        end_idx = buffer.find(b'\xff\xd9')
        if end_idx != -1:
            frame = buffer[:end_idx+2]
            # Keep remaining data for next frame
            buffer = buffer[end_idx+2:]
            return frame
        
        data = stream.read(1024)
        if not data:
            return None
        buffer += data

def start_camera():
    """Start ultra-low-latency camera capture."""
    global camera_thread, camera_running
    
    camera_running = True
    setup_camera_process()
    camera_thread = threading.Thread(target=camera_reader, daemon=True)
    camera_thread.start()
    logger.info("Camera capture started")

def stop_camera():
    """Stop camera capture."""
    global camera_running, camera_process, camera_thread
    
    camera_running = False
    
    if camera_process:
        try:
            camera_process.terminate()
            camera_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            camera_process.kill()
        except:
            pass
        camera_process = None
    
    if camera_thread and camera_thread.is_alive():
        camera_thread.join(timeout=1)
    
    with frame_lock:
        frame_queue.clear()
    
    frame_available.clear()
    logger.info("Camera capture stopped")

class UltraLowLatencyVideoTrack(VideoStreamTrack):
    """Ultra-low-latency video track implementation."""
    
    def __init__(self):
        super().__init__()
        self.rotation = 0
        
    async def recv(self):
        """Receive next video frame with ultra-low latency."""
        pts, time_base = await self.next_timestamp()
        
        # Wait for frame with timeout
        if not frame_available.wait(timeout=0.1):
            # Return black frame if no frame available
            black_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
            av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            return av_frame
        
        # Get frame from queue
        with frame_lock:
            if frame_queue:
                frame = frame_queue.popleft()
                if not frame_queue:
                    frame_available.clear()
            else:
                frame_available.clear()
                black_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
                av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
                av_frame.pts = pts
                av_frame.time_base = time_base
                return av_frame
        
        # Apply rotation if needed
        if self.rotation != 0:
            if self.rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif self.rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif self.rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Convert to VideoFrame
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        return av_frame
    
    async def rotate(self):
        """Rotate camera by 90 degrees."""
        self.rotation = (self.rotation + 90) % 360
        logger.info(f"Camera rotated to {self.rotation} degrees")

class UltraLowLatencyWebRTCServer:
    """Ultra-low-latency WebRTC server."""
    
    def __init__(self):
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.app = web.Application()
        self.video_track: Optional[UltraLowLatencyVideoTrack] = None
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.client_js)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_post("/rotate", self.rotate_camera)
        
    async def index(self, request):
        """Serve the HTML client."""
        return web.Response(text=INDEX_HTML, content_type="text/html")
    
    async def client_js(self, request):
        """Serve the JavaScript client."""
        return web.Response(text=CLIENT_JS, content_type="application/javascript")
    
    async def rotate_camera(self, request):
        """Handle camera rotation request."""
        if self.video_track:
            await self.video_track.rotate()
            return web.Response(status=200)
        return web.Response(status=400, text="Video track not available")

    async def offer(self, request):
        """Handle WebRTC offer from client."""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Get desired settings from client
            width = int(params.get("width", CONFIG["width"]))
            height = int(params.get("height", CONFIG["height"]))
            fps = int(params.get("fps", CONFIG["fps"]))

            # Validate settings
            if width != CONFIG["width"] or height != CONFIG["height"] or fps != CONFIG["fps"]:
                logger.warning(f"Client requested {width}x{height}@{fps}fps, but using {CONFIG['width']}x{CONFIG['height']}@{CONFIG['fps']}fps for ultra-low latency")

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in CONFIG["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)
            self.peer_connections.add(pc)

            # Create or reuse the video track
            if self.video_track is None:
                logger.info("Starting new ultra-low-latency camera track")
                self.video_track = UltraLowLatencyVideoTrack()
                start_camera()
            else:
                logger.info("Reusing existing camera track.")

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state: {pc.connectionState}")
                if pc.connectionState in ("failed", "closed", "disconnected"):
                    await pc.close()
                    self.peer_connections.discard(pc)
                    if not self.peer_connections and self.video_track:
                        logger.info("Last peer disconnected, stopping camera.")
                        stop_camera()
                        self.video_track = None
            
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state: {pc.iceConnectionState}")
            
            # Add video track
            logger.info("Adding video track.")
            pc.addTrack(self.video_track)
            
            # Set remote description
            logger.info("Setting remote description...")
            await pc.setRemoteDescription(offer)

            logger.info("Creating answer...")
            answer = await pc.createAnswer()

            logger.info("Setting local description...")
            await pc.setLocalDescription(answer)

            if pc.localDescription and pc.localDescription.sdp:
                logger.info(f"Successfully generated answer SDP")
                return web.json_response({
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                })
            else:
                logger.error("Failed to generate valid local description.")
                return web.json_response({"error": "Server failed to generate SDP answer"}, status=500)
            
        except Exception as e:
            logger.error(f"Error handling offer: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def start_server(self):
        """Start the web server."""
        runner = web_runner.AppRunner(self.app)
        await runner.setup()
        
        site = web_runner.TCPSite(
            runner, 
            CONFIG["host"], 
            CONFIG["port"]
        )
        await site.start()
        
        logger.info(f"Ultra-low-latency WebRTC server started on http://{CONFIG['host']}:{CONFIG['port']}")
        logger.info("Open the URL in your browser to view the stream")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            # Clean up connections
            for pc in self.peer_connections.copy():
                await pc.close()
            self.peer_connections.clear()
            
            # Stop the camera track
            if self.video_track:
                logger.info("Server shutting down, stopping camera.")
                stop_camera()
                
            await runner.cleanup()

# HTML and JavaScript content (same as original)
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Zero Ultra-Low Latency WebRTC Stream</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: #4CAF50;
            margin-bottom: 20px;
        }
        video {
            width: 100%;
            max-width: 800px;
            height: auto;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            background-color: #000;
        }
        .settings {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
        }
        select {
            padding: 8px;
            border-radius: 4px;
            background-color: #333;
            color: white;
            border: 1px solid #555;
            font-size: 14px;
        }
        .controls {
            margin: 20px 0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        button {
            padding: 12px 24px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #666;
            cursor: not-allowed;
        }
        .status {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        .status.connected {
            background-color: #2d5a2d;
            color: #90EE90;
        }
        .status.connecting {
            background-color: #5a5a2d;
            color: #FFFF90;
        }
        .status.disconnected {
            background-color: #5a2d2d;
            color: #FF9090;
        }
        .stats {
            margin: 20px 0;
            padding: 15px;
            background-color: #2a2a2a;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            text-align: left;
            max-width: 800px;
        }
    </style>
</head>
<body>
    <h1>🚀 Pi Zero Ultra-Low Latency WebRTC Stream</h1>
    
    <div class="settings">
        <label for="resolution">Resolution:</label>
        <select id="resolution">
            <option value="320,240" selected>320x240 (Ultra-low latency)</option>
            <option value="640,480">640x480</option>
        </select>
        <label for="fps" style="margin-left: 15px;">Frame Rate:</label>
        <select id="fps">
            <option value="30">30 FPS</option>
            <option value="60" selected>60 FPS (Ultra-low latency)</option>
        </select>
    </div>

    <div class="controls">
        <button id="startBtn" onclick="start()">Start Stream</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
        <button id="fullscreenBtn" onclick="toggleFullScreen()" disabled>Fullscreen</button>
        <button id="rotateBtn" onclick="rotate()" disabled>Rotate</button>
    </div>
    
    <div id="status" class="status disconnected">Disconnected</div>
    
    <video id="video" autoplay playsinline muted></video>
    
    <div id="stats" class="stats" style="display: none;">
        <div>Connection State: <span id="connectionState">-</span></div>
        <div>ICE Connection State: <span id="iceConnectionState">-</span></div>
        <div>Bytes Received: <span id="bytesReceived">-</span></div>
        <div>Packets Received: <span id="packetsReceived">-</span></div>
        <div>Packets Lost: <span id="packetsLost">-</span></div>
        <div>Frame Rate: <span id="frameRate">-</span></div>
    </div>
    
    <script>
        let pc = null;
        let reconnectTimer = null;

        const configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };

        function updateStatus(message, className) {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = `status ${className}`;
        }

        function updateStats() {
            if (!pc) return;
            
            pc.getStats().then(stats => {
                const statsDiv = document.getElementById('stats');
                statsDiv.style.display = 'block';
                
                stats.forEach(report => {
                    if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
                        document.getElementById('bytesReceived').textContent = report.bytesReceived || '-';
                        document.getElementById('packetsReceived').textContent = report.packetsReceived || '-';
                        document.getElementById('packetsLost').textContent = report.packetsLost || '-';
                        
                        if (report.framesPerSecond) {
                            document.getElementById('frameRate').textContent = report.framesPerSecond.toFixed(1) + ' fps';
                        }
                    }
                });
                
                document.getElementById('connectionState').textContent = pc.connectionState;
                document.getElementById('iceConnectionState').textContent = pc.iceConnectionState;
            });
        }

        async function start() {
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const resolutionSelect = document.getElementById('resolution');
            const fpsSelect = document.getElementById('fps');
            
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            
            startBtn.disabled = true;
            resolutionSelect.disabled = true;
            fpsSelect.disabled = true;
            updateStatus('Connecting...', 'connecting');
            
            try {
                pc = new RTCPeerConnection(configuration);
                
                pc.onconnectionstatechange = () => {
                    console.log('Connection state:', pc.connectionState);
                    if (pc.connectionState === 'connected') {
                        updateStatus('Connected', 'connected');
                        setInterval(updateStats, 1000);
                        if (reconnectTimer) {
                            clearTimeout(reconnectTimer);
                            reconnectTimer = null;
                        }
                    } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                        console.log('Connection failed or disconnected, attempting to reconnect...');
                        updateStatus('Connection lost, reconnecting...', 'connecting');
                        if (pc) {
                            pc.close();
                            pc = null;
                        }
                        if (!reconnectTimer) {
                            reconnectTimer = setTimeout(start, 5000);
                        }
                    }
                };
                
                pc.oniceconnectionstatechange = () => {
                    console.log('ICE connection state:', pc.iceConnectionState);
                };
                
                pc.ontrack = (event) => {
                    console.log('Received remote stream');
                    const video = document.getElementById('video');
                    video.srcObject = event.streams[0];
                };
                
                // Get settings from UI
                const resolution = resolutionSelect.value.split(',');
                const width = parseInt(resolution[0], 10);
                const height = parseInt(resolution[1], 10);
                const fps = parseInt(fpsSelect.value, 10);

                // Create offer for video only
                const offer = await pc.createOffer({
                    offerToReceiveVideo: true,
                    offerToReceiveAudio: false
                });
                await pc.setLocalDescription(offer);
                
                // Send offer to server
                const response = await fetch('/offer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        sdp: offer.sdp,
                        type: offer.type,
                        width: width,
                        height: height,
                        fps: fps,
                    }),
                });
                
                const answer = await response.json();
                await pc.setRemoteDescription(new RTCSessionDescription(answer));
                
                stopBtn.disabled = false;
                document.getElementById('fullscreenBtn').disabled = false;
                document.getElementById('rotateBtn').disabled = false;
                
            } catch (error) {
                console.error('Error starting stream:', error);
                updateStatus('Connection failed', 'disconnected');
                startBtn.disabled = false;
                resolutionSelect.disabled = false;
                fpsSelect.disabled = false;
            }
        }

        function stop() {
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }

            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const statsDiv = document.getElementById('stats');
            const resolutionSelect = document.getElementById('resolution');
            const fpsSelect = document.getElementById('fps');
            
            if (pc) {
                pc.close();
                pc = null;
            }
            
            const video = document.getElementById('video');
            video.srcObject = null;
            
            updateStatus('Disconnected', 'disconnected');
            statsDiv.style.display = 'none';
            
            startBtn.disabled = false;
            stopBtn.disabled = true;
            document.getElementById('fullscreenBtn').disabled = true;
            document.getElementById('rotateBtn').disabled = true;
            resolutionSelect.disabled = false;
            fpsSelect.disabled = false;
        }

        async function rotate() {
            console.log('Requesting camera rotation');
            try {
                const response = await fetch('/rotate', { method: 'POST' });
                if (response.ok) {
                    console.log('Camera rotation request successful');
                } else {
                    console.error('Failed to rotate camera');
                }
            } catch (error) {
                console.error('Error rotating camera:', error);
            }
        }

        function toggleFullScreen() {
            const video = document.getElementById('video');
            if (!document.fullscreenElement) {
                video.requestFullscreen().catch(err => {
                    alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
                });
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        }

        // Handle page visibility changes to maintain connection
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && pc) {
                console.log('Page hidden, maintaining connection');
            } else if (!document.hidden && pc) {
                console.log('Page visible, checking connection');
            }
        });
    </script>
</body>
</html>
"""

CLIENT_JS = """
// Client JS is embedded in INDEX_HTML above
"""

async def main():
    """Main function to start the ultra-low-latency WebRTC server."""
    logger.info("Starting Ultra-Low Latency Pi Zero WebRTC Camera Server")
    logger.info(f"Configuration: {CONFIG}")
    
    server = UltraLowLatencyWebRTCServer()
    await server.start_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")