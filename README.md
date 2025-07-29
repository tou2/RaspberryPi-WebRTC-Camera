# 🚀 Pi WebRTC Camera Streaming

Ultra-low latency WebRTC video streaming solution optimized for all Raspberry Pi models. Stream your Pi camera to any web browser with minimal delay and professional features.

## ✨ Key Features

- **Ultra-Low Latency**: <100ms on local network
- **Universal Pi Support**: Zero W through Pi 5
- **Web-Based**: No client software needed
- **Adaptive Quality**: Automatically optimizes for your hardware
- **Multiple Deployment Options**: Native Python or Docker
- **Professional Monitoring**: Real-time performance stats

## 📋 Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| **Pi Models** | Pi Zero W, Zero 2 W, Pi 3/4/5 |
| **Camera** | Pi Camera Module (v1/v2/v3/HQ) |
| **Storage** | 16GB+ MicroSD (Class 10+) |
| **Network** | WiFi or Ethernet |

### Expected Performance

| Model | Resolution | FPS | Viewers | CPU Usage |
|-------|------------|-----|---------|-----------|
| Pi Zero W | 640x480 | 15-20 | 2-3 | 60-80% |
| Pi Zero 2 W | 1280x720 | 25-30 | 3-5 | 40-60% |
| Pi 3 B/B+ | 1280x720 | 25-30 | 3-5 | 40-60% |
| Pi 4 | 1920x1080 | 30+ | 5-10 | 20-40% |
| Pi 5 | 1920x1080+ | 30+ | 10+ | 15-30% |

---

## 🚀 Quick Start

### Option 1: Automatic Setup (Recommended)

```bash
# Download and run the installer
chmod +x install.sh
./install.sh

# Reboot to apply camera settings
sudo reboot

# Start streaming
./start_stream.sh
```

### Option 2: Docker Deployment

```bash
# Start with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### Accessing Your Stream

1. Find your Pi's IP: `hostname -I`
2. Open browser: `http://[PI_IP]:8080`
3. Click "Start Stream"

---

## 📊 Performance Optimization

### Pi Zero W Settings
```ini
Resolution: 640x480
Frame Rate: 15-20 fps
Bitrate: 300-500 kbps
Profile: Baseline H.264
```

### Pi Zero 2 W Settings
```ini
Resolution: 1280x720
Frame Rate: 25-30 fps  
Bitrate: 600-1200 kbps
Profile: Main H.264
```

### Pi 4/5 Settings
```ini
Resolution: 1920x1080
Frame Rate: 30+ fps
Bitrate: 1-5 Mbps
Profile: High H.264
```

---

## 🛠️ Configuration

### Interactive Configuration Wizard
```bash
python3 configure.py
```

### Manual Configuration (`config.ini`)
```ini
[camera]
width = 640
height = 480
fps = 20
buffer_size = 1

[encoding]
bitrate = 500000
h264_profile = baseline

[network]
port = 8080
max_connections = 3

[performance]
low_latency_mode = true
video_threads = 2
```

---

## 🐳 Docker Deployment

### Quick Start
```bash
docker-compose up --build -d
```

### Manual Docker Commands
```bash
# Build image
docker build -t webrtc-camera .

# Run container
docker run -d \
  --name webrtc-camera \
  -p 8080:8080 \
  --device /dev/video0:/dev/video0 \
  --privileged \
  webrtc-camera
```

### Docker Management
```bash
# View logs
docker-compose logs -f

# Stop container
docker-compose down

# Restart
docker-compose restart
```

---

## 📈 Monitoring & Management

### System Status
```bash
./status.sh                    # Complete system diagnostics
./performance_test.py          # Benchmark your setup
```

### Service Management
```bash
# Start/stop service
sudo systemctl start webrtc-camera.service
sudo systemctl stop webrtc-camera.service

# Enable auto-start
sudo systemctl enable webrtc-camera.service

# View logs
sudo journalctl -u webrtc-camera.service -f
```

