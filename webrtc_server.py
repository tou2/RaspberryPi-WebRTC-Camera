#!/usr/bin/env python3
"""
Low-latency WebRTC video streaming server for Raspberry Pi camera.
Optimized for minimal latency and efficient resource usage.
"""

import asyncio
import logging
import subprocess
import time
from typing import Set

from aiohttp import web, web_runner
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCConfiguration,
    RTCIceServer,
)
from av import VideoFrame

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration
CONFIG = {
    "camera_index": 0,  # Camera device index
    "width": 640,       # Video width (lower for Pi Zero)
    "height": 480,      # Video height
    "fps": 30,          # Target FPS
    "bitrate": 500000,  # Target bitrate (500kbps for Pi Zero)
    "host": "0.0.0.0",
    "port": 8080,
    "ice_servers": [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"}
    ]
}

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Zero WebRTC Stream</title>
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
    <h1>🚀 Pi Zero WebRTC Live Stream</h1>
    
    <div class="settings">
        <label for="resolution">Resolution:</label>
        <select id="resolution">
            <option value="640,480">640x480</option>
            <option value="1280,720" selected>1280x720</option>
            <option value="1920,1080">1920x1080</option>
        </select>
        <label for="fps" style="margin-left: 15px;">Frame Rate:</label>
        <select id="fps">
            <option value="15">15 FPS</option>
            <option value="30" selected>30 FPS</option>
            <option value="60">60 FPS</option>
        </select>
    </div>

    <div class="controls">
        <button id="startBtn" onclick="start()">Start Stream</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
        <button id="fullscreenBtn" onclick="toggleFullScreen()" disabled>Fullscreen</button>
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
    
    <script src="/client.js"></script>
</body>
</html>
"""

CLIENT_JS = """
let pc = null;

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
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                updateStatus('Disconnected', 'disconnected');
                stop();
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
        
    } catch (error) {
        console.error('Error starting stream:', error);
        updateStatus('Connection failed', 'disconnected');
        startBtn.disabled = false;
        resolutionSelect.disabled = false;
        fpsSelect.disabled = false;
    }
}

function stop() {
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
    resolutionSelect.disabled = false;
    fpsSelect.disabled = false;
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
"""

class CameraVideoTrack(VideoStreamTrack):
    """
    A video track that streams video from a Raspberry Pi Camera v3 using rpicam-vid.
    This approach is more reliable than using OpenCV's VideoCapture for libcamera-based devices.
    """
    
    def __init__(self, width, height, fps):
        super().__init__()
        self.rpicam_proc = None
        self._buffer = b''
        self.width = width
        self.height = height
        self.fps = fps
        # Calculate the size of a single YUV420p frame.
        self.frame_size = self.width * self.height * 3 // 2
        self._setup_camera()
        
    def _setup_camera(self):
        """Initialize camera using the rpicam-vid command-line tool."""
        try:
            rpicam_cmd = [
                "rpicam-vid",
                "--timeout", "0",  # Run forever
                "--width", str(self.width),
                "--height", str(self.height),
                "--framerate", str(self.fps),
                "--codec", "yuv420p",  # Request raw YUV420p frames
                "--nopreview",
                "--output", "-"  # Output to stdout
            ]
            
            logger.info(f"Starting rpicam-vid process: {' '.join(rpicam_cmd)}")
            self.rpicam_proc = subprocess.Popen(
                rpicam_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a moment and check if the process started correctly
            time.sleep(2)
            if self.rpicam_proc.poll() is not None:
                stderr_output = self.rpicam_proc.stderr.read().decode('utf-8', errors='ignore')
                raise RuntimeError(f"rpicam-vid failed to start. Error: {stderr_output}")

            logger.info("rpicam-vid process started successfully.")

        except FileNotFoundError:
            logger.error("rpicam-vid command not found. Please ensure 'rpicam-apps' is installed ('sudo apt-get install rpicam-apps').")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize rpicam-vid: {e}")
            raise

    async def recv(self):
        """Read the next raw YUV420p frame from the rpicam-vid process."""
        pts, time_base = await self.next_timestamp()
        
        loop = asyncio.get_event_loop()
        
        try:
            # This is a blocking read, so run it in an executor.
            frame_data = await loop.run_in_executor(None, self._read_yuv_frame)
            
            if frame_data:
                # Create a VideoFrame directly from the raw YUV420p buffer.
                # This avoids any decoding/encoding and is very efficient.
                av_frame = VideoFrame.from_buffer(
                    frame_data, width=self.width, height=self.height, format="yuv420p"
                )
                av_frame.pts = pts
                av_frame.time_base = time_base
                return av_frame
        except Exception as e:
            logger.error(f"Error processing frame from rpicam-vid: {e}")

        # This part should ideally not be reached.
        return None

    def _read_yuv_frame(self):
        """
        Reads a single raw YUV420p frame from the stdout of the rpicam-vid process.
        This is a blocking function and should be run in an executor.
        """
        if not self.rpicam_proc or self.rpicam_proc.poll() is not None:
            raise RuntimeError("rpicam-vid process is not running.")

        # Read exactly one frame's worth of bytes.
        # The buffer helps ensure we read a complete frame even if the OS
        # provides the data in smaller chunks.
        while len(self._buffer) < self.frame_size:
            chunk = self.rpicam_proc.stdout.read(4096)
            if not chunk:
                raise EOFError("Camera stream ended.")
            self._buffer += chunk
        
        frame_data = self._buffer[:self.frame_size]
        self._buffer = self._buffer[self.frame_size:]
        return frame_data
    
    def stop(self):
        """Stop the rpicam-vid process."""
        if self.rpicam_proc:
            logger.info("Terminating rpicam-vid process...")
            self.rpicam_proc.terminate()
            try:
                self.rpicam_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.warning("rpicam-vid did not terminate gracefully, killing.")
                self.rpicam_proc.kill()
            self.rpicam_proc = None
            logger.info("rpicam-vid process stopped.")

class WebRTCServer:
    """WebRTC server managing peer connections and signaling."""
    
    def __init__(self):
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.app = web.Application()
        self.video_track = None
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes for signaling and serving static files."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.client_js)
        self.app.router.add_post("/offer", self.offer)
        
    async def index(self, request):
        """Serve the HTML client."""
        return web.Response(text=INDEX_HTML, content_type="text/html")
    
    async def client_js(self, request):
        """Serve the JavaScript client."""
        return web.Response(text=CLIENT_JS, content_type="application/javascript")
    
    async def offer(self, request):
        """Handle WebRTC offer from client."""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Get desired settings from client
            width = int(params.get("width", CONFIG["width"]))
            height = int(params.get("height", CONFIG["height"]))
            fps = int(params.get("fps", CONFIG["fps"]))

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in CONFIG["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)

            # Add to tracking set
            self.peer_connections.add(pc)

            # Create or reuse the video track
            if self.video_track is None:
                logger.info(f"Starting new camera track with {width}x{height} @ {fps}fps")
                self.video_track = CameraVideoTrack(width, height, fps)
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
                        self.video_track.stop()
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
                logger.info(f"Successfully generated answer SDP of length {len(pc.localDescription.sdp)}")
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
        
        logger.info(f"WebRTC server started on http://{CONFIG['host']}:{CONFIG['port']}")
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
                self.video_track.stop()
                
            await runner.cleanup()

async def main():
    """Main function to start the WebRTC server."""
    logger.info("Starting Pi Zero WebRTC Camera Server")
    logger.info(f"Configuration: {CONFIG}")
    
    server = WebRTCServer()
    await server.start_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
