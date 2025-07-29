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

# Enable camera module - prioritize new camera support
print_status "Configuring camera module..."

# For new cameras (Camera Module 3+), use camera_auto_detect
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    print_status "Camera auto-detect enabled (recommended for new cameras)"
else
    print_status "Camera auto-detect already enabled"
fi

# Legacy camera support
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
    print_status "Legacy camera support enabled"
else
    print_status "Legacy camera support already enabled"
fi

# Set GPU memory split for camera
if ! grep -q "gpu_mem=" /boot/config.txt; then
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    print_status "GPU memory set to 128MB"
elif ! grep -q "gpu_mem=128" /boot/config.txt; then
    sudo sed -i 's/gpu_mem=.*/gpu_mem=128/' /boot/config.txt
    print_status "GPU memory updated to 128MB"
fi

# Enable camera interface (try multiple methods)
print_status "Enabling camera interface..."

# Method 1: Try raspi-config (may not work on newer OS versions)
if sudo raspi-config nonint do_camera 0 2>/dev/null; then
    print_status "Camera enabled via raspi-config"
else
    print_warning "raspi-config camera option not available (normal on newer OS)"
fi

# Method 2: Ensure camera is properly configured in boot files
print_status "Configuring camera in boot configuration..."

# For newer Pi OS, ensure dtparam=camera=on is set
if ! grep -q "dtparam=camera=on" /boot/config.txt; then
    echo "dtparam=camera=on" | sudo tee -a /boot/config.txt
    print_status "Added dtparam=camera=on to boot config"
fi

# Install libcamera tools for new camera support
print_status "Installing libcamera tools for new camera modules..."
sudo apt-get install -y libcamera-apps libcamera-dev

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
aiortc>=1.6.0
aiohttp>=3.9.0
opencv-python>=4.8.0
numpy>=1.24.0
av>=10.0.0

# Additional utilities
psutil>=5.9.0
uvloop>=0.19.0

# System dependencies (let pip choose compatible versions)
cffi
cryptography
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

# Check camera with vcgencmd first
print_status "Checking camera with vcgencmd..."
CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null || echo "supported=0 detected=0")
print_status "Camera status: $CAMERA_STATUS"

if echo "$CAMERA_STATUS" | grep -q "detected=0"; then
    print_error "Camera not detected by system!"
    print_status "Please check:"
    print_status "1. Camera cable is properly connected"
    print_status "2. Camera cable orientation (connector facing away from ethernet port)"
    print_status "3. Camera is properly seated in connector"
    print_warning "Will continue installation - camera may work after reboot"
fi

# Test with libcamera first (for new cameras)
if command -v libcamera-hello >/dev/null 2>&1; then
    print_status "Testing with libcamera (recommended for new cameras)..."
    if timeout 10 libcamera-hello --timeout 2000 --nopreview 2>/dev/null; then
        print_status "Camera test successful with libcamera!"
    else
        print_warning "libcamera test failed - this may be normal during installation"
    fi
else
    print_warning "libcamera tools not available - installing now..."
    sudo apt-get install -y libcamera-apps
fi

# Test with raspistill (for legacy cameras)
if command -v raspistill >/dev/null 2>&1; then
    print_status "Testing camera with raspistill (legacy support)..."
    if timeout 10 raspistill -t 1 -o /tmp/test.jpg >/dev/null 2>&1; then
        print_status "Camera hardware test successful!"
        rm -f /tmp/test.jpg
    else
        print_warning "raspistill test failed (normal for new cameras)"
        print_status "Trying to load camera module..."
        sudo modprobe bcm2835-v4l2 2>/dev/null || true
        sleep 2
    fi
else
    print_warning "raspistill not available (normal for minimal OS installations)"
fi

# Check if camera device exists
if [ ! -e /dev/video0 ]; then
    print_warning "Camera device /dev/video0 not found!"
    print_status "This is normal during installation - device will appear after reboot"
    print_status "If camera still doesn't work after reboot:"
    print_status "1. Run: ./camera_test.sh"
    print_status "2. Check cable connection"
    print_status "3. Verify camera is enabled in boot config"
