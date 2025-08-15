#!/usr/bin/env python3
"""
Ultra-Low Latency Pi Camera WebRTC Streaming Server
Optimized for minimal latency with enhanced features
"""

import asyncio
import logging
from server.web_server import WebRTCServer
from server.camera import Camera
from server.webrtc_handler import WebRTCHandler

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

async def main():
    camera = Camera(CONFIG)
    webrtc_handler = WebRTCHandler(camera, CONFIG)
    server = WebRTCServer(webrtc_handler)
    await server.start_server(CONFIG["host"], CONFIG["port"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")