### Real-time Stats
Access monitoring dashboard: `http://[PI_IP]:8080/stats`

---

## 🔧 Troubleshooting

### Camera Issues
```bash
# Test camera
vcgencmd get_camera
raspistill -o test.jpg

# Check video devices
ls /dev/video*
```

### Performance Issues
1. **Lower resolution** in config.ini
2. **Reduce frame rate**
3. **Check temperature**: `vcgencmd measure_temp`
4. **Monitor CPU**: `top`

### Network Issues
```bash
# Check server status
sudo netstat -tlnp | grep 8080

# Verify firewall
sudo ufw status
```

---

## 🎯 Use Cases

- **Home Security**: Remote monitoring
- **Pet Watching**: Keep an eye on pets
- **Workshop Monitoring**: 3D printer observation
- **Wildlife Camera**: Nature observation
- **Baby Monitor**: Child monitoring
- **Live Streaming**: Broadcast to web

---

## 📚 Advanced Features

### Multiple Camera Support
Run multiple instances on different ports for multiple cameras.

### Custom STUN/TURN Servers
```ini
[network]
ice_servers = [
    {"urls": "stun:your-server.com:3478"},
    {"urls": "turn:your-server.com:3478", "username": "user", "credential": "pass"}
]
```

### Home Assistant Integration
REST API endpoints available for automation systems.

---

## 🔒 Security Notes

- Server binds to all interfaces (0.0.0.0)
- Consider firewall rules for public access
- Use HTTPS in production environments
- Add authentication for internet-facing deployments

### Basic Firewall Setup
```bash
sudo ufw enable
sudo ufw allow 8080/tcp
sudo ufw allow ssh
```

---

## 📦 Project Structure

```
twistedcamera/
├── 📄 Core Servers
│   ├── webrtc_server.py       # Basic streaming server
│   ├── enhanced_server.py     # Advanced server with monitoring
│   └── config.ini            # Configuration settings
│
├── �️ Setup & Management  
│   ├── install.sh            # Automated installation
│   ├── configure.py          # Configuration wizard
│   ├── start_stream.sh       # Start streaming
│   ├── stop_stream.sh        # Stop streaming
│   ├── status.sh             # System diagnostics
│   └── performance_test.py   # Performance testing
│
├── 🐳 Docker
│   ├── Dockerfile           # Container configuration
│   └── docker-compose.yml   # Orchestration setup
│
└── 📚 Documentation
    ├── README.md            # This guide
    └── OS_RECOMMENDATIONS.md # OS selection guide
```

---

## 💡 Pro Tips

1. **Use Pi OS Lite** for headless operation
2. **Position Pi near router** for strong WiFi signal  
3. **Use fast MicroSD card** (Class 10+)
4. **Monitor temperature** during extended use
5. **Consider Pi Zero 2 W** for best price/performance

---

## 🤝 Support & Contributing

### Getting Help
1. Check troubleshooting section
2. Review system logs with `./status.sh`
3. Test with default configuration
4. Monitor system resources

### Contributing
1. Fork the repository
2. Test on actual Pi hardware
3. Submit pull requests

---

## 📄 License

This project is open source. Feel free to modify and distribute.

---

**Ready to start streaming?** Run `./install.sh` and you'll be up and running in minutes! 🎥

---

## 📦 Complete Project Structure

```
twistedcamera/
├── 📄 Core Server Files
│   ├── webrtc_server.py          # Basic WebRTC streaming server
│   ├── enhanced_server.py        # Advanced server with monitoring & adaptive quality
│   ├── config.ini               # Configuration file for easy customization
│   └── requirements.txt         # Python dependencies
│
├── 🛠️ Installation & Setup
│   ├── install.sh              # Automated installation script (Linux/Pi)
│   └── configure.py            # Interactive configuration wizard
│
├── 🎮 Management Scripts
│   ├── start_stream.sh         # Start the streaming server
│   ├── stop_stream.sh          # Stop all streaming processes
│   ├── status.sh               # System diagnostics and status check
│   └── performance_test.py     # Performance testing and optimization
│
├── 🐳 Container Deployment
│   ├── Dockerfile              # Docker container setup
│   └── docker-compose.yml      # Docker Compose configuration
│
└── 📚 Documentation
    └── README.md               # This comprehensive guide
```