else
    print_status "Camera device /dev/video0 found"
    
    # Test with OpenCV if available
    if python3 -c "import cv2" 2>/dev/null; then
        print_status "Testing camera with OpenCV..."
        python3 -c "
import cv2
import sys
import time

try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        time.sleep(2)
        ret, frame = cap.read()
        if ret and frame is not None:
            print('Camera test successful with OpenCV!')
            print(f'Frame shape: {frame.shape}')
        else:
            print('Camera opened but no frame captured')
        cap.release()
    else:
        print('Camera could not be opened with OpenCV')
except Exception as e:
    print(f'Camera test failed: {e}')
" 2>/dev/null || print_warning "OpenCV camera test failed - may work after reboot"
    fi
fi

print_warning "Camera functionality will be fully verified after reboot"

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

# Create camera troubleshooting script
cat > camera_test.sh << 'EOF'
#!/bin/bash

# Comprehensive Camera Test and Troubleshooting Script
# For new and legacy Raspberry Pi cameras

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_section() { echo -e "\n${BLUE}=== $1 ===${NC}"; }

echo "=================================================="
echo "Pi Camera Test & Troubleshooting"
echo "=================================================="

print_section "1. System Information"
echo "Pi Model: $(grep 'Raspberry Pi' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo ""

print_section "2. Boot Configuration Check"
print_status "Checking /boot/config.txt settings..."

# Check various camera configurations
if grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null; then
    echo "✓ camera_auto_detect=1 (recommended for new cameras)"
elif grep -q "^dtparam=camera=on" /boot/config.txt 2>/dev/null; then
    echo "✓ dtparam=camera=on (alternative method)"
elif grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    echo "✓ start_x=1 (legacy camera support)"
else
    print_error "Camera not enabled in boot config!"
    echo "Add one of these to /boot/config.txt:"
    echo "  camera_auto_detect=1  (for new cameras)"
    echo "  dtparam=camera=on     (alternative)"
    echo "  start_x=1             (legacy cameras)"
fi

# Check GPU memory
GPU_MEM=$(grep "^gpu_mem=" /boot/config.txt 2>/dev/null | cut -d'=' -f2)
if [ ! -z "$GPU_MEM" ]; then
    echo "GPU Memory: ${GPU_MEM}MB"
    if [ "$GPU_MEM" -ge 128 ]; then
        echo "✓ GPU memory sufficient"
    else
        print_warning "GPU memory low (recommended: 128MB+)"
    fi
else
    print_warning "GPU memory not set (add gpu_mem=128 to /boot/config.txt)"
fi
echo ""

print_section "3. Hardware Detection"
print_status "Checking camera with vcgencmd..."
if command -v vcgencmd >/dev/null 2>&1; then
    CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null)
    echo "Camera status: $CAMERA_STATUS"
    
    if echo "$CAMERA_STATUS" | grep -q "detected=1"; then
        echo "✓ Camera detected by firmware"
    else
        print_error "Camera not detected by firmware!"
        echo "Check:"
        echo "1. Camera cable connection"
        echo "2. Cable orientation (connector away from ethernet)"
        echo "3. Camera module properly seated"
    fi
else
    print_warning "vcgencmd not available"
fi
echo ""

print_section "4. Camera Device Check"
print_status "Checking for camera devices..."
if ls /dev/video* >/dev/null 2>&1; then
    echo "Camera devices found:"
    ls -la /dev/video*
    
    # Check permissions
    for device in /dev/video*; do
        if [ -r "$device" ] && [ -w "$device" ]; then
            echo "✓ $device - accessible"
        else
            echo "✗ $device - permission issues"
            echo "  Fix: sudo usermod -a -G video $USER"
        fi
    done
else
    print_error "No video devices found!"
    echo "Try:"
    echo "1. sudo modprobe bcm2835-v4l2"
    echo "2. Reboot after enabling camera"
fi
echo ""

