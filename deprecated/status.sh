#!/bin/bash

# System status and diagnostics for WebRTC camera streaming

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}WebRTC Camera System Status${NC}"
echo "=================================="

# Check system info
echo -e "\n${GREEN}System Information${NC}"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Uptime: $(uptime -p)"

# Check camera
echo -e "\n${GREEN}Camera Status${NC}"
if [ -e /dev/video0 ]; then
    echo "Camera device detected: /dev/video0"
    
    # Test camera access
    if python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera test:', 'PASS' if cap.isOpened() else 'FAIL'); cap.release()" 2>/dev/null | grep -q "PASS"; then
        echo "Camera accessible"
    else
        echo "Camera not accessible"
    fi
else
    echo "No camera device found"
fi

# Check camera configuration
if grep -q "start_x=1" /boot/config.txt 2>/dev/null; then
    echo "Camera enabled in config.txt"
else
    echo "Camera not enabled in config.txt"
fi

# Check GPU memory
GPU_MEM=$(vcgencmd get_config gpu_mem 2>/dev/null | cut -d'=' -f2)
if [ ! -z "$GPU_MEM" ]; then
    echo "GPU Memory: ${GPU_MEM}MB"
    if [ "$GPU_MEM" -ge 128 ]; then
        echo "GPU memory sufficient"
    else
        echo "GPU memory may be insufficient (recommend 128MB+)"
    fi
fi

# Check service status
echo -e "\n${GREEN}Service Status${NC}"
if systemctl is-active --quiet webrtc-camera.service; then
    echo "WebRTC service is running"
    echo "Service uptime: $(systemctl show webrtc-camera.service --property=ActiveEnterTimestamp --value | xargs -I {} date -d {} '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'Unknown')"
else
    echo "WebRTC service is not running"
fi

if systemctl is-enabled --quiet webrtc-camera.service; then
    echo "Service enabled for auto-start"
else
    echo "Service not enabled for auto-start"
fi

# Check processes
echo -e "\n${GREEN}Running Processes${NC}"
PROCS=$(pgrep -f "webrtc_server.py\|enhanced_server.py")
if [ ! -z "$PROCS" ]; then
    echo "WebRTC processes running:"
    echo "$PROCS" | xargs ps -p | tail -n +2
else
    echo "No WebRTC processes found"
fi

# Check network
echo -e "\n${GREEN}Network Status${NC}"
if ss -tlnp | grep -q ":8080"; then
    echo "Server listening on port 8080"
    echo "Access URL: http://$(hostname -I | awk '{print $1}'):8080"
else
    echo "Server not listening on port 8080"
fi

# Check Python environment
echo -e "\n${GREEN}Python Environment${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment exists"
    source venv/bin/activate
    
    # Check key packages
    for pkg in aiortc aiohttp opencv-python numpy av; do
        if pip list | grep -q "^$pkg "; then
            VERSION=$(pip list | grep "^$pkg " | awk '{print $2}')
            echo "$pkg $VERSION"
        else
            echo "$pkg not installed"
        fi
    done
    
    deactivate
else
    echo "Virtual environment not found"
fi

# Check system resources
echo -e "\n${GREEN}System Resources${NC}"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{print $5}')"

# Check temperature (Raspberry Pi)
if command -v vcgencmd >/dev/null 2>&1; then
    TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2 | cut -d"'" -f1)
    if [ ! -z "$TEMP" ]; then
        echo "Temperature: ${TEMP}°C"
        if (( $(echo "$TEMP > 70" | bc -l) )); then
            echo -e "${RED}High temperature warning!${NC}"
        fi
    fi
fi

# Check recent logs
echo -e "\n${GREEN}Recent Logs (last 10 lines)${NC}"
if systemctl list-units --type=service | grep -q webrtc-camera; then
    sudo journalctl -u webrtc-camera.service --no-pager -n 10 2>/dev/null || echo "No logs available"
else
    echo "Service not found"
fi

echo -e "\n${GREEN}Status check complete${NC}"