### File Descriptions

#### 📄 Core Server Files
- **`webrtc_server.py`**: Basic WebRTC server with essential streaming functionality
- **`enhanced_server.py`**: Advanced server with performance monitoring, adaptive quality, and web interface
- **`config.ini`**: Configuration file with all customizable settings (camera, encoding, network, performance)
- **`requirements.txt`**: All Python package dependencies for easy installation

#### 🛠️ Installation & Setup
- **`install.sh`**: Comprehensive installation script that handles system packages, Python environment, camera setup, and service configuration
- **`configure.py`**: Interactive wizard to generate optimal configuration based on your hardware and use case

#### 🎮 Management Scripts
- **`start_stream.sh`**: Convenient script to activate environment and start streaming with status checks
- **`stop_stream.sh`**: Safely stops all streaming processes and releases camera resources
- **`status.sh`**: Comprehensive system diagnostics including camera, service, network, and performance status
- **`performance_test.py`**: Automated testing script to benchmark your system and provide optimization recommendations

#### 🐳 Container Deployment
- **`Dockerfile`**: Multi-stage Docker build optimized for Raspberry Pi with minimal footprint
- **`docker-compose.yml`**: Complete container orchestration with proper device mapping and resource limits

---

## � Docker Deployment Guide

### Quick Start with Docker

The easiest way to deploy using Docker:

```bash
# Build and start the container
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Docker Compose Configuration

The `docker-compose.yml` provides a complete setup:

```yaml
version: '3.8'
services:
  webrtc-camera:
    build: .
    ports:
      - "8080:8080"
    devices:
      - /dev/video0:/dev/video0  # Camera access
    volumes:
      - ./config.ini:/app/config.ini:ro
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    privileged: true  # Required for camera access
```

### Manual Docker Commands

#### Build the Image
```bash
# Build for your Pi architecture
docker build -t webrtc-camera .

# Build for specific architecture (if cross-compiling)
docker buildx build --platform linux/arm/v6 -t webrtc-camera .  # Pi Zero
docker buildx build --platform linux/arm64 -t webrtc-camera .   # Pi 4/5
```

#### Run the Container
```bash
# Basic run
docker run -d \
  --name webrtc-camera \
  -p 8080:8080 \
  --device /dev/video0:/dev/video0 \
  --privileged \
  webrtc-camera

# Run with custom config
docker run -d \
  --name webrtc-camera \
  -p 8080:8080 \
  --device /dev/video0:/dev/video0 \
  -v $(pwd)/config.ini:/app/config.ini:ro \
  --privileged \
  webrtc-camera

# Run with interactive mode (for debugging)
docker run -it \
  --name webrtc-camera \
  -p 8080:8080 \
  --device /dev/video0:/dev/video0 \
  --privileged \
  webrtc-camera bash
```

### Docker Management Commands

```bash
# Container lifecycle
docker-compose up -d          # Start in background
docker-compose down           # Stop and remove
docker-compose restart        # Restart services
docker-compose pull           # Update images

# Monitoring
docker-compose logs -f        # Follow logs
docker-compose ps             # Check status
docker stats webrtc-camera    # Resource usage

# Maintenance
docker-compose down -v        # Remove with volumes
docker system prune           # Clean unused containers/images
```

### Docker Configuration Options

#### Environment Variables
Set these in `docker-compose.yml` or pass with `-e`:

```yaml
environment:
  - CAMERA_WIDTH=640
  - CAMERA_HEIGHT=480
  - CAMERA_FPS=20
  - SERVER_PORT=8080
  - BITRATE=500000
