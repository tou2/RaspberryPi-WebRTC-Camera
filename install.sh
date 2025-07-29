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

# Enable camera interface
print_status "Enabling camera interface..."
sudo raspi-config nonint do_camera 0

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

# First check if camera device exists
if [ ! -e /dev/video0 ]; then
    print_error "Camera device /dev/video0 not found!"
    print_status "Troubleshooting steps:"
    print_status "1. Check camera connection"
    print_status "2. Run: vcgencmd get_camera"
    print_status "3. Try: sudo modprobe bcm2835-v4l2"
    exit 1
fi

# Check camera with vcgencmd first
print_status "Checking camera with vcgencmd..."
CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null || echo "supported=0 detected=0")
print_status "Camera status: $CAMERA_STATUS"

if echo "$CAMERA_STATUS" | grep -q "detected=0"; then
    print_error "Camera not detected by system!"
    print_status "Please check:"
    print_status "1. Camera cable is properly connected"
    print_status "2. Camera is enabled in raspi-config"
    print_status "3. Reboot after enabling camera"
    exit 1
fi

# Test with raspistill first (more reliable)
print_status "Testing camera with raspistill..."
if timeout 10 raspistill -t 1 -o /tmp/test.jpg >/dev/null 2>&1; then
    print_status "Camera hardware test successful!"
    rm -f /tmp/test.jpg
else
    print_error "Camera hardware test failed!"
    print_status "Trying to load camera module..."
    sudo modprobe bcm2835-v4l2
    sleep 2
fi

# Now test with OpenCV
print_status "Testing camera with OpenCV..."
python3 -c "
import cv2
import sys
import time

try:
    # Try multiple camera indices
    for camera_idx in [0, 1]:
        print(f'Trying camera index {camera_idx}...')
        cap = cv2.VideoCapture(camera_idx)
        
        if cap.isOpened():
            # Set some properties before trying to read
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 15)
            
            # Wait a moment for camera to initialize
            time.sleep(2)
            
            # Try multiple frame captures
            for attempt in range(5):
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f'Camera test successful on index {camera_idx}!')
                    print(f'Frame shape: {frame.shape}')
                    cap.release()
                    sys.exit(0)
                print(f'Attempt {attempt + 1}: No frame captured, retrying...')
                time.sleep(1)
            
            cap.release()
        
    print('ERROR: Could not capture frames from any camera')
    print('Troubleshooting:')
    print('1. Check camera connection')
    print('2. Ensure camera is enabled: sudo raspi-config')
    print('3. Try: sudo modprobe bcm2835-v4l2')
    print('4. Reboot and try again')
    sys.exit(1)
    
except Exception as e:
    print(f'Camera test failed with exception: {e}')
    print('This may be normal during installation - camera will be tested again after reboot')
"

# Don't exit on camera test failure during install - it may work after reboot
if [ $? -ne 0 ]; then
    print_warning "Camera test failed, but continuing installation..."
    print_warning "Camera functionality will be verified after reboot"
fi

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

# Camera troubleshooting script

echo "=== Camera Diagnostics ==="
echo ""

# Check if camera device exists
echo "1. Checking camera device..."
if [ -e /dev/video0 ]; then
    echo "✓ /dev/video0 exists"
    ls -la /dev/video0
else
    echo "✗ /dev/video0 not found"
fi
echo ""

# Check camera status with vcgencmd
echo "2. Checking camera status..."
vcgencmd get_camera 2>/dev/null || echo "vcgencmd not available"
echo ""

# Check if camera module is loaded
echo "3. Checking loaded modules..."
lsmod | grep -i camera || echo "No camera modules loaded"
lsmod | grep bcm2835 || echo "No bcm2835 modules loaded"
echo ""

# Try loading camera module
echo "4. Loading camera module..."
sudo modprobe bcm2835-v4l2 && echo "✓ Module loaded" || echo "✗ Failed to load module"
echo ""

# Test with raspistill
echo "5. Testing with raspistill..."
timeout 10 raspistill -t 1 -o /tmp/camera_test.jpg 2>/dev/null && echo "✓ raspistill test passed" || echo "✗ raspistill test failed"
rm -f /tmp/camera_test.jpg
echo ""

# Test with OpenCV
echo "6. Testing with OpenCV..."
python3 -c "
import cv2
import time

for idx in [0, 1]:
    print(f'Testing camera index {idx}...')
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        time.sleep(2)
        ret, frame = cap.read()
        if ret:
            print(f'✓ Camera {idx} working - Frame shape: {frame.shape}')
        else:
            print(f'✗ Camera {idx} opened but no frame')
        cap.release()
    else:
        print(f'✗ Camera {idx} could not open')
    print()
"

echo "=== Troubleshooting Tips ==="
echo "If camera tests fail:"
echo "1. Check camera cable connection"
echo "2. Enable camera: sudo raspi-config -> Interface Options -> Camera"
echo "3. Reboot after enabling camera"
echo "4. Check /boot/config.txt has: start_x=1 and gpu_mem=128"
echo "5. Try: sudo modprobe bcm2835-v4l2"
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