print_section "5. libcamera Test (New Cameras)"
if command -v libcamera-hello >/dev/null 2>&1; then
    print_status "Testing with libcamera-hello..."
    if timeout 10 libcamera-hello --timeout 2000 --nopreview 2>/dev/null; then
        echo "✓ libcamera test successful!"
    else
        print_error "libcamera test failed"
    fi
    
    print_status "Testing with libcamera-still..."
    if timeout 10 libcamera-still -t 2000 -o /tmp/test_libcamera.jpg --nopreview 2>/dev/null; then
        if [ -f /tmp/test_libcamera.jpg ] && [ -s /tmp/test_libcamera.jpg ]; then
            echo "✓ libcamera-still test successful!"
            echo "  Image size: $(stat -c%s /tmp/test_libcamera.jpg) bytes"
            rm -f /tmp/test_libcamera.jpg
        else
            print_error "libcamera-still failed to create image"
        fi
    else
        print_error "libcamera-still test failed"
    fi
else
    print_warning "libcamera tools not installed"
    echo "Install with: sudo apt-get install -y libcamera-apps"
fi
echo ""

print_section "6. raspistill Test (Legacy Cameras)"
if command -v raspistill >/dev/null 2>&1; then
    print_status "Testing with raspistill..."
    if timeout 10 raspistill -t 1000 -o /tmp/test_raspistill.jpg 2>/dev/null; then
        if [ -f /tmp/test_raspistill.jpg ] && [ -s /tmp/test_raspistill.jpg ]; then
            echo "✓ raspistill test successful!"
            echo "  Image size: $(stat -c%s /tmp/test_raspistill.jpg) bytes"
            rm -f /tmp/test_raspistill.jpg
        else
            print_error "raspistill failed to create image"
        fi
    else
        print_warning "raspistill test failed (normal for new cameras)"
    fi
else
    print_warning "raspistill not available"
    echo "Install with: sudo apt-get install -y raspberrypi-utils"
fi
echo ""

print_section "7. OpenCV Test"
if python3 -c "import cv2" 2>/dev/null; then
    print_status "Testing with OpenCV..."
    python3 -c "
import cv2
import time

for idx in [0, 1, 2]:
    print(f'Testing camera index {idx}...')
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        time.sleep(2)
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f'✓ Camera {idx} working - Shape: {frame.shape}')
        else:
            print(f'✗ Camera {idx} opened but no frame')
        cap.release()
    else:
        print(f'✗ Camera {idx} could not open')
    print()
"
else
    print_warning "OpenCV not available"
    echo "Install with: pip install opencv-python"
fi

print_section "8. Module Loading"
print_status "Checking and loading camera modules..."
if lsmod | grep -q bcm2835; then
    echo "✓ Camera modules loaded:"
    lsmod | grep bcm2835
else
    print_warning "No camera modules loaded, trying to load..."
    sudo modprobe bcm2835-v4l2 2>/dev/null && echo "✓ Module loaded" || echo "✗ Module load failed"
fi
echo ""

print_section "Troubleshooting Recommendations"
echo ""
echo "If camera is not working:"
echo ""
echo "1. HARDWARE CHECK:"
echo "   - Ensure camera cable is fully inserted"
echo "   - Check cable orientation (blue side towards ethernet on most models)"
echo "   - Try a different camera cable if available"
echo ""
echo "2. CONFIGURATION:"
echo "   - Add to /boot/config.txt: camera_auto_detect=1"
echo "   - Add to /boot/config.txt: gpu_mem=128"
echo "   - Reboot after changes: sudo reboot"
echo ""
echo "3. SOFTWARE:"
echo "   - Install libcamera: sudo apt-get install -y libcamera-apps"
echo "   - Load module: sudo modprobe bcm2835-v4l2"
echo "   - Check permissions: sudo usermod -a -G video \$USER"
echo ""
echo "4. TEST COMMANDS:"
echo "   - vcgencmd get_camera"
echo "   - libcamera-hello --timeout 2000"
echo "   - ls /dev/video*"
echo ""

# Final status
if command -v vcgencmd >/dev/null 2>&1; then
    CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null)
    if echo "$CAMERA_STATUS" | grep -q "detected=1"; then
        print_status "Camera appears to be detected - try running the WebRTC server!"
    else
        print_error "Camera hardware issues - check connections and reboot"
    fi
fi

echo "Test completed!"
EOF