```

#### Volume Mounts
Customize configuration and data persistence:

```yaml
volumes:
  - ./config.ini:/app/config.ini:ro       # Custom config
  - ./logs:/app/logs                      # Log persistence
  - camera-data:/app/data                 # Data persistence
```

#### Device Access
Essential for camera functionality:

```yaml
devices:
  - /dev/video0:/dev/video0               # Primary camera
  - /dev/video1:/dev/video1               # Secondary camera (if available)
```

### Docker Networking

#### Default Setup
The container exposes port 8080 and maps it to the host:

```yaml
ports:
  - "8080:8080"                           # Host:Container
```

#### Custom Port Mapping
```yaml
ports:
  - "9090:8080"                           # Access via port 9090
```

#### Network Mode
For advanced networking:

```yaml
network_mode: "host"                      # Use host networking
```

### Multi-Architecture Support

The Dockerfile supports multiple Pi architectures:

#### For Pi Zero W (ARMv6)
```bash
docker buildx build --platform linux/arm/v6 -t webrtc-camera:armv6 .
```

#### For Pi Zero 2 W / Pi 3 (ARMv7)
```bash
docker buildx build --platform linux/arm/v7 -t webrtc-camera:armv7 .
```

#### For Pi 4/5 (ARM64)
```bash
docker buildx build --platform linux/arm64 -t webrtc-camera:arm64 .
```

### Production Deployment

#### Using Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml webrtc-stack
```

#### Resource Limits
Add to `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 256M      # Limit memory usage
      cpus: '0.5'       # Limit CPU usage
    reservations:
      memory: 128M
      cpus: '0.25'
```

### Troubleshooting Docker Issues

#### Camera Not Accessible
```bash
# Check camera device exists
ls -la /dev/video*

# Verify camera permissions
sudo usermod -a -G video $USER

# Check if camera is in use
lsof /dev/video0
```

#### Container Won't Start
```bash
# Check container logs
docker-compose logs webrtc-camera

# Check container status
docker ps -a

# Debug with shell access
docker-compose exec webrtc-camera bash
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats webrtc-camera

# Check system resources
free -h
top
```

#### Port Conflicts
```bash
# Check if port is in use
sudo netstat -tulpn | grep 8080

# Use different port
docker-compose down
# Edit docker-compose.yml to change port
docker-compose up -d
```

### Docker vs Native Installation

| Feature | Docker | Native |
|---------|--------|--------|
| **Setup Time** | Fast (5 min) | Longer (15-30 min) |
| **Isolation** | Excellent | None |
| **Updates** | Easy (`docker-compose pull`) | Manual |
| **Debugging** | Moderate | Easy |
| **Performance** | ~5% overhead | Native speed |
| **Disk Usage** | Higher (~500MB) | Lower (~100MB) |
| **System Integration** | Limited | Full |

### Docker Best Practices

1. **Use specific tags** instead of `latest` for production
2. **Set resource limits** to prevent system overload  
3. **Use health checks** for automatic container restart
4. **Mount config as read-only** for security
5. **Use multi-stage builds** to minimize image size
6. **Enable logging rotation** to prevent disk filling

#### Health Check Example
Add to `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Advanced Docker Features

#### Automatic Restart Policies
```yaml
restart: unless-stopped        # Restart unless manually stopped
restart: always               # Always restart
restart: on-failure:3         # Restart on failure, max 3 attempts
```

#### Custom Networks
```yaml
networks:
  camera-network:
    driver: bridge
```

#### Secrets Management
```yaml
secrets:
  camera_config:
    file: ./config.ini
