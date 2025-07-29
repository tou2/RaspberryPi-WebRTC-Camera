# 🚀 Pi Zero WebRTC Camera Streaming

Ultra-low latency WebRTC video streaming solution optimized for Raspberry Pi Zero. This project provides real-time camera streaming with adaptive quality, performance monitoring, and extensive optimization for resource-constrained devices.

## ✨ Features

- **Ultra-Low Latency**: Optimized for minimal delay (typically <100ms on local network)
- **Adaptive Quality**: Automatically adjusts video quality based on device performance
- **Resource Efficient**: Specifically optimized for Raspberry Pi Zero's limited resources
- **Web-Based Client**: No additional software needed - just open a browser
- **Performance Monitoring**: Real-time stats and system monitoring
- **Configurable**: Easy configuration through config files
- **Multiple Connections**: Support for multiple simultaneous viewers

## 📋 Requirements

- Raspberry Pi Zero W (or any Pi with camera support)
- Raspberry Pi Camera Module (v1, v2, or HQ camera)
- MicroSD card (16GB+ recommended)
- Stable internet connection

## 🚀 Quick Start

### 1. Automatic Installation

Run the installation script to set up everything automatically:

```bash
chmod +x install.sh
./install.sh
```

The script will:
- Update your system
- Install all required packages
- Configure the camera
- Set up Python environment
- Create systemd service
- Apply performance optimizations

### 2. Manual Installation

If you prefer manual setup:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3 python3-pip python3-venv git

# Clone/download project files
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Enable camera
sudo raspi-config nonint do_camera 0
```

### 3. Configuration

Edit `config.ini` to customize settings:

```ini
[camera]
width = 640          # Video width (lower = better performance)
height = 480         # Video height
fps = 20            # Frame rate (lower = better performance)

[encoding]
bitrate = 500000    # Bitrate in bps (adjust for network)

[network]
port = 8080         # Server port
```

### 4. Running the Server

#### Option A: Direct Run
```bash
source venv/bin/activate
python webrtc_server.py
```

#### Option B: Enhanced Server
```bash
source venv/bin/activate
python enhanced_server.py
```

#### Option C: System Service
```bash
sudo systemctl start webrtc-camera.service
sudo systemctl enable webrtc-camera.service  # Auto-start on boot
```

### 5. Accessing the Stream

1. Find your Pi's IP address: `hostname -I`
2. Open a web browser and go to: `http://[PI_IP]:8080`
3. Click "Start Stream" to begin streaming

## 📊 Performance Optimization

### For Pi Zero W:
- **Resolution**: 640x480 or lower
- **FPS**: 15-20 for best performance
- **Bitrate**: 200-500 kbps
- **Buffer Size**: 1 (minimal latency)

### For Pi 4:
- **Resolution**: Up to 1080p
- **FPS**: 30
- **Bitrate**: 1-2 Mbps

## 🛠️ Configuration Options

### Camera Settings
```ini
[camera]
device_index = 0      # Camera device (/dev/video0)
width = 640          # Video width in pixels
height = 480         # Video height in pixels
fps = 20             # Target frame rate
buffer_size = 1      # Camera buffer size (1 = low latency)
```

### Encoding Settings
```ini
[encoding]
bitrate = 500000         # Target bitrate in bits/second
h264_profile = baseline  # H.264 profile (baseline/main/high)
keyframe_interval = 2    # Keyframe interval in seconds
```

### Performance Settings
```ini
[performance]
use_gpu_acceleration = true    # Use GPU acceleration if available
video_threads = 2             # Number of video processing threads
low_latency_mode = true       # Enable low-latency optimizations
frame_drop_strategy = smart   # Frame dropping strategy
```

## 📈 Monitoring

The enhanced server provides real-time monitoring:

- **Connection Stats**: State, uptime, ICE status
- **Video Stats**: Frame rate, resolution, bitrate
- **Network Stats**: Bandwidth, packet loss, jitter
- **System Stats**: CPU usage, memory, temperature

