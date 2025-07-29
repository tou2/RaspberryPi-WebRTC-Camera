#!/bin/bash

# Comprehensive Camera Test and Troubleshooting Script
# For Raspberry Pi WebRTC Camera Streaming

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

echo "=================================================="
echo "Raspberry Pi Camera Test & Troubleshooting"
echo "=================================================="

print_section "1. System Information"
echo "Hostname: $(hostname)"
echo "Pi Model: $(grep 'Raspberry Pi' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo ""

print_section "2. Camera Device Detection"
print_status "Checking for camera devices..."

# Check for video devices
if ls /dev/video* >/dev/null 2>&1; then
    echo "Camera devices found:"
    ls -la /dev/video*
    echo ""
    
    # Check permissions
    for device in /dev/video*; do
        if [ -r "$device" ] && [ -w "$device" ]; then
            echo "✓ $device - readable and writable"
        else
            echo "✗ $device - permission issues"
            echo "  Try: sudo usermod -a -G video $USER"
        fi
    done
else
    print_error "No camera devices found in /dev/"
    echo "This usually means:"
    echo "1. Camera is not connected properly"
    echo "2. Camera module is not loaded"
    echo "3. Camera is not enabled in raspi-config"
fi
echo ""

print_section "3. Camera Hardware Detection"
print_status "Checking camera with vcgencmd..."

if command -v vcgencmd >/dev/null 2>&1; then
    CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "Camera status: $CAMERA_STATUS"
        
        if echo "$CAMERA_STATUS" | grep -q "supported=1"; then
            echo "✓ Camera is supported"
        else
            echo "✗ Camera not supported"
        fi
        
        if echo "$CAMERA_STATUS" | grep -q "detected=1"; then
            echo "✓ Camera is detected"
        else
            echo "✗ Camera not detected"
            print_error "Camera hardware not detected!"
            echo "Check:"
            echo "1. Camera cable connection"
            echo "2. Camera cable orientation"
            echo "3. Camera module is properly seated"
        fi
    else
        print_error "vcgencmd failed to check camera"
    fi
else
    print_warning "vcgencmd not available (not on Raspberry Pi?)"
fi
echo ""

print_section "4. Boot Configuration Check"
print_status "Checking /boot/config.txt settings..."

# Check camera enable - new cameras use camera_auto_detect
if grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null; then
    echo "✓ Camera auto-detect enabled (recommended for new cameras)"
elif grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    echo "✓ Legacy camera enabled (start_x=1)"
    print_warning "For new camera modules, consider using camera_auto_detect=1 instead"
else
    print_error "Camera not enabled in config.txt"
    echo "For new camera modules, add: camera_auto_detect=1"
    echo "Or run: sudo raspi-config -> Interface Options -> Camera -> Enable"
fi

# Check GPU memory
GPU_MEM=$(grep "^gpu_mem=" /boot/config.txt 2>/dev/null | cut -d'=' -f2)
if [ ! -z "$GPU_MEM" ]; then
    echo "GPU Memory: ${GPU_MEM}MB"
    if [ "$GPU_MEM" -ge 128 ]; then
        echo "✓ GPU memory sufficient for camera"
    else
        print_warning "GPU memory may be insufficient (recommended: 128MB+)"
        echo "Add to /boot/config.txt: gpu_mem=128"
    fi
else
    print_warning "GPU memory not explicitly set"
fi
echo ""

print_section "5. Kernel Module Check"
print_status "Checking loaded camera modules..."

# Check for camera modules - new cameras use libcamera
if lsmod | grep -q bcm2835_v4l2; then
    echo "✓ bcm2835_v4l2 module loaded (legacy camera)"
elif lsmod | grep -q bcm2835-v4l2; then
    echo "✓ bcm2835-v4l2 module loaded (legacy camera)"
else
    print_warning "Legacy camera V4L2 module not loaded"
    echo "This is normal for new camera modules (Camera Module 3+)"
    echo "New cameras use libcamera instead of V4L2"
fi

# Check for libcamera support (new cameras)
if command -v libcamera-hello >/dev/null 2>&1; then
    echo "✓ libcamera tools available (supports new cameras)"
else
    print_warning "libcamera tools not found"
    echo "Install with: sudo apt-get install -y libcamera-apps"
fi

# Try to load legacy module anyway (for compatibility)
if ! lsmod | grep -q bcm2835; then
    echo "Trying to load legacy camera module for compatibility..."
    if sudo modprobe bcm2835-v4l2 2>/dev/null; then
        echo "✓ Successfully loaded bcm2835-v4l2 module"
        sleep 2
    else
        echo "Legacy camera module not available (normal for new cameras)"
    fi
fi

