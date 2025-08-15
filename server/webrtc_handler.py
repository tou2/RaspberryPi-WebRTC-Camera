import logging
import asyncio
from typing import Set, Optional
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCConfiguration,
    RTCIceServer,
)
from av import VideoFrame
import numpy as np
import cv2
import queue

from .camera import Camera
from .utils import get_battery_status

logger = logging.getLogger(__name__)

class CameraVideoTrack(VideoStreamTrack):
    """Video track optimized for ultra-low latency."""
    
    def __init__(self, frame_queue, config):
        super().__init__()
        self.frame_queue = frame_queue
        self.config = config
        self.rotation = 0
        
    async def recv(self):
        """Receive next video frame with ultra-low latency."""
        pts, time_base = await self.next_timestamp()
        
        try:
            # Get frame from queue with very short timeout
            frame = self.frame_queue.get(timeout=0.05)  # 50ms timeout
            
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
            black_frame = np.zeros((self.config["height"], self.config["width"], 3), dtype=np.uint8)
            av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            return av_frame
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            # Return black frame on error
            black_frame = np.zeros((self.config["height"], self.config["width"], 3), dtype=np.uint8)
            av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
            av_frame.pts = pts
            av_frame.time_base = time_base
            return av_frame
    
    async def rotate(self):
        """Rotate camera by 90 degrees."""
        self.rotation = (self.rotation + 90) % 360
        logger.info(f"Camera rotated to {self.rotation} degrees")

class WebRTCHandler:
    def __init__(self, camera, config):
        self.camera = camera
        self.config = config
        self.peer_connections: Set[RTCPeerConnection] = set()
        self.video_track: Optional[CameraVideoTrack] = None
        self.get_battery_status = get_battery_status

    async def offer(self, request):
        """Handle WebRTC offer from client with ultra-low latency."""
        try:
            params = await request.json()
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Get desired settings from client
            width = int(params.get("width", self.config["width"]))
            height = int(params.get("height", self.config["height"]))
            fps = int(params.get("fps", self.config["fps"]))
            quality = int(params.get("quality", self.config["quality"]))
            sharpness = float(params.get("sharpness", self.config["sharpness"]))
            contrast = float(params.get("contrast", self.config["contrast"]))
            saturation = float(params.get("saturation", self.config["saturation"]))
            brightness = float(params.get("brightness", self.config["brightness"]))
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
            self.config["width"] = width
            self.config["height"] = height
            self.config["fps"] = fps
            self.config["quality"] = quality
            self.config["sharpness"] = sharpness
            self.config["contrast"] = contrast
            self.config["saturation"] = saturation
            self.config["brightness"] = brightness

            # Create RTCConfiguration
            config = RTCConfiguration(
                iceServers=[RTCIceServer(**server) for server in self.config["ice_servers"]]
            )

            # Create new peer connection
            pc = RTCPeerConnection(configuration=config)
            self.peer_connections.add(pc)

            # Create or reuse the video track
            if self.video_track is None:
                logger.info("Starting ultra-low latency camera track")
                self.video_track = CameraVideoTrack(self.camera.frame_queue, self.config)
                self.camera.start_camera()
            else:
                logger.info("Reusing existing camera track.")
                # Restart camera if resolution/FPS changed significantly
                if (width != self.config["width"] or 
                    height != self.config["height"] or 
                    fps != self.config["fps"]):
                    logger.info("Restarting camera with new settings for ultra-low latency")
                    self.camera.stop_camera()
                    self.camera.start_camera()

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"Connection state: {pc.connectionState}")
                if pc.connectionState in ("failed", "closed", "disconnected"):
                    await pc.close()
                    self.peer_connections.discard(pc)
                    if not self.peer_connections and self.video_track:
                        logger.info("Last peer disconnected, stopping camera.")
                        self.camera.stop_camera()
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

    async def cleanup(self):
        # Clean up connections
        for pc in self.peer_connections.copy():
            await pc.close()
        self.peer_connections.clear()
        
        # Stop the camera track
        if self.video_track:
            logger.info("Server shutting down, stopping camera.")
            self.camera.stop_camera()
