#!/bin/bash

# Stop WebRTC camera streaming service and processes

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🛑 Stopping WebRTC Camera Stream${NC}"

# Stop systemd service if running
if systemctl is-active --quiet webrtc-camera.service; then
    echo -e "${YELLOW}📦 Stopping systemd service...${NC}"
    sudo systemctl stop webrtc-camera.service
    echo -e "${GREEN}✅ Service stopped${NC}"
else
    echo -e "${YELLOW}📦 Service not running${NC}"
fi

# Kill any running Python processes for the camera
PIDS=$(pgrep -f "webrtc_server.py\|enhanced_server.py")
if [ ! -z "$PIDS" ]; then
    echo -e "${YELLOW}🔪 Killing Python camera processes...${NC}"
    echo "$PIDS" | xargs kill -TERM
    sleep 2
    
    # Force kill if still running
    PIDS=$(pgrep -f "webrtc_server.py\|enhanced_server.py")
    if [ ! -z "$PIDS" ]; then
        echo "$PIDS" | xargs kill -KILL
    fi
    echo -e "${GREEN}✅ Processes terminated${NC}"
else
    echo -e "${YELLOW}🔍 No camera processes found${NC}"
fi

# Release camera device
echo -e "${YELLOW}📹 Releasing camera device...${NC}"
sudo fuser -k /dev/video0 2>/dev/null || true

echo -e "${GREEN}✅ WebRTC camera stream stopped${NC}"