```

---

## �🚀 Complete Solution Features

### Ultra-Low Latency Optimizations
- ⚡ **Minimal buffering** (1 frame buffer)
- 🎯 **Adaptive quality** based on system performance
- 📉 **Frame dropping** for latency control
- 🔧 **Hardware-specific optimizations** for Pi Zero
- 📹 **Direct camera access** with optimized settings

### Performance Features
- 📊 **Resource monitoring** (CPU, memory, temperature)
- 🔄 **Automatic quality adjustment** based on performance
- 🌐 **Multiple connection support** with limits
- 📈 **Real-time statistics** and diagnostics
- ⬇️ **Graceful degradation** under load

### User-Friendly Features
- 🌐 **Web-based interface** - no client software needed
- 📱 **Responsive design** - works on mobile devices
- 🖥️ **Fullscreen mode** for immersive viewing
- 📊 **Real-time stats display** in the web interface
- ⚙️ **Easy configuration** through config files

---

## 🛠️ Complete Installation Process

1. **📥 Copy all files** to your Pi Zero
2. **🔧 Run the installation script**: `chmod +x install.sh && ./install.sh`
3. **🔄 Reboot your Pi**: `sudo reboot`
4. **🚀 Start streaming**: `./start_stream.sh`
5. **🌐 Access via browser**: `http://[PI_IP]:8080`

---

## ⚡ Performance Optimizations by Pi Model

### Pi Zero W Optimizations:
- 📺 **Lower default resolution** (640x480)
- 🎬 **Reduced frame rate** (20 fps)
- 🔧 **Baseline H.264 profile** (lowest CPU usage)
- 💾 **Memory-mapped I/O** for better performance
- 🧵 **Minimal threading** to reduce overhead
- 📊 **Adaptive bitrate** based on performance
- ⚡ **Smart frame dropping** when overloaded

### Pi Zero 2 W Optimizations:
- 📺 **720p resolution** (1280x720)
- 🎬 **Standard frame rate** (25-30 fps)
- 🔧 **Main H.264 profile** (balanced quality/performance)
- 🧵 **Quad-core processing** (4 threads)
- 📊 **Dynamic bitrate adjustment**
- ⚡ **Moderate frame dropping**

### Pi 3 Optimizations:
- 📺 **720p resolution** (1280x720)
- 🎬 **Standard frame rate** (25-30 fps)
- 🔧 **Main H.264 profile** (balanced quality/performance)
- 🧵 **Moderate threading** (2-4 threads)
- 📊 **Dynamic bitrate adjustment**

### Pi 4/Pi 5 Optimizations:
- 📺 **Full HD resolution** (1920x1080)
- 🎬 **High frame rate** (30+ fps)
- 🔧 **High H.264 profile** (best quality)
- ⚡ **Hardware acceleration** (GPU encoding when available)
- 🧵 **Multi-threading** (4-8 threads)
- 📊 **High bitrate streaming** (up to 5 Mbps)
- 🚀 **Multiple concurrent streams**

---

## 🎯 Expected Performance

### Pi Zero W
- ⚡ **Latency**: 50-150ms on local network
- 📺 **Resolution**: 640x480 @ 15-20 fps
- 📊 **Bitrate**: 300-800 kbps
- 🖥️ **CPU Usage**: 60-80% under normal conditions
- 👥 **Multiple viewers**: 2-3 concurrent connections

### Pi Zero 2 W
- ⚡ **Latency**: 35-120ms on local network
- 📺 **Resolution**: 1280x720 @ 25-30 fps
- 📊 **Bitrate**: 600-1200 kbps
- 🖥️ **CPU Usage**: 40-60% under normal conditions
- 👥 **Multiple viewers**: 3-5 concurrent connections

### Pi 3 B/B+
- ⚡ **Latency**: 30-100ms on local network
- 📺 **Resolution**: 1280x720 @ 25-30 fps
- 📊 **Bitrate**: 800-1500 kbps
- 🖥️ **CPU Usage**: 40-60% under normal conditions
- 👥 **Multiple viewers**: 3-5 concurrent connections