Access stats at: `http://[PI_IP]:8080/stats`

## 🔧 Troubleshooting

### Camera Not Detected
```bash
# Check camera connection
vcgencmd get_camera

# Test camera manually
raspistill -o test.jpg

# Check video devices
ls /dev/video*
```

### Poor Performance
1. Lower resolution in `config.ini`
2. Reduce frame rate
3. Lower bitrate
4. Enable low-latency mode
5. Check CPU temperature: `vcgencmd measure_temp`

### Connection Issues
```bash
# Check if service is running
sudo systemctl status webrtc-camera.service

# View logs
sudo journalctl -u webrtc-camera.service -f

# Check port availability
sudo netstat -tlnp | grep 8080
```

### High CPU Usage
1. Reduce video resolution
2. Lower frame rate
3. Use baseline H.264 profile
4. Enable frame dropping
5. Check temperature throttling

## 📱 Client Features

### Web Interface
- **Start/Stop Streaming**: Easy control buttons
- **Fullscreen Mode**: Immersive viewing experience
- **Real-time Stats**: Performance monitoring
- **Responsive Design**: Works on mobile devices

### Keyboard Shortcuts
- `F` - Toggle fullscreen
- `S` - Start/stop stream
- `Esc` - Exit fullscreen

## 🚦 Service Management

```bash
# Start service
sudo systemctl start webrtc-camera.service

# Stop service
sudo systemctl stop webrtc-camera.service

# Enable auto-start
sudo systemctl enable webrtc-camera.service

# Check status
sudo systemctl status webrtc-camera.service

# View logs
sudo journalctl -u webrtc-camera.service -f
```

## 🔒 Security Considerations

1. **Network Access**: Server binds to all interfaces (0.0.0.0)
2. **Firewall**: Consider restricting access to specific IPs
3. **HTTPS**: For production, use HTTPS with proper certificates
4. **Authentication**: Add authentication for public deployments

### Enable Firewall
```bash
sudo ufw enable
sudo ufw allow 8080/tcp
sudo ufw allow ssh
```

## 🎯 Use Cases

- **Home Security**: Monitor your home remotely
- **Pet Monitoring**: Keep an eye on pets
- **Baby Monitor**: Watch over children
- **Workshop Monitoring**: Monitor 3D printers, etc.
- **Garden Monitoring**: Time-lapse photography
- **Wildlife Observation**: Remote wildlife watching

## 🐛 Known Issues

1. **First Boot**: May take 10-15 minutes for initial compilation on Pi Zero
2. **Memory Usage**: Long sessions may require periodic restart
3. **Heat**: Ensure adequate cooling for continuous operation
4. **WiFi Stability**: Use 5GHz WiFi when possible for better performance

## 📚 Advanced Usage

### Custom STUN/TURN Servers
Edit `config.ini`:
```ini
[network]
ice_servers = [
    {"urls": "stun:your-stun-server.com:3478"},
    {"urls": "turn:your-turn-server.com:3478", "username": "user", "credential": "pass"}
]
```

### Multiple Camera Support
Create separate config files and run multiple instances on different ports.

### Integration with Home Assistant
The server provides a REST API that can be integrated with home automation systems.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on actual Pi Zero hardware
5. Submit a pull request

## 📄 License

This project is open source. Feel free to modify and distribute.

## 💡 Tips for Best Performance

1. **Use wired connection** when possible for setup
2. **Position Pi close to router** for strong WiFi signal
3. **Use fast MicroSD card** (Class 10 or better)
4. **Monitor temperature** and add cooling if needed
5. **Close unnecessary services** to free up resources
6. **Use 5GHz WiFi** if your Pi supports it

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section
2. Review system logs
3. Test with default configuration
4. Monitor system resources
5. Verify camera hardware

Happy streaming! 🎥
