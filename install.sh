#!/bin/bash

# WebRTC Camera Streaming Setup Script for Raspberry Pi
# This script installs required packages and configures the camera.

set -e  # Exit on any error

echo "=================================================="
echo "🚀 WebRTC Camera Setup Script for Raspberry Pi 🚀"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root. Use sudo when needed."
    exit 1
fi

# Check if we're on a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is optimized for Raspberry Pi, but continuing anyway..."
fi

print_section "System Update"
print_status "Updating package lists..."
sudo apt-get update

print_status "Upgrading system packages..."
sudo apt-get upgrade -y

print_section "Installing System Dependencies"

# Essential system packages
print_status "Installing essential system packages..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    build-essential \
    cmake \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    rpicam-apps

print_section "Camera Configuration"

# Enable camera module - prioritize new camera support
print_status "Configuring camera module..."

# For new cameras (Camera Module 3+), use camera_auto_detect
# if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
#     echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
#     print_status "Camera auto-detect enabled (recommended for new cameras)"
# else
#     print_status "Camera auto-detect already enabled"
# fi

print_section "Python Environment Setup"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip setuptools wheel

print_section "Installing Python Dependencies"

# Create requirements.txt
print_status "Creating requirements.txt..."
cat > requirements.txt << 'EOF'
# Core WebRTC and media processing
aiortc
aiohttp
opencv-python
numpy
av

# Optional performance enhancements
uvloop
psutil
EOF

# Install Python packages
print_status "Installing Python packages (this may take a while)..."
pip install -r requirements.txt

print_section "Service Configuration"

# Create systemd service file
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/webrtc_stream.service > /dev/null << EOF
[Unit]
Description=WebRTC Camera Stream
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python enhanced_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable webrtc_stream.service

print_section "Performance Optimization"

# Set up performance optimizations for Pi Zero
print_status "Applying performance optimizations..."

# Camera optimizations
# if ! grep -q "disable_camera_led=1" /boot/config.txt; then
#     echo "disable_camera_led=1" | sudo tee -a /boot/config.txt
# fi

# Network optimizations
echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf

print_section "Firewall Configuration"

# Configure firewall if ufw is installed
if command -v ufw >/dev/null 2>&1; then
    print_status "Configuring firewall..."
    sudo ufw allow 8080/tcp
    print_status "Opened port 8080 for WebRTC server"
fi

print_section "Creating Startup Scripts"

# Create startup script
cat > start_stream.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 enhanced_server.py
EOF

chmod +x start_stream.sh

# Create stop script
cat > stop_stream.sh << 'EOF'
#!/bin/bash
sudo systemctl stop webrtc_stream.service
EOF

chmod +x stop_stream.sh

# Create camera troubleshooting script
cat > camera_test.sh << 'EOF'
#!/bin/bash
echo "=================================================="
echo "Pi Camera Test & Troubleshooting"
echo "=================================================="
echo "This script will help you diagnose camera issues."
echo ""
echo "1. Checking hardware detection with vcgencmd..."
vcgencmd get_camera
echo ""
echo "2. Checking for /dev/video devices..."
ls /dev/video*
echo ""
echo "3. Testing with rpicam-hello (for libcamera)..."
echo "   This command should show a preview for 5 seconds."
rpicam-hello -t 5000
echo ""
echo "If tests fail, check your camera's physical connection."
EOF

chmod +x camera_test.sh

print_section "Installation Complete!"

print_status "All dependencies have been installed successfully!"
echo ""
echo "Next steps:"
echo "1. Reboot your Pi to apply camera settings:"
echo "   ${GREEN}sudo reboot${NC}"
echo ""
echo "2. After reboot, start the stream:"
echo "   ${GREEN}./start_stream.sh${NC}"
echo ""
echo "   Or start as a service:"
echo "   ${GREEN}sudo systemctl start webrtc_stream.service${NC}"
echo ""
echo "3. Open a web browser and navigate to:"
echo "   ${GREEN}http://[PI_IP_ADDRESS]:8080${NC}"
echo ""
echo "4. Click 'Start Stream' to begin streaming!"

echo ""
echo "Useful commands:"
echo "  - Start manually: ${GREEN}./start_stream.sh${NC}"
echo "  - Stop service: ${GREEN}./stop_stream.sh${NC}"
echo "  - Check service status: ${GREEN}sudo systemctl status webrtc_stream.service${NC}"
echo "  - View logs: ${GREEN}sudo journalctl -u webrtc_stream.service -f${NC}"
echo "  - Test camera: ${GREEN}./camera_test.sh${NC}"

echo ""
print_warning "If camera issues persist after reboot, run: ./camera_test.sh"

# Display current IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ ! -z "$IP_ADDRESS" ]; then
    echo ""
    print_status "Your Pi's IP address appears to be: ${GREEN}$IP_ADDRESS${NC}"
    print_status "Access the stream at: ${GREEN}http://$IP_ADDRESS:8080${NC}"
fi

echo ""
print_status "Setup complete! Please reboot to ensure all changes take effect."
