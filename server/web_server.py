from aiohttp import web
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

class WebRTCServer:
    """Ultra-low latency WebRTC server."""
    
    def __init__(self, webrtc_handler):
        self.webrtc_handler = webrtc_handler
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get("/", self.index)
        self.app.router.add_post("/offer", self.offer)
        self.app.router.add_post("/rotate", self.rotate_camera)
        self.app.router.add_post("/snapshot", self.snapshot)
        self.app.router.add_get("/battery", self.battery_status)
        self.app.router.add_static('/static', 'static')
        
    async def index(self, request):
        """Serve the HTML client."""
        with open(os.path.join('static', 'index.html'), 'r') as f:
            return web.Response(text=f.read(), content_type="text/html")
    
    async def rotate_camera(self, request):
        """Handle camera rotation request."""
        if self.webrtc_handler.video_track:
            await self.webrtc_handler.video_track.rotate()
            return web.Response(status=200)
        return web.Response(status=400, text="Video track not available")
    
    async def snapshot(self, request):
        """Handle snapshot request."""
        return web.Response(status=200, text="Snapshot functionality available")

    async def battery_status(self, request):
        """Handle battery status request."""
        status = await asyncio.to_thread(self.webrtc_handler.get_battery_status)
        if status:
            return web.json_response(status)
        return web.json_response({"error": "Battery not found or error reading status"}, status=404)

    async def offer(self, request):
        """Handle WebRTC offer from client with ultra-low latency."""
        return await self.webrtc_handler.offer(request)

    async def start_server(self, host, port):
        """Start the ultra-low latency web server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Ultra-Low Latency WebRTC server started on http://{host}:{port}")
        logger.info("Open the URL in your browser to view the stream")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down ultra-low latency server...")
        finally:
            await self.webrtc_handler.cleanup()
            await runner.cleanup()
