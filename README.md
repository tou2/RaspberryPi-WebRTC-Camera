# 🚀 Pi WebRTC Camera Streaming

Ultra-low latency WebRTC video streaming solution optimized for all Raspberry Pi models. Stream your Pi camera to any web browser with minimal delay.

## ✨ Key Features

- **Ultra-Low Latency**: <100ms on local network
- **Universal Pi Support**: Zero W through Pi 5
- **Web-Based**: No client software needed
- **Adaptive Quality**: Automatically optimizes for your hardware
- **Multiple Deployment Options**: Native Python or Docker

## 📋 Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| **Pi Models** | Pi Zero W, Zero 2 W, Pi 3/4/5 |
| **Camera** | Pi Camera Module (v1/v2/v3/HQ) |
| **Storage** | 16GB+ MicroSD (Class 10+) |
| **Network** | WiFi or Ethernet |

## 📊 Expected Performance

| Model | Resolution | FPS | Viewers | CPU Usage |
|-------|------------|-----|---------|-----------|
| Pi Zero W | 640x480 | 15-20 | 2-3 | 60-80% |
| Pi Zero 2 W | 1280x720 | 25-30 | 3-5 | 40-60% |
| Pi 3 B/B+ | 1280x720 | 25-30 | 3-5 | 40-60% |
| Pi 4 | 1920x1080 | 30+ | 5-10 | 20-40% |
| Pi 5 | 1920x1080+ | 30+ | 10+ | 15-30% |

## 🚀 Quick Start

### Automatic Setup (Recommended)

```bash
# Download and run the installer
chmod +x install.sh
./install.sh

# Reboot to apply camera settings
sudo reboot

# Start streaming
./start_stream.sh
```

### Accessing Your Stream

1. Find your Pi's IP: `hostname -I`
2. Open browser: `http://[PI_IP]:8080`
3. Click "Start Stream"

## ⚙️ Configuration

### Interactive Configuration
```bash
python3 configure.py
```

### Manual Configuration (`config.ini`)
```ini
[camera]
width = 640
height = 480
fps = 20

[encoding]
bitrate = 500000
h264_profile = baseline

[network]
port = 8080
max_connections = 3
```

## 🐳 Docker Deployment

Deploy the WebRTC camera server using Docker for easy setup and portability.

### Quick Start (Recommended)
```bash
docker-compose up --build -d
```

### Manual Docker Commands
```bash
# Build the image
docker build -t webrtc-camera .

# Run the container
# (Expose port 8080 and grant camera access)
docker run -d --name webrtc-camera -p 8080:8080 --device /dev/video0:/dev/video0 --privileged webrtc-camera

# Management
# View logs
docker-compose logs -f
# Stop and remove container
docker-compose down
```

### Notes
- Ensure your Pi camera is enabled and accessible as `/dev/video0`.
- For multiple cameras, run containers on different ports and map additional devices.
- For troubleshooting, check container logs and camera diagnostics scripts.

## 🛠️ Management & Monitoring
```bash
./status.sh                    # System diagnostics
./performance_test.py          # Benchmark setup
./camera_test.sh              # Test camera functionality

# Service Management
sudo systemctl start webrtc-camera.service   # Start service
sudo systemctl stop webrtc-camera.service    # Stop service
sudo systemctl enable webrtc-camera.service  # Auto-start
sudo journalctl -u webrtc-camera.service -f  # View logs

# Access real-time stats
http://[PI_IP]:8080/stats
```

## 🔧 Troubleshooting

### Camera Issues
```bash
# Test camera (comprehensive diagnostics)
./camera_test.sh

# Manual tests
vcgencmd get_camera           # Check hardware detection
libcamera-hello --timeout 2000  # Test new cameras
raspistill -o test.jpg        # Test legacy cameras
ls /dev/video*               # Check video devices
```

### Performance Issues
1. Lower resolution in `config.ini`
2. Reduce frame rate
3. Check temperature: `vcgencmd measure_temp`
4. Monitor CPU: `top`

### Network Issues
```bash
sudo netstat -tlnp | grep 8080  # Check server status
sudo ufw status                  # Verify firewall
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
├── webrtc_server.py       # Basic streaming server
├── enhanced_server.py     # Advanced server with monitoring
├── config.ini             # Configuration settings
├── requirements.txt       # Python dependencies
├── install.sh             # Automated installation
├── configure.py           # Configuration wizard
├── start_stream.sh        # Start streaming
├── stop_stream.sh         # Stop streaming
├── status.sh              # System diagnostics
├── performance_test.py    # Performance testing
├── camera_test.sh         # Camera troubleshooting
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Orchestration setup
├── README.md              # This guide
└── OS_RECOMMENDATIONS.md  # OS selection guide
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