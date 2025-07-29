#!/bin/bash

# WebRTC Camera Streaming Setup Script for Raspberry Pi Zero
# This script installs all required packages and dependencies

set -e  # Exit on any error

echo "=================================================="
echo "Pi Zero WebRTC Camera Setup Script"
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
    python3-dev \
    python3-venv \
    git \
    build-essential \
    cmake \
    pkg-config \
    libjpeg-dev \
    libtiff5-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    libssl-dev \
    libffi-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev

print_section "Camera Configuration"

# Enable camera module
print_status "Enabling camera module..."
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
    print_status "Camera module enabled in config.txt"
else
    print_status "Camera module already enabled"
fi

# Set GPU memory split for camera
if ! grep -q "gpu_mem=" /boot/config.txt; then
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    print_status "GPU memory set to 128MB"
elif ! grep -q "gpu_mem=128" /boot/config.txt; then
    sudo sed -i 's/gpu_mem=.*/gpu_mem=128/' /boot/config.txt
    print_status "GPU memory updated to 128MB"
fi

# Enable camera interface
print_status "Enabling camera interface..."
sudo raspi-config nonint do_camera 0

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
aiortc==1.6.0
aiohttp==3.9.1
opencv-python==4.8.1.78
numpy==1.24.3
av==10.0.0

# Additional utilities
psutil==5.9.6
uvloop==0.19.0

# For better performance on ARM
cffi==1.16.0
cryptography==41.0.8
EOF

# Install Python packages
print_status "Installing Python packages (this may take a while on Pi Zero)..."
pip install -r requirements.txt

print_section "OpenCV Optimization"

# For Pi Zero, we might need to use a pre-compiled OpenCV
if grep -q "Pi Zero" /proc/cpuinfo; then
    print_warning "Detected Pi Zero - installing optimized OpenCV..."
    
    # Remove pip-installed opencv and install optimized version
    pip uninstall -y opencv-python
    
    # Install pre-compiled OpenCV for Pi Zero
    sudo apt-get install -y python3-opencv
    
    # Create symlink for virtual environment
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
    sudo ln -sf /usr/lib/python3/dist-packages/cv2 "$SITE_PACKAGES/"
    
    print_status "Installed optimized OpenCV for Pi Zero"
fi

print_section "Camera Testing"

print_status "Testing camera functionality..."
python3 -c "
import cv2
import sys

try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print('Camera test successful!')
            print(f'Frame shape: {frame.shape}')
        else:
            print('Camera opened but could not capture frame')
            sys.exit(1)
        cap.release()
    else:
        print('Could not open camera')
        sys.exit(1)
except Exception as e:
    print(f'Camera test failed: {e}')
    sys.exit(1)
"

print_section "Service Configuration"

# Create systemd service file
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/webrtc-camera.service > /dev/null << EOF
[Unit]
Description=WebRTC Camera Stream
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python webrtc_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable webrtc-camera.service

print_section "Performance Optimization"

# Set up performance optimizations for Pi Zero
print_status "Applying performance optimizations..."

# GPU memory split optimization
if ! grep -q "gpu_mem_256=128" /boot/config.txt; then
    echo "gpu_mem_256=128" | sudo tee -a /boot/config.txt
fi

if ! grep -q "gpu_mem_512=128" /boot/config.txt; then
    echo "gpu_mem_512=128" | sudo tee -a /boot/config.txt
fi

# Camera optimizations
if ! grep -q "disable_camera_led=1" /boot/config.txt; then
    echo "disable_camera_led=1" | sudo tee -a /boot/config.txt
fi

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

# Create convenient startup script
cat > start_stream.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python webrtc_server.py
EOF

chmod +x start_stream.sh

# Create stop script
cat > stop_stream.sh << 'EOF'
#!/bin/bash
sudo systemctl stop webrtc-camera.service
EOF

chmod +x stop_stream.sh

print_section "Installation Complete!"

print_status "All dependencies have been installed successfully!"
echo ""
echo "Next steps:"
echo "1. Reboot your Pi Zero to apply camera settings:"
echo "   ${GREEN}sudo reboot${NC}"
echo ""
echo "2. After reboot, start the stream:"
echo "   ${GREEN}./start_stream.sh${NC}"
echo ""
echo "   Or start as a service:"
echo "   ${GREEN}sudo systemctl start webrtc-camera.service${NC}"
echo ""
echo "3. Open a web browser and navigate to:"
echo "   ${GREEN}http://[PI_IP_ADDRESS]:8080${NC}"
echo ""
echo "4. Click 'Start Stream' to begin streaming!"
echo ""
echo "Useful commands:"
echo "  - Check service status: ${GREEN}sudo systemctl status webrtc-camera.service${NC}"
echo "  - View logs: ${GREEN}sudo journalctl -u webrtc-camera.service -f${NC}"
echo "  - Stop service: ${GREEN}sudo systemctl stop webrtc-camera.service${NC}"
echo ""
print_warning "Note: The first run may take longer as aiortc compiles native modules."
print_warning "For Pi Zero, expect initial compilation to take 10-15 minutes."

# Display current IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [ ! -z "$IP_ADDRESS" ]; then
    echo ""
    print_status "Your Pi's IP address appears to be: ${GREEN}$IP_ADDRESS${NC}"
    print_status "Access the stream at: ${GREEN}http://$IP_ADDRESS:8080${NC}"
fi

echo ""
print_status "Setup complete! Please reboot to ensure all changes take effect."