chmod +x camera_test.sh

print_section "Docker Installation (Optional)"

# Ask user if they want to install Docker
echo ""
read -p "Do you want to install Docker for container deployment? (y/N): " install_docker

if [[ $install_docker =~ ^[Yy]$ ]]; then
    print_status "Installing Docker..."
    
    # Install Docker using the official script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Install Docker Compose
    print_status "Installing Docker Compose..."
    sudo apt-get install -y docker-compose
    
    # Enable Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Create docker-compose.yml if it doesn't exist
    if [ ! -f docker-compose.yml ]; then
        print_status "Creating docker-compose.yml..."
        cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  webrtc-camera:
    build: .
    ports:
      - "8080:8080"
    devices:
      - /dev/video0:/dev/video0
    volumes:
      - ./config.ini:/app/config.ini:ro
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    privileged: true
EOF
    fi
    
    # Create Dockerfile if it doesn't exist
    if [ ! -f Dockerfile ]; then
        print_status "Creating Dockerfile..."
        cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
    libssl-dev \
    libffi-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run the server
CMD ["python", "enhanced_server.py"]
EOF
    fi
    
    print_status "Docker installation complete!"
    print_status "You can now use Docker deployment with:"
    print_status "  docker-compose up --build -d"
    echo ""
    print_warning "Note: You'll need to log out and back in for Docker group membership to take effect."
    echo ""
else
    print_status "Skipping Docker installation."
fi

print_section "Installation Complete!"

print_status "All dependencies have been installed successfully!"
echo ""

if [[ $install_docker =~ ^[Yy]$ ]]; then
    echo "Deployment options:"
    echo ""
    echo "${BLUE}Option 1: Native Python (Recommended for Pi Zero W)${NC}"
    echo "1. Reboot your Pi: ${GREEN}sudo reboot${NC}"
    echo "2. Start the stream: ${GREEN}./start_stream.sh${NC}"
    echo ""
    echo "${BLUE}Option 2: Docker Container${NC}"
    echo "1. Reboot your Pi: ${GREEN}sudo reboot${NC}"
    echo "2. Start with Docker: ${GREEN}docker-compose up --build -d${NC}"
    echo "3. View logs: ${GREEN}docker-compose logs -f${NC}"
    echo ""
    echo "4. Open a web browser and navigate to:"
    echo "   ${GREEN}http://[PI_IP_ADDRESS]:8080${NC}"
    echo ""
    echo "5. Click 'Start Stream' to begin streaming!"
else
    echo "Next steps:"
    echo "1. Reboot your Pi to apply camera settings:"
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
fi

echo ""
echo "Useful commands:"
if [[ $install_docker =~ ^[Yy]$ ]]; then
    echo "  ${BLUE}Native Python:${NC}"
    echo "  - Check service status: ${GREEN}sudo systemctl status webrtc-camera.service${NC}"
    echo "  - View logs: ${GREEN}sudo journalctl -u webrtc-camera.service -f${NC}"
    echo "  - Stop service: ${GREEN}sudo systemctl stop webrtc-camera.service${NC}"
    echo ""
    echo "  ${BLUE}Docker:${NC}"
    echo "  - Start container: ${GREEN}docker-compose up -d${NC}"
    echo "  - View logs: ${GREEN}docker-compose logs -f${NC}"
    echo "  - Stop container: ${GREEN}docker-compose down${NC}"
    echo "  - Rebuild image: ${GREEN}docker-compose up --build -d${NC}"
    echo "  - Container status: ${GREEN}docker-compose ps${NC}"
else
    echo "  - Check service status: ${GREEN}sudo systemctl status webrtc-camera.service${NC}"
    echo "  - View logs: ${GREEN}sudo journalctl -u webrtc-camera.service -f${NC}"
    echo "  - Stop service: ${GREEN}sudo systemctl stop webrtc-camera.service${NC}"
    echo "  - Test camera: ${GREEN}./camera_test.sh${NC}"
fi
echo ""
print_warning "Note: The first run may take longer as aiortc compiles native modules."
print_warning "For Pi Zero, expect initial compilation to take 10-15 minutes."
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
