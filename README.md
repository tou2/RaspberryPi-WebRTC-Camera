# Pi WebRTC Camera Stream

A simple, low-latency WebRTC video streaming server for Raspberry Pi, optimized for the Raspberry Pi Camera Module v3 and newer.

## Key Features

-   **Low Latency**: Streams video directly to your web browser with minimal delay.
-   **Raspberry Pi Optimized**: Specifically designed to work with `rpicam-vid` for efficient, hardware-accelerated video capture on modern Raspberry Pi boards (Bullseye OS or newer).
-   **Configurable**: Key settings like resolution, FPS, and quality can be adjusted directly within the `enhanced_server.py` script.
-   **Web-Based UI**: A clean web interface allows you to start, stop, and control the stream, including camera rotation.
-   **Simple & Self-Contained**: Everything is in a single Python script (`enhanced_server.py`) using `aiohttp` and `aiortc`.

## Requirements

-   **Hardware**:
    -   A Raspberry Pi (Pi Zero 2 W, Pi 3, 4, or 5 recommended).
    -   Raspberry Pi Camera Module (v2, v3, or HQ).
-   **Software**:
    -   Raspberry Pi OS (Bullseye or newer).
    -   Python 3.
    -   `rpicam-apps` installed (`sudo apt install rpicam-apps`).

## Quick Start

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tou2/RaspberryPi-WebRTC-Camera.git
    cd RaspberryPi-WebRTC-Camera
    ```

2.  **Run the installer:**
    This script will install Python dependencies and set up a systemd service to run the server automatically.
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

3.  **Reboot the system:**
    A reboot is recommended to ensure all system changes are applied.
    ```bash
    sudo reboot
    ```

4.  **Start the streaming server:**
    After rebooting, the service should start automatically. You can also start it manually:
    ```bash
    ./start_stream.sh
    ```
    Or control the systemd service:
    ```bash
    sudo systemctl start webrtc_stream.service
    ```

5.  **Access Your Stream:**
    -   Find your Raspberry Pi's IP address: `hostname -I`
    -   Open a web browser on another device on the same network and go to `http://<YOUR_PI_IP>:8080`.
    -   Click "Start" to begin streaming.

## How It Works

This server uses a modern and efficient pipeline for streaming:

1.  **`rpicam-vid`**: The official command-line tool from the Raspberry Pi Foundation is used to capture video. It's configured to output a high-framerate MJPEG stream to `stdout`.
2.  **Python `subprocess`**: The Python server runs `rpicam-vid` as a subprocess and reads the MJPEG video data directly from its standard output pipe.
3.  **`aiortc`**: The Python script handles the WebRTC signaling and connection. When a frame is requested by the client, it reads the latest complete MJPEG frame from the pipe, decodes it, and sends it over the peer connection.

## Configuration

The server is configured by editing the `CONFIG` dictionary at the top of the `enhanced_server.py` script.

```python
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
```

## Development

To run the server directly for development without installing the service:

1.  Make sure you have installed the dependencies and created the virtual environment by running `./install.sh`.
2.  Activate the virtual environment:
    ```bash
    source venv/bin/activate
    ```
3.  Run the server directly:
    ```bash
    python3 enhanced_server.py
    ```
4.  Press `Ctrl+C` to stop the server.
5.  When you are finished, you can deactivate the virtual environment by simply running:
    ```bash
    deactivate
    ```