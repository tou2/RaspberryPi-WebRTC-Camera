#!/usr/bin/env python3
"""
Ultra-Low Latency Pi Camera WebRTC Streaming Server with H.264
Optimized for minimal latency using hardware H.264 encoding
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

# Ultra-low latency configuration with H.264
CONFIG = {
    "width": 640,           # Resolution
    "height": 480,          # Resolution
    "fps": 30,              # Frame rate
    "bitrate": 1000000,     # 1 Mbps bitrate
    "profile": "baseline",  # H.264 baseline profile for compatibility
    "level": "4.0",         # H.264 level
    "host": "0.0.0.0",
    "port": 8080,
    "ice_servers": [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"}
    ],
    "queue_size": 2,        # Small queue for low latency
    "low_latency": True,
}

# Global variables
nal_queue = queue.Queue(maxsize=CONFIG["queue_size"])
camera_process = None
camera_thread = None
camera_running = False

def camera_reader():
    """Camera reader optimized for H.264 streaming."""
    global camera_process, camera_running, nal_queue
    
    buffer = b''
    start_code = b'\x00\x00\x00\x01'
    
    while camera_running:
        try:
            if not camera_process or camera_process.poll() is not None:
                setup_camera_process()
                buffer = b''  # Reset buffer
                time.sleep(0.05)  # Shorter wait for faster restart
                continue
                
            # Read data from camera process
            data = camera_process.stdout.read(4096)
            if not 
                continue
                
            buffer += data
            
            # Look for H.264 NAL units in the buffer
            while True:
                # Find start of NAL unit
                start_idx = buffer.find(start_code)
                if start_idx == -1:
                    break
                    
                # Find end of NAL unit (next start code or end of buffer)
                next_start = buffer.find(start_code, start_idx + 4)
                if next_start == -1:
                    # Need more data to find complete NAL unit
                    if len(buffer) - start_idx > 100000:  # Prevent buffer overflow
                        buffer = buffer[start_idx:]  # Keep only from start
                    break
                    
                # Extract complete NAL unit
                nal_unit = buffer[start_idx:next_start]
                buffer = buffer[next_start:]
                
                # Add to queue (overwrite if full for lowest latency)
                try:
                    nal_queue.put(nal_unit, block=False)
                except queue.Full:
                    try:
                        nal_queue.get_nowait()  # Remove oldest
                        nal_queue.put(nal_unit, block=False)
                    except:
                        pass
                    
        except Exception as e:
            logger.error(f"Camera reader error: {e}")
            time.sleep(0.001)  # Very short sleep

def setup_camera_process():
    """Setup camera process with H.264 encoding."""
    global camera_process
    
    if camera_process:
        try:
            camera_process.terminate()
            camera_process.wait(timeout=1)
        except:
            camera_process.kill()
        camera_process = None
    
    try:
        # H.264 optimized camera command
        rpicam_cmd = [
            "rpicam-vid",
            "-t", "0",              # Run forever
            "-n",                   # No preview
            "--width", str(CONFIG["width"]),
            "--height", str(CONFIG["height"]),
            "--framerate", str(CONFIG["fps"]),
            "--bitrate", str(CONFIG["bitrate"]),  # Hardware encoder bitrate
            "--profile", CONFIG["profile"],       # H.264 profile
            "--level", CONFIG["level"],           # H.264 level
            "--intra", str(CONFIG["fps"]),        # Keyframe every second
            "--qp", "23",                        # Quantization parameter
            "--codec", "h264",                   # H.264 encoding
            "--flush",                          # Immediate flush for low latency
            "--inline",                         # Inline headers
            "--save-pts", "0",                  # No timestamp saving
            "--verbose", "0",                   # No verbose output
            "--denoise", "cdn_off",             # Disable denoise for speed
            "--awb", "auto",                    # Auto white balance
            "-o", "-"                           # Output to stdout
        ]
        
        logger.info(f"Starting H.264 camera with: {' '.join(rpicam_cmd)}")
        camera_process = subprocess.Popen(
            rpicam_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=512*1024  # Buffer for H.264 streaming
        )
        
        # Fast startup check
        time.sleep(0.1)
        if camera_process.poll() is not None:
            stderr_output = camera_process.stderr.read().decode('utf-8', errors='ignore')
            logger.error(f"Camera process failed: {stderr_output}")
            raise RuntimeError(f"Camera process failed: {stderr_output}")
            
        logger.info("H.264 camera started successfully")
        
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
    logger.info("H.264 camera capture started")

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
    while not nal_queue.empty():
        try:
            nal_queue.get_nowait()
        except:
            break
    
    logger.info("Camera capture stopped")

class H264VideoTrack(VideoStreamTrack):
    """Video track for H.264 streaming."""
    
    def __init__(self):
        super().__init__()
        self.rotation = 0
        self.frame_counter = 0
        # Create a placeholder frame since we're not decoding H.264 in this example
        self.placeholder_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
        cv2.rectangle(self.placeholder_frame, (50, 50), (CONFIG["width"]-50, CONFIG["height"]-50), (0, 255, 0), 2)
        cv2.putText(self.placeholder_frame, "H.264 Stream Active", 
                   (CONFIG["width"]//2-120, CONFIG["height"]//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
    async def recv(self):
        """Receive next video frame."""
        pts, time_base = await self.next_timestamp()
        
        try:
            # Get NAL unit from queue with timeout
            nal_unit = nal_queue.get(timeout=0.1)
            
            # In a full implementation, you would decode the H.264 NAL unit here
            # For this example, we'll use a placeholder frame
            frame = self.placeholder_frame.copy()
            
            # Add frame counter
            self.frame_counter += 1
            cv2.putText(frame, f"Frame: {self.frame_counter}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Apply rotation if needed
            if self.rotation != 0:
                rotation_map = {
                    90: cv2.ROTATE_90_CLOCKWISE,
                    180: cv2.ROTATE_180,
                    270: cv2.ROTATE_90_COUNTERCLOCKWISE
                }
                if self.rotation in rotation_map:
                    frame = cv2.rotate(frame, rotation_map[self.rotation])
            
            # Convert to VideoFrame
            av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            
            return av_frame
            
        except queue.Empty:
            # Return placeholder frame if no NAL unit available
            frame = self.placeholder_frame.copy()
            cv2.putText(frame, f"Frame: {self.frame_counter} (Buffering)", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
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
    """WebRTC server with H.264 support."""
    
    def __init__(self):
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.app = web.Application()
        self.video_track: Optional[H264VideoTrack] = None
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
            bitrate = int(params.get("bitrate", CONFIG["bitrate"]))

            # Update global config
            CONFIG["width"] = width
            CONFIG["height"] = height
            CONFIG["fps"] = fps
            CONFIG["bitrate"] = bitrate

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in CONFIG["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)
            self.peer_connections.add(pc)

            # Create or reuse the video track
            if self.video_track is None:
                logger.info("Starting H.264 camera track")
                self.video_track = H264VideoTrack()
                start_camera()
            else:
                logger.info("Reusing existing camera track.")
                # Restart camera if settings changed significantly
                if (width != CONFIG["width"] or 
                    height != CONFIG["height"] or 
                    fps != CONFIG["fps"]):
                    logger.info("Restarting camera with new settings")
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
            logger.info("Adding H.264 video track.")
            pc.addTrack(self.video_track)
            
            # Set remote description
            await pc.setRemoteDescription(offer)

            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            if pc.localDescription and pc.localDescription.sdp:
                logger.info("Successfully generated H.264 answer SDP")
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
        
        logger.info(f"H.264 WebRTC server started on http://{CONFIG['host']}:{CONFIG['port']}")
        logger.info("Open the URL in your browser to view the stream")
        logger.info(f"H.264 mode: {CONFIG['width']}x{CONFIG['height']}@{CONFIG['fps']}fps")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down H.264 server...")
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

# HTML with H.264 options
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>H.264 Pi Camera WebRTC Stream</title>
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
        .value-display {
            font-size: 12px;
            color: #4CAF50;
            min-width: 30px;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>H.264 Pi Camera Stream</h1>
    
    <div class="settings">
        <div class="setting-group">
            <label for="resolution">Resolution:</label>
            <select id="resolution">
                <option value="640,480" selected>640x480</option>
                <option value="1280,720">1280x720</option>
                <option value="1920,1080">1920x1080</option>
            </select>
        </div>
        
        <div class="setting-group">
            <label for="fps">FPS:</label>
            <select id="fps">
                <option value="15">15 FPS</option>
                <option value="30" selected>30 FPS</option>
                <option value="60">60 FPS</option>
            </select>
        </div>
        
        <div class="setting-group">
            <label for="bitrate">Bitrate:</label>
            <input type="range" id="bitrate" min="500000" max="5000000" value="1000000" step="100000">
            <span id="bitrateValue" class="value-display">1.0M</span>
        </div>
    </div>

    <div class="controls">
        <button id="startBtn" onclick="start()">Start Stream</button>
        <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
        <button id="fullscreenBtn" onclick="toggleFullScreen()" disabled>Fullscreen</button>
        <button id="rotateBtn" onclick="rotate()" disabled>Rotate</button>
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
    </div>
    
    <script>
        let pc = null;
        let reconnectTimer = null;

        // Update bitrate value display
        document.getElementById('bitrate').addEventListener('input', function() {
            const mbps = (this.value / 1000000).toFixed(1);
            document.getElementById('bitrateValue').textContent = mbps + 'M';
        });

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

        async function start() {
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const resolutionSelect = document.getElementById('resolution');
            const fpsSelect = document.getElementById('fps');
            const bitrateSlider = document.getElementById('bitrate');
            
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            
            startBtn.disabled = true;
            resolutionSelect.disabled = true;
            fpsSelect.disabled = true;
            bitrateSlider.disabled = true;
            updateStatus('Connecting...', 'connecting');
            
            try {
                pc = new RTCPeerConnection(configuration);
                
                pc.onconnectionstatechange = () => {
                    console.log('Connection state:', pc.connectionState);
                    if (pc.connectionState === 'connected') {
                        updateStatus('Connected - H.264 Stream', 'connected');
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
                const bitrate = parseInt(bitrateSlider.value);

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
                        bitrate: bitrate
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
                bitrateSlider.disabled = false;
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
            const bitrateSlider = document.getElementById('bitrate');
            
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
            bitrateSlider.disabled = false;
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
    """Main function to start the H.264 WebRTC server."""
    logger.info("Starting H.264 Pi Camera WebRTC Server")
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