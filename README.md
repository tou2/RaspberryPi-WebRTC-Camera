# Pi WebRTC Camera Stream

A simple, low-latency WebRTC video streaming server for Raspberry Pi, optimized for the Raspberry Pi Camera Module v3 and newer.

## Key Features

-   **Low Latency**: Streams video directly to your web browser with minimal delay.
-   **Raspberry Pi Optimized**: Specifically designed to work with `rpicam-vid` for efficient, hardware-accelerated video capture on modern Raspberry Pi boards (Bullseye OS or newer).
-   **Configurable**: Settings can be adjusted in `config.ini` (camera resolution, FPS, network ports).
-   **Web-Based UI**: A clean web interface allows you to start, stop, and control the stream.
-   **Simple & Self-Contained**: Everything is in a single Python script (`enhanced_server.py`) using `aiohttp` and `aiortc`. No complex dependencies.

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
    This script will install Python dependencies, create a default `config.ini`, and set up a systemd service.
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

3.  **Start the streaming server:**
    ```bash
    ./start_stream.sh
    ```
    You can view the server logs with `journalctl -u webrtc_stream.service -f`.

    Or run as a systemd service:
    ```bash
    sudo systemctl start webrtc_stream.service
    ```

4.  **Access Your Stream:**
    -   Find your Raspberry Pi's IP address: `hostname -I`
    -   Open a web browser on another device on the same network and go to `http://<YOUR_PI_IP>:8080`.
    -   Click "Start" to begin streaming.

## How It Works

This server uses a modern and efficient pipeline for streaming:

1.  **`rpicam-vid`**: The official command-line tool from the Raspberry Pi Foundation is used to capture video. It's configured to output a high-framerate MJPEG stream to `stdout`.
2.  **Python `subprocess`**: The Python server runs `rpicam-vid` as a subprocess and reads the MJPEG video data directly from its standard output pipe.
3.  **`aiortc`**: The Python script handles the WebRTC signaling and connection. When a frame is requested by the client, it reads the latest complete MJPEG frame from the pipe, decodes it, and sends it over the peer connection.

## Configuration

The server can be configured by editing the `config.ini` file. The default settings are:

```ini
[camera]
width = 640
height = 480
fps = 20

[network]
host = 0.0.0.0
port = 8080

[logging]
level = INFO
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