# Check other camera-related modules
echo ""
echo "Camera-related modules:"
lsmod | grep -E "(bcm2835|camera|video)" || echo "No legacy camera modules found (normal for new cameras)"
echo ""

print_section "6. Hardware Test (libcamera & raspistill)"
print_status "Testing camera with available tools..."

# Test with libcamera first (for new cameras)
if command -v libcamera-hello >/dev/null 2>&1; then
    echo "Testing with libcamera (recommended for new cameras)..."
    if timeout 10 libcamera-hello --timeout 2000 --nopreview 2>/tmp/libcamera_error.log; then
        echo "✓ libcamera test successful!"
    else
        print_error "libcamera test failed"
        echo "Error log:"
        cat /tmp/libcamera_error.log 2>/dev/null || echo "No error log available"
    fi
    rm -f /tmp/libcamera_error.log
    echo ""
fi

# Test with libcamera-still (for new cameras)
if command -v libcamera-still >/dev/null 2>&1; then
    echo "Taking test photo with libcamera-still..."
    if timeout 15 libcamera-still -t 2000 -o /tmp/camera_libcamera_test.jpg --nopreview 2>/tmp/libcamera_still_error.log; then
        if [ -f /tmp/camera_libcamera_test.jpg ] && [ -s /tmp/camera_libcamera_test.jpg ]; then
            echo "✓ libcamera-still test successful!"
            echo "Test image size: $(stat -c%s /tmp/camera_libcamera_test.jpg) bytes"
            rm -f /tmp/camera_libcamera_test.jpg
        else
            print_error "libcamera-still test failed - no image created"
        fi
    else
        print_error "libcamera-still command failed"
        echo "Error log:"
        cat /tmp/libcamera_still_error.log 2>/dev/null || echo "No error log available"
    fi
    rm -f /tmp/libcamera_still_error.log
    echo ""
fi

# Test with raspistill (legacy cameras)
if command -v raspistill >/dev/null 2>&1; then
    echo "Testing with raspistill (legacy camera support)..."
    if timeout 15 raspistill -t 1000 -o /tmp/camera_hardware_test.jpg -v 2>/tmp/raspistill_error.log; then
        if [ -f /tmp/camera_hardware_test.jpg ] && [ -s /tmp/camera_hardware_test.jpg ]; then
            echo "✓ raspistill test successful!"
            echo "Test image size: $(stat -c%s /tmp/camera_hardware_test.jpg) bytes"
            rm -f /tmp/camera_hardware_test.jpg
        else
            print_error "raspistill test failed - no image created"
            echo "Error log:"
            cat /tmp/raspistill_error.log 2>/dev/null || echo "No error log available"
        fi
    else
        print_warning "raspistill command failed (normal for new cameras)"
        echo "New camera modules typically require libcamera tools"
    fi
    rm -f /tmp/raspistill_error.log
else
    print_warning "raspistill not available"
    echo "Install with: sudo apt-get install -y raspberrypi-utils"
    echo "Note: New cameras work better with libcamera tools"
fi
echo ""

print_section "7. OpenCV Camera Test"
print_status "Testing camera with OpenCV..."

# Check if Python3 and OpenCV are available
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import sys
import time

try:
    import cv2
    print('OpenCV version:', cv2.__version__)
    
    # Test multiple camera indices
    cameras_found = []
    
    for camera_idx in range(3):  # Test indices 0, 1, 2
        print(f'\\nTesting camera index {camera_idx}...')
        cap = cv2.VideoCapture(camera_idx)
        
        if cap.isOpened():
            # Get camera properties
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f'  Camera {camera_idx} opened')
            print(f'  Default resolution: {int(width)}x{int(height)}')
            print(f'  Default FPS: {fps}')
            
            # Try to set properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 15)
            
            # Wait for camera to initialize
            time.sleep(2)
            
            # Try to capture frames
            success_count = 0
            for attempt in range(5):
                ret, frame = cap.read()
                if ret and frame is not None:
                    success_count += 1
                    if attempt == 0:  # Print details for first successful frame
                        print(f'  ✓ Frame captured: {frame.shape}')
                        print(f'  Frame data type: {frame.dtype}')
                        print(f'  Frame size: {frame.nbytes} bytes')
                else:
                    print(f'  Attempt {attempt + 1}: No frame captured')
                time.sleep(0.5)
            
            if success_count > 0:
                print(f'  ✓ Camera {camera_idx} working! ({success_count}/5 frames captured)')
                cameras_found.append(camera_idx)
            else:
                print(f'  ✗ Camera {camera_idx} opened but no frames captured')
            
            cap.release()
        else:
            print(f'  ✗ Camera {camera_idx} could not be opened')
    
    if cameras_found:
        print(f'\\n✓ Working cameras found at indices: {cameras_found}')
        print('Camera test PASSED')
    else:
        print('\\n✗ No working cameras found')
        print('Camera test FAILED')
        
