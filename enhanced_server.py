#!/usr/bin/env python3
"""
Enhanced WebRTC video streaming server with configuration support.
Optimized specifically for Raspberry Pi Zero with ultra-low latency.
"""

import asyncio
import configparser
import json
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Set, Optional

import cv2
from aiohttp import web, web_runner
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame
import numpy as np
import subprocess

# Try to import uvloop for better performance on Linux
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Using uvloop for enhanced performance")
except ImportError:
    print("uvloop not available, using default event loop")

class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path="config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file with defaults."""
        # Set defaults
        self.config.read_dict({
            'camera': {
                'device_index': '0',
                'width': '640',
                'height': '480',
                'fps': '20',
                'buffer_size': '1'
            },
            'encoding': {
                'bitrate': '500000',
                'h264_profile': 'baseline',
                'keyframe_interval': '2'
            },
            'network': {
                'host': '0.0.0.0',
                'port': '8080',
                'max_connections': '3'
            },
            'performance': {
                'use_gpu_acceleration': 'true',
                'video_threads': '2',
                'low_latency_mode': 'true',
                'frame_drop_strategy': 'smart'
            },
            'logging': {
                'level': 'DEBUG',
                'log_performance': 'true',
                'log_file': ''
            },
            'advanced': {
                'raspberry_pi_optimizations': 'true',
                'use_mmap': 'true'
            }
        })
        
        # Load user config if exists
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
            print(f"Loaded configuration from {self.config_path}")
        else:
            print("Using default configuration")
    
    def get_camera_config(self):
        """Get camera configuration."""
        return {
            'device_index': self.config.getint('camera', 'device_index'),
            'width': self.config.getint('camera', 'width'),
            'height': self.config.getint('camera', 'height'),
            'fps': self.config.getint('camera', 'fps'),
            'buffer_size': self.config.getint('camera', 'buffer_size')
        }
    
    def get_encoding_config(self):
        """Get encoding configuration."""
        return {
            'bitrate': self.config.getint('encoding', 'bitrate'),
            'h264_profile': self.config.get('encoding', 'h264_profile'),
            'keyframe_interval': self.config.getint('encoding', 'keyframe_interval')
        }
    
    def get_network_config(self):
        """Get network configuration."""
        return {
            'host': self.config.get('network', 'host'),
            'port': self.config.getint('network', 'port'),
            'max_connections': self.config.getint('network', 'max_connections')
        }
    
    def get_performance_config(self):
        """Get performance configuration."""
        return {
            'use_gpu_acceleration': self.config.getboolean('performance', 'use_gpu_acceleration'),
            'video_threads': self.config.getint('performance', 'video_threads'),
            'low_latency_mode': self.config.getboolean('performance', 'low_latency_mode'),
            'frame_drop_strategy': self.config.get('performance', 'frame_drop_strategy')
        }

