#!/usr/bin/env python3
"""
Ultra-Low Latency Pi Camera WebRTC Streaming Server
Optimized for minimal latency with enhanced features
"""

import asyncio
import logging
import subprocess
import time
import threading
import queue
import cv2
import numpy as np
from typing import Set, Optional
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

# Ultra-low latency configuration
CONFIG = {
    "width": 320,           # Ultra-low latency resolution
    "height": 240,          # Ultra-low latency resolution
    "fps": 60,              # Higher FPS for smoother streaming
    "quality": 75,          # Lower quality for speed
    "sharpness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "brightness": 0.0,
    "denoise": "cdn_off",   # Disable denoise for speed
    "host": "0.0.0.0",
    "port": 8080,
    "ice_servers": [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"}
    ],
    "queue_size": 1,        # Minimal queue for lowest latency
    "low_latency": True,
}

# Global variables
frame_queue = queue.Queue(maxsize=CONFIG["queue_size"])
camera_process = None
camera_thread = None
camera_running = False

def camera_reader():
    """Camera reader optimized for ultra-low latency."""
    global camera_process, camera_running, frame_queue
    
    buffer = b''
    
    while camera_running:
        try:
            if not camera_process or camera_process.poll() is not None:
                setup_camera_process()
                buffer = b''  # Reset buffer
                time.sleep(0.05)  # Shorter wait for faster restart
                continue
                
            # Read data from camera process (smaller chunks for responsiveness)
            data = camera_process.stdout.read(2048)
            if not data:
                continue
                
            buffer += data
            
            # Look for JPEG frames in the buffer
            while True:
                # Find start of JPEG
                start_idx = buffer.find(b'\xff\xd8')
                if start_idx == -1:
                    break
                    
                # Find end of JPEG
                end_idx = buffer.find(b'\xff\xd9', start_idx)
                if end_idx == -1:
                    break
                    
                # Extract JPEG frame
                jpeg_data = buffer[start_idx:end_idx+2]
                buffer = buffer[end_idx+2:]
                
                # Decode JPEG to numpy array
                try:
                    nparr = np.frombuffer(jpeg_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Add to queue (overwrite if full for lowest latency)
                        try:
                            frame_queue.put(frame, block=False)
                        except queue.Full:
                            try:
                                frame_queue.get_nowait()  # Remove oldest
                                frame_queue.put(frame, block=False)
                            except:
                                pass
                except Exception as e:
                    logger.error(f"Frame decode error: {e}")
                    
        except Exception as e:
            logger.error(f"Camera reader error: {e}")
            time.sleep(0.001)  # Very short sleep

def setup_camera_process():
    """Setup camera process with ultra-low latency settings."""
    global camera_process
    
    if camera_process:
        try:
            camera_process.terminate()
            camera_process.wait(timeout=1)
        except:
            camera_process.kill()
        camera_process = None
    
    try:
        # Ultra-low latency optimized camera command
        rpicam_cmd = [
            "rpicam-vid",
            "-t", "0",              # Run forever
            "-n",                   # No preview
            "--width", str(CONFIG["width"]),
            "--height", str(CONFIG["height"]),
            "--framerate", str(CONFIG["fps"]),
            "--codec", "mjpeg",     # MJPEG output
            "--quality", str(CONFIG["quality"]),      # Optimized quality
            "--sharpness", str(CONFIG["sharpness"]),  # Sharpness
            "--contrast", str(CONFIG["contrast"]),    # Contrast
            "--saturation", str(CONFIG["saturation"]), # Saturation
            "--brightness", str(CONFIG["brightness"]), # Brightness
            "--denoise", CONFIG["denoise"],           # Minimal denoise
            "--awb", "auto",        # Auto white balance
            "--flush",              # Immediate flush for low latency
            "--save-pts", "0",      # No timestamp saving
            "--verbose", "0",       # No verbose output
            "-o", "-"               # Output to stdout
        ]
        
        # Remove empty arguments
        rpicam_cmd = [arg for arg in rpicam_cmd if arg]
        
        logger.info(f"Starting ultra-low latency camera with: {' '.join(rpicam_cmd)}")
        camera_process = subprocess.Popen(
            rpicam_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=256*1024  # Smaller buffer for responsiveness
        )
        
        # Very fast startup check
        time.sleep(0.1)
        if camera_process.poll() is not None:
            stderr_output = camera_process.stderr.read().decode('utf-8', errors='ignore')
            logger.error(f"Camera process failed: {stderr_output}")
            raise RuntimeError(f"Camera process failed: {stderr_output}")
            
        logger.info("Ultra-low latency camera started successfully")
        
    except FileNotFoundError:
        logger.error("rpicam-vid not found. Install with: sudo apt install rpicam-apps")
        raise
    except Exception as e:
        logger.error(f"Failed to start camera: {e}")
        raise

def start_camera():
    """Start camera capture."""
    global camera_thread, camera_running
    
    camera_running = True
    setup_camera_process()
    camera_thread = threading.Thread(target=camera_reader, daemon=True)
    camera_thread.start()
    logger.info("Ultra-low latency camera capture started")

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
    
    # Clear queue
    while not frame_queue.empty():
        try:
            frame_queue.get_nowait()
        except:
            break
    
    logger.info("Camera capture stopped")

class CameraVideoTrack(VideoStreamTrack):
    """Video track optimized for ultra-low latency."""
    
    def __init__(self):
        super().__init__()
        self.rotation = 0
        self.frame_counter = 0
        
    async def recv(self):
        """Receive next video frame with ultra-low latency."""
        pts, time_base = await self.next_timestamp()
        
        try:
            # Get frame from queue with very short timeout
            frame = frame_queue.get(timeout=0.05)  # 50ms timeout
            
            # Apply rotation if needed
            if self.rotation != 0:
                rotation_map = {
                    90: cv2.ROTATE_90_CLOCKWISE,
                    180: cv2.ROTATE_180,
                    270: cv2.ROTATE_90_COUNTERCLOCKWISE
                }
                if self.rotation in rotation_map:
                    frame = cv2.rotate(frame, rotation_map[self.rotation])
            
            # Convert BGR to RGB (OpenCV uses BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to VideoFrame
            av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            
            return av_frame
            
        except queue.Empty:
            # Return black frame if no frame available (keeps stream alive)
            black_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
            av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            return av_frame
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            # Return black frame on error
            black_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
            av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            return av_frame
    
    async def rotate(self):
        """Rotate camera by 90 degrees."""
        self.rotation = (self.rotation + 90) % 360
        logger.info(f"Camera rotated to {self.rotation} degrees")

class WebRTCServer:
    """Ultra-low latency WebRTC server."""
    
    def __init__(self):
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.app = web.Application()
        self.video_track: Optional[CameraVideoTrack] = None
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.client_js)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_post("/rotate", self.rotate_camera)
        self.app.router.add_post("/snapshot", self.snapshot)
        
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
    
    async def snapshot(self, request):
        """Handle snapshot request."""
        return web.Response(status=200, text="Snapshot functionality available")

    async def offer(self, request):
        """Handle WebRTC offer from client with ultra-low latency."""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Get desired settings from client
            width = int(params.get("width", CONFIG["width"]))
            height = int(params.get("height", CONFIG["height"]))
            fps = int(params.get("fps", CONFIG["fps"]))
            quality = int(params.get("quality", CONFIG["quality"]))
            sharpness = float(params.get("sharpness", CONFIG["sharpness"]))
            contrast = float(params.get("contrast", CONFIG["contrast"]))
            saturation = float(params.get("saturation", CONFIG["saturation"]))
            brightness = float(params.get("brightness", CONFIG["brightness"]))
            latency_mode = params.get("latencyMode", "ultra")

            # Apply latency mode presets for ultra-low latency
            if latency_mode == "ultra":
                width, height = 320, 240
                fps = 60
                quality = 70
            elif latency_mode == "low":
                width, height = 640, 480
                fps = 30
                quality = 75

            # Update global config
            CONFIG["width"] = width
            CONFIG["height"] = height
            CONFIG["fps"] = fps
            CONFIG["quality"] = quality
            CONFIG["sharpness"] = sharpness
            CONFIG["contrast"] = contrast
            CONFIG["saturation"] = saturation
            CONFIG["brightness"] = brightness

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in CONFIG["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)
            self.peer_connections.add(pc)

            # Create or reuse the video track
            if self.video_track is None:
                logger.info("Starting ultra-low latency camera track")
                self.video_track = CameraVideoTrack()
                start_camera()
            else:
                logger.info("Reusing existing camera track.")
                # Restart camera if resolution/FPS changed significantly
                if (width != CONFIG["width"] or 
                    height != CONFIG["height"] or 
                    fps != CONFIG["fps"]):
                    logger.info("Restarting camera with new settings for ultra-low latency")
                    stop_camera()
                    start_camera()

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
            logger.info("Adding ultra-low latency video track.")
            pc.addTrack(self.video_track)
            
            # Set remote description
            await pc.setRemoteDescription(offer)

            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            if pc.localDescription and pc.localDescription.sdp:
                logger.info("Successfully generated ultra-low latency answer SDP")
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
        """Start the ultra-low latency web server."""
        runner = web_runner.AppRunner(self.app)
        await runner.setup()
        
        site = web_runner.TCPSite(
            runner, 
            CONFIG["host"], 
            CONFIG["port"]
        )
        await site.start()
        
        logger.info(f"Ultra-Low Latency WebRTC server started on http://{CONFIG['host']}:{CONFIG['port']}")
        logger.info("Open the URL in your browser to view the stream")
        logger.info(f"Ultra-low latency mode: {CONFIG['width']}x{CONFIG['height']}@{CONFIG['fps']}fps")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down ultra-low latency server...")
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

# Enhanced HTML with ultra-low latency options
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Ultra-Low Latency Pi Camera WebRTC Stream</title>
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
            font-size: 1.5em;
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
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
            background: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            width: 100%;
            max-width: 800px;
        }
        .setting-group {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        label {
            font-size: 14px;
            white-space: nowrap;
        }
        select, input[type="range"] {
            padding: 5px;
            border-radius: 4px;
            background-color: #333;
            color: white;
            border: 1px solid #555;
            font-size: 13px;
        }
        select {
            padding: 8px;
        }
        input[type="range"] {
            width: 80px;
        }
        .controls {
            margin: 15px 0;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        button {
            padding: 12px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
            white-space: nowrap;
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
            text-align: center;
            width: 100%;
            max-width: 800px;
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
            margin: 15px 0;
            padding: 15px;
            background-color: #2a2a2a;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            text-align: left;
            width: 100%;
            max-width: 800px;
            display: none;
        }
        .advanced-settings {
            margin: 10px 0;
            padding: 15px;
            background: #333;
            border-radius: 8px;
            width: 100%;
            max-width: 800px;
            display: none;
        }
        .advanced-settings h3 {
            margin-top: 0;
            color: #4CAF50;
            font-size: 1.2em;
        }
        .advanced-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }
        .advanced-control {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
        }
        .value-display {
            font-size: 12px;
            color: #4CAF50;
            min-width: 30px;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>Ultra-Low Latency Pi Camera Stream</h1>
    
    <div class="settings">
        <div class="setting-group">
            <label for="latencyMode">Mode:</label>
            <select id="latencyMode">
                <option value="ultra" selected>Ultra-Low Latency (320x240@60fps)</option>
                <option value="low">Low Latency (640x480@30fps)</option>
                <option value="balanced">Balanced</option>
                <option value="quality">High Quality</option>
            </select>
        </div>
        
        <div class="setting-group">
            <label for="resolution">Res:</label>
            <select id="resolution">
                <option value="320,240" selected>320x240</option>
                <option value="640,480">640x480</option>
                <option value="800,600">800x600</option>
                <option value="1280,720">1280x720</option>
            </select>
        </div>
        
        <div class="setting-group">
            <label for="fps">FPS:</label>
            <select id="fps">
                <option value="15">15 FPS</option>
                <option value="30">30 FPS</option>
                <option value="60" selected>60 FPS</option>
                <option value="90">90 FPS</option>
            </select>
        </div>
        
        <div class="setting-group">
            <label for="quality">Quality:</label>
            <input type="range" id="quality" min="50" max="100" value="75">
            <span id="qualityValue" class="value-display">75</span>
        </div>
    </div>

    <button onclick="toggleAdvancedSettings()" style="margin-bottom: 10px;">Advanced Settings</button>
    
    <div class="advanced-settings" id="advancedSettings">
        <h3>Advanced Camera Settings</h3>
        <div class="advanced-controls">
            <div class="advanced-control">
                <label>Sharpness:</label>
                <input type="range" id="sharpness" min="0" max="200" value="100">
                <span id="sharpnessValue" class="value-display">1.0</span>
            </div>
            
            <div class="advanced-control">
                <label>Contrast:</label>
                <input type="range" id="contrast" min="0" max="200" value="100">
                <span id="contrastValue" class="value-display">1.0</span>
            </div>
            
            <div class="advanced-control">
                <label>Saturation:</label>
                <input type="range" id="saturation" min="0" max="200" value="100">
                <span id="saturationValue" class="value-display">1.0</span>
            </div>
            
            <div class="advanced-control">
                <label>Brightness:</label>
                <input type="range" id="brightness" min="0" max="200" value="100">
                <span id="brightnessValue" class="value-display">0.0</span>
            </div>
            
            <button onclick="resetAdvancedSettings()">Reset</button>
        </div>
    </div>

    <div class="controls">
        <button id="startBtn" onclick="start()">Start Stream</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
        <button id="fullscreenBtn" onclick="toggleFullScreen()" disabled>Fullscreen</button>
        <button id="rotateBtn" onclick="rotate()" disabled>Rotate</button>
        <button id="snapshotBtn" onclick="takeSnapshot()" disabled>Snapshot</button>
    </div>
    
    <div id="status" class="status disconnected">Disconnected</div>
    
    <video id="video" autoplay playsinline muted></video>
    
    <div id="stats" class="stats">
        <div>Connection State: <span id="connectionState">-</span></div>
        <div>ICE Connection State: <span id="iceConnectionState">-</span></div>
        <div>Bytes Received: <span id="bytesReceived">-</span></div>
        <div>Packets Received: <span id="packetsReceived">-</span></div>
        <div>Packets Lost: <span id="packetsLost">-</span></div>
        <div>Frame Rate: <span id="frameRate">-</span></div>
        <div>Resolution: <span id="resolutionInfo">-</span></div>
        <div>Latency: <span id="latency">-</span> ms</div>
    </div>
    
    <script>
        let pc = null;
        let reconnectTimer = null;
        let lastFrameTime = 0;
        let latencyMeasurements = [];

        // Update quality value display
        document.getElementById('quality').addEventListener('input', function() {
            document.getElementById('qualityValue').textContent = this.value;
        });

        // Update advanced settings displays
        document.getElementById('sharpness').addEventListener('input', function() {
            document.getElementById('sharpnessValue').textContent = (this.value / 100).toFixed(1);
        });

        document.getElementById('contrast').addEventListener('input', function() {
            document.getElementById('contrastValue').textContent = (this.value / 100).toFixed(1);
        });

        document.getElementById('saturation').addEventListener('input', function() {
            document.getElementById('saturationValue').textContent = (this.value / 100).toFixed(1);
        });

        document.getElementById('brightness').addEventListener('input', function() {
            const value = (this.value / 100) - 1;
            document.getElementById('brightnessValue').textContent = value.toFixed(1);
        });

        // Set ultra-low latency as default
        document.getElementById('latencyMode').value = 'ultra';
        document.getElementById('resolution').value = '320,240';
        document.getElementById('fps').value = '60';
        document.getElementById('quality').value = '75';
        document.getElementById('qualityValue').textContent = '75';

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
                
                // Update resolution info
                const resolutionSelect = document.getElementById('resolution');
                const resolution = resolutionSelect.value;
                document.getElementById('resolutionInfo').textContent = resolution;
            });
        }

        function toggleAdvancedSettings() {
            const settings = document.getElementById('advancedSettings');
            settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
        }

        function resetAdvancedSettings() {
            document.getElementById('sharpness').value = 100;
            document.getElementById('contrast').value = 100;
            document.getElementById('saturation').value = 100;
            document.getElementById('brightness').value = 100;
            
            document.getElementById('sharpnessValue').textContent = '1.0';
            document.getElementById('contrastValue').textContent = '1.0';
            document.getElementById('saturationValue').textContent = '1.0';
            document.getElementById('brightnessValue').textContent = '0.0';
        }

        async function start() {
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const latencyModeSelect = document.getElementById('latencyMode');
            const resolutionSelect = document.getElementById('resolution');
            const fpsSelect = document.getElementById('fps');
            
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            
            startBtn.disabled = true;
            latencyModeSelect.disabled = true;
            resolutionSelect.disabled = true;
            fpsSelect.disabled = true;
            updateStatus('Connecting...', 'connecting');
            
            try {
                pc = new RTCPeerConnection(configuration);
                
                pc.onconnectionstatechange = () => {
                    console.log('Connection state:', pc.connectionState);
                    if (pc.connectionState === 'connected') {
                        updateStatus('Connected - Ultra-Low Latency', 'connected');
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
                    
                    // Add frame timing for latency measurement
                    video.addEventListener('timeupdate', () => {
                        if (lastFrameTime) {
                            const latency = (Date.now() - lastFrameTime);
                            latencyMeasurements.push(latency);
                            if (latencyMeasurements.length > 10) {
                                latencyMeasurements.shift();
                            }
                            const avgLatency = latencyMeasurements.reduce((a, b) => a + b, 0) / latencyMeasurements.length;
                            document.getElementById('latency').textContent = avgLatency.toFixed(0);
                        }
                        lastFrameTime = Date.now();
                    });
                };
                
                // Get settings from UI
                const latencyMode = latencyModeSelect.value;
                const resolution = resolutionSelect.value.split(',');
                const width = parseInt(resolution[0], 10);
                const height = parseInt(resolution[1], 10);
                const fps = parseInt(fpsSelect.value, 10);
                const quality = parseInt(document.getElementById('quality').value);
                const sharpness = parseFloat(document.getElementById('sharpness').value) / 100;
                const contrast = parseFloat(document.getElementById('contrast').value) / 100;
                const saturation = parseFloat(document.getElementById('saturation').value) / 100;
                const brightness = (parseFloat(document.getElementById('brightness').value) / 100) - 1;

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
                        quality: quality,
                        sharpness: sharpness,
                        contrast: contrast,
                        saturation: saturation,
                        brightness: brightness,
                        latencyMode: latencyMode
                    }),
                });
                
                const answer = await response.json();
                await pc.setRemoteDescription(new RTCSessionDescription(answer));
                
                stopBtn.disabled = false;
                document.getElementById('fullscreenBtn').disabled = false;
                document.getElementById('rotateBtn').disabled = false;
                document.getElementById('snapshotBtn').disabled = false;
                
            } catch (error) {
                console.error('Error starting stream:', error);
                updateStatus('Connection failed', 'disconnected');
                startBtn.disabled = false;
                latencyModeSelect.disabled = false;
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
            const latencyModeSelect = document.getElementById('latencyMode');
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
            document.getElementById('snapshotBtn').disabled = true;
            latencyModeSelect.disabled = false;
            resolutionSelect.disabled = false;
            fpsSelect.disabled = false;
            
            // Reset latency measurements
            latencyMeasurements = [];
            lastFrameTime = 0;
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

        function takeSnapshot() {
            const video = document.getElementById('video');
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Create download link
            const link = document.createElement('a');
            link.download = 'snapshot-' + new Date().toISOString().slice(0, 19).replace(/:/g, '-') + '.png';
            link.href = canvas.toDataURL();
            link.click();
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
    """Main function to start the ultra-low latency WebRTC server."""
    logger.info("Starting Ultra-Low Latency Pi Camera WebRTC Server")
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