except ImportError:
    print('✗ OpenCV not installed')
    print('Install with: pip install opencv-python')
    sys.exit(1)
except Exception as e:
    print(f'✗ OpenCV test failed: {e}')
    sys.exit(1)
"
else
    print_error "Python3 not available"
fi
echo ""

print_section "8. Process Check"
print_status "Checking for processes using camera..."

# Check for processes using video devices
for device in /dev/video*; do
    if [ -e "$device" ]; then
        PROCS=$(lsof "$device" 2>/dev/null | tail -n +2)
        if [ ! -z "$PROCS" ]; then
            echo "Processes using $device:"
            echo "$PROCS"
        else
            echo "✓ $device is available (not in use)"
        fi
    fi
done
echo ""

print_section "9. System Resources"
print_status "Checking system resources..."

# Memory
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')
echo "Memory usage: $MEMORY_USAGE"

# Temperature (if available)
if command -v vcgencmd >/dev/null 2>&1; then
    TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2)
    if [ ! -z "$TEMP" ]; then
        echo "CPU temperature: $TEMP"
        TEMP_NUM=$(echo "$TEMP" | cut -d"'" -f1)
        if (( $(echo "$TEMP_NUM > 70" | bc -l) )); then
            print_warning "High temperature detected!"
        fi
    fi
fi

# Disk space
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')
echo "Disk usage: $DISK_USAGE"
echo ""

print_section "10. Quick Fixes"
print_status "Applying common fixes..."

# Install libcamera tools if missing (for new cameras)
if ! command -v libcamera-hello >/dev/null 2>&1; then
    echo "Installing libcamera tools for new camera support..."
    if sudo apt-get update && sudo apt-get install -y libcamera-apps; then
        echo "✓ libcamera tools installed"
    else
        print_warning "Failed to install libcamera tools"
    fi
fi

# Try loading camera module (for legacy compatibility)
echo "Loading legacy camera module for compatibility..."
sudo modprobe bcm2835-v4l2 2>/dev/null && echo "✓ Legacy module loaded" || echo "Legacy module not available (normal for new cameras)"

# Check and fix permissions
if [ -e /dev/video0 ]; then
    if [ ! -r /dev/video0 ] || [ ! -w /dev/video0 ]; then
        echo "Fixing camera permissions..."
        sudo usermod -a -G video $USER && echo "✓ Added user to video group" || echo "✗ Failed to add to video group"
        echo "Note: You may need to log out and back in for group changes to take effect"
    fi
fi
echo ""

print_section "Troubleshooting Summary"

echo "If camera is still not working, try these steps:"
echo ""
echo "1. Hardware checks:"
echo "   - Ensure camera cable is properly connected"
echo "   - Check cable orientation (blue side towards Ethernet port on Pi)"
echo "   - Try a different camera cable"
echo "   - Test camera on a different Pi (if available)"
echo ""
echo "2. Software configuration:"
echo "   sudo raspi-config"
echo "   -> Interface Options -> Camera -> Enable"
echo "   -> Advanced Options -> Memory Split -> 128"
echo ""
echo "   For new cameras (Camera Module 3+), ensure:"
echo "   /boot/config.txt contains: camera_auto_detect=1"
echo ""
echo "3. Install required tools:"
echo "   sudo apt-get update"
echo "   sudo apt-get install -y libcamera-apps"
echo ""
echo "4. Manual module loading (legacy cameras):"
echo "   sudo modprobe bcm2835-v4l2"
echo "   echo 'bcm2835-v4l2' | sudo tee -a /etc/modules"
echo ""
echo "5. Reboot and test:"
echo "   sudo reboot"
echo "   ./camera_test.sh"
echo ""
echo "6. Check for hardware issues:"
echo "   vcgencmd get_camera"
echo "   libcamera-hello --timeout 2000 (for new cameras)"
echo "   raspistill -t 1000 -o test.jpg (for legacy cameras)"
echo ""

# Final status
if [ -e /dev/video0 ]; then
    if command -v vcgencmd >/dev/null 2>&1; then
        CAMERA_STATUS=$(vcgencmd get_camera 2>/dev/null)
        if echo "$CAMERA_STATUS" | grep -q "detected=1"; then
            print_status "Camera hardware appears to be working!"
            echo "You can now try running the WebRTC server:"
            echo "  ./start_stream.sh"
        else
            print_error "Camera hardware issues detected"
            echo "Please check the troubleshooting steps above"
        fi
    else
        print_status "Camera device exists, try running the WebRTC server"
    fi
else
    print_error "Camera device not found"
    echo "Camera may not be properly enabled or connected"
fi

echo ""
echo "Test completed!"
