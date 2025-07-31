#!/bin/bash

# Quick start script for WebRTC camera streaming
# This script activates the environment and starts the server

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting WebRTC Camera Stream${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run the installation script first: ./install.sh"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if camera is available
if ! python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera available:', cap.isOpened()); cap.release()" 2>/dev/null | grep -q "True"; then
    echo -e "${RED}❌ Camera not available!${NC}"
    echo "Please check camera connection and configuration."
    exit 1
fi

echo -e "${GREEN}📹 Camera detected successfully${NC}"

# Start the server
echo -e "${GREEN}🌐 Starting WebRTC server...${NC}"
echo ""
echo "Access the stream at: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 enhanced_server.py
