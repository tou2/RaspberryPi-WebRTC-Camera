#!/usr/bin/env python3
"""
Low-latency WebRTC video streaming server for Raspberry Pi Zero camera.
Optimized for minimal latency and efficient resource usage.
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Dict, Set

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

class CameraVideoTrack(VideoStreamTrack):
    """
    Custom video track that captures from camera with optimizations for low latency.
    """
    
    def __init__(self):
        super().__init__()
        self.cap = None
        self._setup_camera()
        self.frame_count = 0
        self.last_frame_time = time.time()
        
    def _setup_camera(self):
        """Initialize camera with optimal settings for low latency."""
        try:
            # Explicitly use the V4L2 backend for libcamera compatibility
            logger.info("Using V4L2 backend for camera capture.")
            self.cap = cv2.VideoCapture(CONFIG["camera_index"], cv2.CAP_V4L2)
            
            # Set camera properties for low latency
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["width"])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["height"])
            self.cap.set(cv2.CAP_PROP_FPS, CONFIG["fps"])
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer for low latency
            
            # The FOURCC setting can be problematic with libcamera, so it's removed.
            # The driver will select a default compatible format.

            # Allow camera to warm up
            logger.info("Allowing camera to warm up for 2 seconds...")
            time.sleep(2)

            if not self.cap.isOpened():
                raise ConnectionError("Camera could not be opened.")
            
            logger.info(f"Camera initialized: {CONFIG['width']}x{CONFIG['height']} @ {CONFIG['fps']}fps")
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise
    
    async def recv(self):
        """Receive the next video frame."""
        pts, time_base = await self.next_timestamp()
        
        if self.cap is None or not self.cap.isOpened():
            logger.error("Camera not available")
            # Return a black frame as fallback
            frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
        else:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to capture frame")
                frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
        
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create VideoFrame
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        # Log FPS periodically
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_frame_time >= 5.0:  # Every 5 seconds
            fps = self.frame_count / (current_time - self.last_frame_time)
            logger.info(f"Streaming at {fps:.1f} FPS")
            self.frame_count = 0
            self.last_frame_time = current_time
        
        return av_frame
    
    def stop(self):
        """Clean up camera resources."""
        if self.cap:
            self.cap.release()
            logger.info("Camera released")

class WebRTCServer:
    """WebRTC server managing peer connections and signaling."""
    
    def __init__(self):
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes for signaling and serving static files."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.client_js)
        self.app.router.add_post("/offer", self.offer)
        
    async def index(self, request):
        """Serve the HTML client."""
        html_content = """
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
    
    <div class="controls">
        <button id="startBtn" onclick="start()">Start Stream</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
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
        return web.Response(text=html_content, content_type="text/html")
    
    async def client_js(self, request):
        """Serve the JavaScript client."""
        js_content = """
let pc = null;
let localStream = null;

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
    
    startBtn.disabled = true;
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
            }),
        });
        
        const answer = await response.json();
        await pc.setRemoteDescription(new RTCSessionDescription(answer));
        
        stopBtn.disabled = false;
        
    } catch (error) {
        console.error('Error starting stream:', error);
        updateStatus('Connection failed', 'disconnected');
        startBtn.disabled = false;
    }
}

function stop() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statsDiv = document.getElementById('stats');
    
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
        return web.Response(text=js_content, content_type="application/javascript")
    
    async def offer(self, request):
        """Handle WebRTC offer from client."""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in CONFIG["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)

            # Add to tracking set
            self.peer_connections.add(pc)

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state: {pc.connectionState}")
                if pc.connectionState == "closed":
                    self.peer_connections.discard(pc)
            
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state: {pc.iceConnectionState}")
            
            # Add video track
            logger.info("Adding video track.")
            pc.addTrack(CameraVideoTrack())
            
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