### Pi 4
- ⚡ **Latency**: 20-80ms on local network
- 📺 **Resolution**: 1920x1080 @ 30 fps
- 📊 **Bitrate**: 1-3 Mbps
- 🖥️ **CPU Usage**: 20-40% under normal conditions
- 👥 **Multiple viewers**: 5-10 concurrent connections

### Pi 5
- ⚡ **Latency**: 15-60ms on local network
- 📺 **Resolution**: 1920x1080+ @ 30+ fps
- 📊 **Bitrate**: 2-5 Mbps
- 🖥️ **CPU Usage**: 15-30% under normal conditions
- 👥 **Multiple viewers**: 10+ concurrent connections

The system automatically adapts quality to maintain performance and low latency across all Pi models.

---

## 🚀 Why Use Pi 4/Pi 5?

### Advantages over Pi Zero W:

#### 🔥 **Significantly Better Performance**
- **4-8x faster CPU** for smoother video processing
- **More RAM** (2-8GB vs 512MB) for better multitasking
- **Hardware video acceleration** for efficient encoding
- **Gigabit Ethernet** for stable, high-bandwidth streaming

#### 📺 **Superior Video Quality**
- **Full 1080p streaming** at 30+ FPS
- **Higher bitrates** (up to 5 Mbps) for crisp video
- **Multiple concurrent viewers** (10+ connections)
- **Better low-light performance** with advanced processing

#### 🌐 **Enhanced Features**
- **Dual display support** (Pi 4/5) for monitoring + streaming
- **USB 3.0 ports** for external storage or additional cameras
- **Better thermal management** for sustained performance
- **Future-proof** with ongoing software updates

#### ⚙️ **Professional Use Cases**
- **Security systems** with multiple camera inputs
- **Live streaming** to platforms like YouTube/Twitch
- **Remote monitoring** of industrial equipment
- **Educational demonstrations** with high-quality video

### 🚀 Pi Zero 2 W: The Sweet Spot

The **Pi Zero 2 W** offers a compelling middle ground:

#### 💡 **Key Advantages over Pi Zero W**
- **5x faster** quad-core ARM Cortex-A53 CPU
- **Same form factor** and power consumption
- **720p streaming** capability instead of 480p
- **Better multitasking** with more processing power
- **Improved latency** (35-120ms vs 50-150ms)

#### 💰 **Cost-Effective Upgrade**
- **Minimal price increase** over Pi Zero W
- **Significant performance boost** for streaming
- **Better long-term value** for most use cases
- **Same accessories** and cases work

### Recommended Pi Model by Use Case:

| Use Case | Pi Zero W | Pi Zero 2 W | Pi 3 | Pi 4 | Pi 5 |
|----------|-----------|-------------|------|------|------|
| Basic monitoring | ✅ Ideal | ✅ Great | ✅ Good | ✅ Overkill | ✅ Overkill |
| Home security | ⚠️ Limited | ✅ Good | ✅ Good | ✅ Excellent | ✅ Excellent |
| Live streaming | ❌ Too slow | ⚠️ Basic | ⚠️ Basic | ✅ Great | ✅ Perfect |
| Multiple cameras | ❌ No | ⚠️ 2 max | ⚠️ 2 max | ✅ 3-4 | ✅ 5+ |
| Professional use | ❌ No | ⚠️ Limited | ⚠️ Limited | ✅ Yes | ✅ Ideal |
| Budget priority | ✅ Cheapest | ✅ Best value | ⚠️ OK | ❌ Expensive | ❌ Expensive |

---

## 🔧 Easy Management Commands

- **🚀 Start**: `./start_stream.sh`
- **🛑 Stop**: `./stop_stream.sh`
- **📊 Status**: `./status.sh`
- **⚙️ Configure**: `python3 configure.py`
- **🧪 Test Performance**: `python3 performance_test.py`

This solution provides professional-grade, ultra-low latency streaming optimized specifically for Raspberry Pi Zero's constraints while maintaining ease of use and comprehensive monitoring capabilities.