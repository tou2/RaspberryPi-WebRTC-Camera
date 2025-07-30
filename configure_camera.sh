#!/bin/bash

# Manual Camera Configuration Script
# Use this if raspi-config doesn't have camera option

echo "=================================================="
echo "Manual Camera Configuration"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root."
    exit 1
fi

print_status "Configuring camera manually..."

# Backup config file
sudo cp /boot/config.txt /boot/config.txt.backup
print_status "Backed up config.txt"

# Add camera configuration
print_status "Adding camera configuration to /boot/config.txt..."

# For new cameras (Camera Module 3+)
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    print_status "Added camera_auto_detect=1 (for new cameras)"
fi

# Alternative method
if ! grep -q "dtparam=camera=on" /boot/config.txt; then
    echo "dtparam=camera=on" | sudo tee -a /boot/config.txt
    print_status "Added dtparam=camera=on"
fi

# Legacy support
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
    print_status "Added start_x=1 (legacy support)"
fi

# GPU memory
if ! grep -q "gpu_mem=" /boot/config.txt; then
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    print_status "Set GPU memory to 128MB"
elif ! grep -q "gpu_mem=128" /boot/config.txt; then
    sudo sed -i 's/gpu_mem=.*/gpu_mem=128/' /boot/config.txt
    print_status "Updated GPU memory to 128MB"
fi

# Install required packages
print_status "Installing camera packages..."
sudo apt-get update
sudo apt-get install -y rpicam-apps rpicam-dev

print_status "Configuration complete!"
echo ""
print_warning "IMPORTANT: You must reboot for changes to take effect:"
echo "  sudo reboot"
echo ""
print_status "After reboot, test your camera with:"
echo "  ./camera_test.sh"
echo ""
print_status "Or test manually:"
echo "  vcgencmd get_camera"
echo "  rpicam-hello --timeout 2000"