class PerformanceMonitor:
    """Monitors and logs performance metrics."""
    
    def __init__(self):
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.dropped_frames = 0
        self.total_frames = 0
        self.cpu_usage = 0
        self.memory_usage = 0
        
        # Try to import psutil for system monitoring
        try:
            import psutil
            self.psutil = psutil
            self.monitor_system = True
        except ImportError:
            self.psutil = None
            self.monitor_system = False
    
    def update_frame_stats(self, dropped=False):
        """Update frame statistics."""
        self.total_frames += 1
        if dropped:
            self.dropped_frames += 1
        else:
            self.frame_count += 1
    
    def get_fps(self):
        """Calculate current FPS."""
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        if elapsed >= 1.0:
            fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_frame_time = current_time
            return fps
        return None
    
    def get_system_stats(self):
        """Get system performance statistics."""
        if not self.monitor_system:
            return {}
        
        try:
            return {
                'cpu_percent': self.psutil.cpu_percent(),
                'memory_percent': self.psutil.virtual_memory().percent,
                'temperature': self.get_cpu_temperature()
            }
        except:
            return {}
    
    def get_cpu_temperature(self):
        """Get CPU temperature on Raspberry Pi."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return temp
        except:
            return None

class OptimizedCameraTrack(VideoStreamTrack):
    """
    Video track for Raspberry Pi Camera v3 using rpicam-hello only.
    """
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self.camera_config = self.config.get_camera_config()
        self.performance_config = self.config.get_performance_config()
        self.monitor = PerformanceMonitor()
        self.last_capture_time = time.time()
        self.adaptive_quality = True
        self.current_quality = 1.0
        
        self._setup_camera()
        self._setup_optimizations()
        
        # Start performance monitoring thread
        if self.performance_config['low_latency_mode']:
            self.monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
            self.monitor_thread.start()
    
    def _setup_camera(self):
        """Initialize v3 camera using rpicam-vid for video streaming."""
        try:
            self.rpicam_cmd = [
                "rpicam-vid",
                "--timeout", "0",
                "--width", str(self.camera_config['width']),
                "--height", str(self.camera_config['height']),
                "--framerate", str(self.camera_config['fps']),
                "--codec", "mjpeg",
                "--nopreview",
                "--output", "-"
            ]
            self.rpicam_proc = subprocess.Popen(
                self.rpicam_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered for real-time streaming
            )
            logging.info(f"Using Raspberry Pi Camera v3 via rpicam-vid: {' '.join(self.rpicam_cmd)} (PID: {self.rpicam_proc.pid})")
            # Log initial stderr output (first 256 bytes)
            try:
                import time
                time.sleep(0.5)  # Give process a moment to start
                if self.rpicam_proc.stderr:
                    err_start = self.rpicam_proc.stderr.read(256)
                    if err_start:
                        logging.info(f"rpicam-vid initial stderr: {err_start.decode(errors='ignore').strip()}")
            except Exception as e:
                logging.warning(f"Could not read initial rpicam-vid stderr: {e}")
        except Exception as e:
            logging.error(f"Failed to initialize v3 camera: {e}")
            raise

    def _setup_optimizations(self):
        """Setup performance optimizations."""
        logging.info("Performance optimizations enabled")
    
    def _monitor_performance(self):
        """Monitor performance and adjust quality adaptively."""
        while True:
            try:
                time.sleep(1)  # Check every second
                
                fps = self.monitor.get_fps()
                if fps is not None:
                    target_fps = self.camera_config['fps']
                    
                    # Adaptive quality based on performance
                    if fps < target_fps * 0.8:  # If FPS drops below 80% of target
                        if self.current_quality > 0.5:
                            self.current_quality *= 0.9  # Reduce quality
                            logging.info(f"Reducing quality to {self.current_quality:.2f} (FPS: {fps:.1f})")
                    elif fps > target_fps * 0.95:  # If FPS is good
                        if self.current_quality < 1.0:
                            self.current_quality = min(1.0, self.current_quality * 1.05)
                    
                    # Log performance stats
                    if self.config.config.getboolean('logging', 'log_performance'):
                        stats = self.monitor.get_system_stats()
                        temp_str = f", Temp: {stats.get('temperature', 'N/A')}°C" if stats.get('temperature') else ""
                        logging.info(f"FPS: {fps:.1f}, Quality: {self.current_quality:.2f}, "
                                   f"CPU: {stats.get('cpu_percent', 'N/A')}%, "
                                   f"RAM: {stats.get('memory_percent', 'N/A')}%{temp_str}")
                
            except Exception as e:
                logging.error(f"Performance monitoring error: {e}")
                time.sleep(5)
    
    async def recv(self):
        """Receive the next video frame from v3 camera."""
        pts, time_base = await self.next_timestamp()
        
        try:
            # Check if rpicam process is still running
            if self.rpicam_proc.poll() is not None:
                logging.error(f"rpicam-vid process has terminated with code: {self.rpicam_proc.poll()}")
                raise RuntimeError("Camera process terminated")
            
            # Use asyncio to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            
            # Read data in a non-blocking way
            frame_data = await loop.run_in_executor(None, self._read_mjpeg_frame)
            
            if frame_data and len(frame_data) > 100:
                # Decode the JPEG frame
                arr = np.frombuffer(frame_data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Convert BGR to RGB for WebRTC
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Update performance stats
                    self.monitor.update_frame_stats()
                    
                    # Create VideoFrame with proper timing
                    av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
                    av_frame.pts = pts
                    av_frame.time_base = time_base
                    
                    logging.debug(f"Successfully decoded frame: {frame.shape}")
                    return av_frame
                else:
                    logging.warning(f"Failed to decode JPEG frame of {len(frame_data)} bytes")
            else:
                logging.warning("No valid frame data received from camera")
                        
        except Exception as e:
            logging.error(f"Error reading frame from v3 camera: {e}", exc_info=True)
        
        # Return black frame if camera read failed
        logging.warning("Returning black frame due to camera read failure")
        frame = np.zeros((self.camera_config['height'], self.camera_config['width'], 3), dtype=np.uint8)
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        return av_frame

    def _read_mjpeg_frame(self):
        """Read a single MJPEG frame from rpicam-vid stdout (blocking operation)."""
        frame_data = b''
        found_start = False
        max_frame_size = 1024 * 1024  # 1MB max frame size
        read_timeout = 0.1  # 100ms timeout for each read
        
        import select
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < 1.0:  # 1 second total timeout
            # Check if data is available to read
            ready, _, _ = select.select([self.rpicam_proc.stdout], [], [], read_timeout)
            
            if not ready:
                continue  # No data available, try again
                
            try:
                # Read small chunks to avoid blocking
                chunk = self.rpicam_proc.stdout.read(4096)
                if not chunk:
                    logging.warning("No data chunk from rpicam-vid")
                    break
                
                frame_data += chunk
                
                # Look for JPEG start marker (SOI: 0xFFD8)
                if not found_start and b'\xff\xd8' in frame_data:
                    start_pos = frame_data.find(b'\xff\xd8')
                    frame_data = frame_data[start_pos:]  # Keep only from JPEG start
                    found_start = True
                    logging.debug("Found JPEG start marker")
                
                # Look for JPEG end marker (EOI: 0xFFD9)
                if found_start and b'\xff\xd9' in frame_data:
                    end_pos = frame_data.find(b'\xff\xd9') + 2
                    complete_frame = frame_data[:end_pos]
                    logging.debug(f"Found complete JPEG frame: {len(complete_frame)} bytes")
                    return complete_frame
                
                # Prevent memory overflow
                if len(frame_data) > max_frame_size:
                    logging.warning("Frame data too large, resetting buffer")
                    frame_data = b''
                    found_start = False
                    
            except Exception as e:
                logging.error(f"Error reading chunk from rpicam-vid: {e}")
                break
        
        logging.warning("Timeout reading MJPEG frame")
        return None

    def stop(self):
        """Clean up v3 camera resources."""
        if hasattr(self, 'rpicam_proc') and self.rpicam_proc:
            self.rpicam_proc.terminate()
            self.rpicam_proc.wait()
            logging.info("rpicam-vid process terminated")

class WebRTCServer:
    """Enhanced WebRTC server with configuration support."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.network_config = self.config.get_network_config()
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.connection_count = 0
        self.app = web.Application()
        self._setup_routes()
        self._setup_logging()
        self._setup_signal_handlers()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = {
            'level': getattr(logging, self.config.config.get('logging', 'level')),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
        
        log_file = self.config.config.get('logging', 'log_file')
        if log_file:
            log_config['filename'] = log_file
        
        logging.basicConfig(**log_config)
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self._shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/client.js", self.client_js)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_get("/stats", self.stats)
    
    async def index(self, request):
        """Serve enhanced HTML client."""
        # Read the HTML template from file or use embedded version
        html_path = Path(__file__).parent / "client.html"
        if html_path.exists():
            with open(html_path, 'r') as f:
                html_content = f.read()
        else:
            # Embedded HTML (same as before but with stats endpoint)
            html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Zero WebRTC Stream - Enhanced</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            max-width: 1200px;
            width: 100%;
        }
        h1 {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .video-container {
            position: relative;
            margin: 20px 0;
            border: 3px solid #4CAF50;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        video {
            width: 100%;
            height: auto;
            display: block;
            background-color: #000;
        }
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            min-width: 120px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
        }
        button:disabled {
            background: #666;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .status {
            text-align: center;
            margin: 15px 0;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 18px;
        }
        .status.connected {
            background: linear-gradient(45deg, #2d5a2d, #4CAF50);
            color: white;
        }
        .status.connecting {
            background: linear-gradient(45deg, #5a5a2d, #FFC107);
            color: white;
        }
        .status.disconnected {
            background: linear-gradient(45deg, #5a2d2d, #f44336);
            color: white;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stats-panel {
            background: rgba(42, 42, 42, 0.8);
            border: 1px solid #4CAF50;
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        .stats-title {
            color: #4CAF50;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            font-family: 'Courier New', monospace;
        }
        .stat-label {
            color: #ccc;
        }
        .stat-value {
            color: #4CAF50;
            font-weight: bold;
        }
        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
                align-items: center;
            }
            button {
                width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pi Zero WebRTC Stream</h1>
        
        <div class="controls">
            <button id="startBtn" onclick="start()">Start Stream</button>
            <button id="stopBtn" onclick="stop()" disabled>Stop Stream</button>
            <button id="fullscreenBtn" onclick="toggleFullscreen()" disabled>Fullscreen</button>
        </div>
        
        <div id="status" class="status disconnected">Disconnected</div>
        
        <div class="video-container">
            <video id="video" autoplay playsinline muted></video>
        </div>
        
        <div class="stats-grid">
            <div class="stats-panel">
                <div class="stats-title">Connection Stats</div>
                <div class="stat-item">
                    <span class="stat-label">State:</span>
                    <span class="stat-value" id="connectionState">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">ICE State:</span>
                    <span class="stat-value" id="iceConnectionState">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Uptime:</span>
                    <span class="stat-value" id="uptime">-</span>
                </div>
            </div>
            
            <div class="stats-panel">
                <div class="stats-title">Video Stats</div>
                <div class="stat-item">
                    <span class="stat-label">Frame Rate:</span>
                    <span class="stat-value" id="frameRate">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Resolution:</span>
                    <span class="stat-value" id="resolution">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Bitrate:</span>
                    <span class="stat-value" id="bitrate">-</span>
                </div>
            </div>
            
            <div class="stats-panel">
                <div class="stats-title">Network Stats</div>
                <div class="stat-item">
                    <span class="stat-label">Bytes Received:</span>
                    <span class="stat-value" id="bytesReceived">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Packets Lost:</span>
                    <span class="stat-value" id="packetsLost">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Jitter:</span>
                    <span class="stat-value" id="jitter">-</span>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/client.js"></script>
</body>
</html>
            """
        
        return web.Response(text=html_content, content_type="text/html")
    
    async def client_js(self, request):
        """Serve enhanced JavaScript client."""
        js_content = """
let pc = null;
let startTime = null;

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

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateStats() {
    if (!pc) return;
    
    // Update uptime
    if (startTime) {
        const uptime = (Date.now() - startTime) / 1000;
        document.getElementById('uptime').textContent = formatTime(uptime);
    }
    
    pc.getStats().then(stats => {
        stats.forEach(report => {
            if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
                document.getElementById('bytesReceived').textContent = formatBytes(report.bytesReceived || 0);
                document.getElementById('packetsLost').textContent = report.packetsLost || '0';
                
                if (report.framesPerSecond) {
                    document.getElementById('frameRate').textContent = report.framesPerSecond.toFixed(1) + ' fps';
                }
                
                if (report.jitter !== undefined) {
                    document.getElementById('jitter').textContent = (report.jitter * 1000).toFixed(1) + ' ms';
                }
                
                // Calculate bitrate
                if (report.bytesReceived && report.timestamp) {
                    const bitrate = (report.bytesReceived * 8) / (report.timestamp / 1000);
                    document.getElementById('bitrate').textContent = (bitrate / 1000).toFixed(1) + ' kbps';
                }
            }
        });
        
        document.getElementById('connectionState').textContent = pc.connectionState;
        document.getElementById('iceConnectionState').textContent = pc.iceConnectionState;
    });
}

function toggleFullscreen() {
    const video = document.getElementById('video');
    if (!document.fullscreenElement) {
        video.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

async function start() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    startBtn.disabled = true;
    updateStatus('Connecting...', 'connecting');
    try {
        pc = new RTCPeerConnection(configuration);
        startTime = Date.now();
        
        pc.onconnectionstatechange = () => {
            console.log('Connection state:', pc.connectionState);
            if (pc.connectionState === 'connected') {
                updateStatus('Connected', 'connected');
                setInterval(updateStats, 1000);
                fullscreenBtn.disabled = false;
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
            
            // Update resolution when video loads
            video.onloadedmetadata = () => {
                document.getElementById('resolution').textContent = `${video.videoWidth}x${video.videoHeight}`;
            };
        };
        
        // Create offer
        const offer = await pc.createOffer();
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
        if (answer.error) {
            throw new Error(answer.error);
        }
        if (!answer.sdp || !answer.type) {
            throw new Error('Invalid answer from server');
        }
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
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    
    if (pc) {
        pc.close();
        pc = null;
    }
    
    startTime = null;
    
    const video = document.getElementById('video');
    video.srcObject = null;
    
    updateStatus('Disconnected', 'disconnected');
    
    // Reset stats
    ['connectionState', 'iceConnectionState', 'uptime', 'frameRate', 'resolution', 
     'bitrate', 'bytesReceived', 'packetsLost', 'jitter'].forEach(id => {
        document.getElementById(id).textContent = '-';
    });
    
    startBtn.disabled = false;
    stopBtn.disabled = true;
    fullscreenBtn.disabled = true;
}

// Handle visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden && pc) {
        console.log('Page hidden, maintaining connection');
    } else if (!document.hidden && pc) {
        console.log('Page visible, refreshing stats');
    }
});
        """
        return web.Response(text=js_content, content_type="application/javascript")
    
    async def stats(self, request):
        """Serve server statistics."""
        stats = {
            'connections': len(self.peer_connections),
            'total_connections': self.connection_count,
            'uptime': time.time() - getattr(self, 'start_time', time.time()),
            'config': {
                'camera': self.config.get_camera_config(),
                'network': self.config.get_network_config()
            }
        }
        return web.json_response(stats)
    
    async def offer(self, request):
        """Handle WebRTC offer with connection limiting."""
        try:
            # Check connection limit
            if len(self.peer_connections) >= self.network_config['max_connections']:
                return web.json_response({
                    "error": "Maximum connections reached"
                }, status=429)
            
            params = await request.json()
            logging.info(f"Received offer: type={params.get('type')}, sdp_length={len(params.get('sdp', ''))}")
            
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            
            # Create new peer connection
            config = RTCConfiguration(
                iceServers=[
                    RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                    RTCIceServer(urls=["stun:stun1.l.google.com:19302"])
                ]
            )
            pc = RTCPeerConnection(configuration=config)
            logging.info(f"Created RTCPeerConnection with config: {config}")
            
            self.peer_connections.add(pc)
            self.connection_count += 1
            
            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logging.info(f"Connection state: {pc.connectionState}")
                if pc.connectionState in ["closed", "failed"]:
                    self.peer_connections.discard(pc)
            
            # Set remote description and create answer
            logging.info("Setting remote description...")
            await pc.setRemoteDescription(offer)
            
            # Add optimized video track AFTER setting remote description
            try:
                video_track = OptimizedCameraTrack(self.config)
                // Add track with explicit direction and kind to avoid aiortc SDP direction bug
                transceiver = pc.addTransceiver(video_track, direction="sendonly")
                logging.info(f"Added video track to peer connection with direction: {transceiver.direction}")
                
                // Force MID assignment before creating answer - this is critical for BUNDLE groups
                transceiver._mid = "0"
                logging.info(f"Assigned MID '0' to video transceiver")
                    
            } catch (Exception track_error) {
                logging.error(f"Failed to create/add video track: {track_error}")
                raise
            
            logging.info("Creating answer...")
            answer = await pc.createAnswer()
            logging.info(f"Created answer: type={answer.type}, sdp_length={len(answer.sdp) if answer.sdp else 0}")
            
            // Debug and robustly fix SDP content before setting local description
            if (answer.sdp) {
                sdp_lines = answer.sdp.split('\n')
                logging.debug("Answer SDP preview:")
                for (i, line) in sdp_lines[:10].entries() {
                    logging.debug(f"  {i}: {line}")
                }

                // Find ICE credentials from SDP if present
                ice_ufrag = None
                ice_pwd = None
                for line in sdp_lines {
                    if (line.startswith('a=ice-ufrag:')) {
                        ice_ufrag = line.split(':', 1)[1].strip()
                    }
                    if (line.startswith('a=ice-pwd:')) {
                        ice_pwd = line.split(':', 1)[1].strip()
                    }
                }
                // If not present, generate dummy values
                if (!ice_ufrag) {
                    ice_ufrag = 'dummyufrag'
                }
                if (!ice_pwd) {
                    ice_pwd = 'dummypwd1234567890'
                }

                // Find all mids in media sections
                mids = [line.split(':', 1)[1].strip() for line in sdp_lines if line.startswith('a=mid:')]
                video_section_found = False
                for (idx, line) in sdp_lines.entries() {
                    if (line.startswith('m=video')) {
                        video_section_found = True
                        // Check if a=mid:0, ICE, and DTLS setup are present in the next few lines
                        mid_present = false
                        ice_present = false
                        setup_present = false
                        for (offset in 1..10) {
                            if (idx + offset < len(sdp_lines)) {
                                if (sdp_lines[idx + offset].startswith('a=mid:0')) {
                                    mid_present = true
                                }
                                if (sdp_lines[idx + offset].startswith('a=ice-ufrag:')) {
                                    ice_present = true
                                }
                                if (sdp_lines[idx + offset].startswith('a=setup:')) {
                                    setup_present = true
                                }
                        insert_pos = idx + 1
                        if (!mid_present) {
                            sdp_lines.insert(insert_pos, 'a=mid:0')
                            mids = ['0']
                            logging.info("Inserted missing a=mid:0 after m=video")
                            insert_pos += 1
                        }
                        if (!ice_present) {
                            sdp_lines.insert(insert_pos, f'a=ice-ufrag:{ice_ufrag}')
                            sdp_lines.insert(insert_pos + 1, f'a=ice-pwd:{ice_pwd}')
                            logging.info("Inserted missing ICE credentials after m=video")
                            insert_pos += 2
                        }
                        if (!setup_present) {
                            sdp_lines.insert(insert_pos, 'a=setup:actpass')
                            logging.info("Inserted missing DTLS setup line after m=video")
                        }
                        break
                }
                // If no video section, add one at the end
                if (!video_section_found) {
                    sdp_lines.append('m=video 9 UDP/TLS/RTP/SAVPF 96')
                    sdp_lines.append('c=IN IP4 0.0.0.0')
                    sdp_lines.append('a=rtpmap:96 VP8/90000')
                    sdp_lines.append('a=mid:0')
                    sdp_lines.append(f'a=ice-ufrag:{ice_ufrag}')
                    sdp_lines.append(f'a=ice-pwd:{ice_pwd}')
                    sdp_lines.append('a=setup:actpass')
                    mids = ['0']
                    logging.info("Added missing m=video section with a=mid:0, ICE credentials, and DTLS setup")
                // Patch BUNDLE line and DTLS setup
                fixed_sdp_lines = []
                for line in sdp_lines {
                    if (line.startswith('a=group:BUNDLE')) {
                        // Replace with correct mids
                        line = 'a=group:BUNDLE ' + (' '.join(mids) if mids else '0')
                        logging.info(f"Fixed BUNDLE line: {line}")
                    }
                    if (line.startswith('a=setup:actpass')) {
                        line = 'a=setup:passive'
                        logging.info("Replaced DTLS setup attribute with 'passive' for answer")
                    }
                    fixed_sdp_lines.append(line)
                }
                // Update the answer with fixed SDP
                answer = RTCSessionDescription(sdp='\n'.join(fixed_sdp_lines), type=answer.type)
                logging.info("Applied robust SDP fixes for BUNDLE/MID, media section, ICE credentials, and DTLS setup issues")
            
            // Fix transceiver directions before setting local description
            for transceiver in pc.getTransceivers():
                if transceiver.sender.track and hasattr(transceiver.sender.track, '__class__'):
                    if 'CameraTrack' in transceiver.sender.track.__class__.__name__:
                        // Set both direction attributes to avoid aiortc SDP direction bug
                        transceiver._direction = "sendonly"
                        transceiver._offerDirection = "sendonly"
                        transceiver._currentDirection = "sendonly"
                        logging.info(f"Fixed transceiver directions: direction={transceiver._direction}, offerDirection={getattr(transceiver, '_offerDirection', 'None')}")
            
            logging.info("Setting local description...")
            try {
                await pc.setLocalDescription(answer)
            } catch (ValueError ve) {
                if ("None is not in list" in str(ve)) {
                    logging.error("Encountered aiortc SDP direction bug, attempting workaround...")
                    // Patch the problematic method temporarily
                    import aiortc.rtcpeerconnection as rtc_module
                    original_and_direction = rtc_module.and_direction
                    
                    def patched_and_direction(a, b):
                        if a is None:
                            a = "sendonly"
                        if b is None:
                            b = "sendonly"
                        return original_and_direction(a, b)
                    
                    rtc_module.and_direction = patched_and_direction
                    try {
                        await pc.setLocalDescription(answer)
                        logging.info("Successfully set local description with workaround")
                    } finally {
                        rtc_module.and_direction = original_and_direction
                    }
                } else {
                    raise
                }

            // Ensure localDescription is set before returning
            if (pc.localDescription is None) {
                logging.warning("pc.localDescription is None, waiting 100ms...")
                import asyncio
                await asyncio.sleep(0.1)
            }
            if (pc.localDescription is None) {
                logging.error("pc.localDescription is still None after setLocalDescription. Cannot return answer.")
                return web.json_response({"error": "Internal server error: no SDP answer generated"}, status=500)
            }

            logging.info(f"New connection established. Active connections: {len(self.peer_connections)}")
            logging.info(f"Returning answer: type={pc.localDescription.type}, sdp_length={len(pc.localDescription.sdp) if pc.localDescription.sdp else 0}")

            response_data = {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
            
            // Validate response data before sending
            if (!response_data["sdp"] || !response_data["type"]) {
                logging.error(f"Invalid response data: sdp={bool(response_data['sdp'])}, type={response_data['type']}")
                return web.json_response({"error": "Invalid SDP answer generated"}, status=500)
            }
            
            return web.json_response(response_data)
            
        } catch (Exception e) {
            logging.error(f"Error handling offer: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)
    }
    
    async def _shutdown(self):
        """Graceful shutdown."""
        logging.info("Shutting down server...")
        
        // Close all peer connections
        for pc in self.peer_connections.copy():
            await pc.close()
        
        sys.exit(0)
    
    async def start_server(self):
        """Start the enhanced web server."""
        self.start_time = time.time()
        
        runner = web_runner.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(
            runner, 
            self.network_config['host'], 
            self.network_config['port']
        )
        await site.start()
        
        logging.info(f"Enhanced WebRTC server started on http://{self.network_config['host']}:{self.network_config['port']}")
        logging.info(f"Maximum concurrent connections: {self.network_config['max_connections']}")
        
        try {
            while (true) {
                await asyncio.sleep(1)
            }
        } catch (KeyboardInterrupt) {
            logging.info("Server stopped by user")
        } finally {
            await runner.cleanup()
        }
    }

async def main():
    """Main function."""
    print("Pi Zero Enhanced WebRTC Camera Server")
    print("=====================================")
    
    server = WebRTCServer()
    await server.start_server()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)
