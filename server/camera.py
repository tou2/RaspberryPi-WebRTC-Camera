import logging
import subprocess
import time
import threading
import queue
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class Camera:
    def __init__(self, config):
        self.config = config
        self.frame_queue = queue.Queue(maxsize=self.config["queue_size"])
        self.camera_process = None
        self.camera_thread = None
        self.camera_running = False

    def camera_reader(self):
        """Camera reader optimized for ultra-low latency."""
        buffer = b''
        
        while self.camera_running:
            try:
                if not self.camera_process or self.camera_process.poll() is not None:
                    self.setup_camera_process()
                    buffer = b''  # Reset buffer
                    time.sleep(0.05)  # Shorter wait for faster restart
                    continue
                    
                # Read data from camera process (smaller chunks for responsiveness)
                data = self.camera_process.stdout.read(2048)
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
                                self.frame_queue.put(frame, block=False)
                            except queue.Full:
                                try:
                                    self.frame_queue.get_nowait()  # Remove oldest
                                    self.frame_queue.put(frame, block=False)
                                except:
                                    pass
                    except Exception as e:
                        logger.error(f"Frame decode error: {e}")
                        
            except Exception as e:
                logger.error(f"Camera reader error: {e}")
                time.sleep(0.001)  # Very short sleep

    def setup_camera_process(self):
        """Setup camera process with ultra-low latency settings."""
        if self.camera_process:
            try:
                self.camera_process.terminate()
                self.camera_process.wait(timeout=1)
            except:
                self.camera_process.kill()
            self.camera_process = None
        
        try:
            # Ultra-low latency optimized camera command
            rpicam_cmd = [
                "rpicam-vid",
                "-t", "0",              # Run forever
                "-n",                   # No preview
                "--width", str(self.config["width"]),
                "--height", str(self.config["height"]),
                "--framerate", str(self.config["fps"]),
                "--codec", "mjpeg",     # MJPEG output
                "--quality", str(self.config["quality"]),      # Optimized quality
                "--sharpness", str(self.config["sharpness"]),  # Sharpness
                "--contrast", str(self.config["contrast"]),    # Contrast
                "--saturation", str(self.config["saturation"]), # Saturation
                "--brightness", str(self.config["brightness"]), # Brightness
                "--denoise", self.config["denoise"],           # Minimal denoise
                "--awb", "auto",        # Auto white balance
                "--flush",              # Immediate flush for low latency
                "--save-pts", "0",      # No timestamp saving
                "--verbose", "0",       # No verbose output
                "-o", "-"               # Output to stdout
            ]
            
            # Remove empty arguments
            rpicam_cmd = [arg for arg in rpicam_cmd if arg]
            
            logger.info(f"Starting ultra-low latency camera with: {' '.join(rpicam_cmd)}")
            self.camera_process = subprocess.Popen(
                rpicam_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=256*1024  # Smaller buffer for responsiveness
            )
            
            # Very fast startup check
            time.sleep(0.1)
            if self.camera_process.poll() is not None:
                stderr_output = self.camera_process.stderr.read().decode('utf-8', errors='ignore')
                logger.error(f"Camera process failed: {stderr_output}")
                raise RuntimeError(f"Camera process failed: {stderr_output}")
                
            logger.info("Ultra-low latency camera started successfully")
            
        except FileNotFoundError:
            logger.error("rpicam-vid not found. Install with: sudo apt install rpicam-apps")
            raise
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            raise

    def start_camera(self):
        """Start camera capture."""
        self.camera_running = True
        self.setup_camera_process()
        self.camera_thread = threading.Thread(target=self.camera_reader, daemon=True)
        self.camera_thread.start()
        logger.info("Ultra-low latency camera capture started")

    def stop_camera(self):
        """Stop camera capture."""
        self.camera_running = False
        
        if self.camera_process:
            try:
                self.camera_process.terminate()
                self.camera_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.camera_process.kill()
            except:
                pass
            self.camera_process = None
        
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=1)
        
        # Clear queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                break
        
        logger.info("Camera capture stopped")
