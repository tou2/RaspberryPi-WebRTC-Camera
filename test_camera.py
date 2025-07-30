#!/usr/bin/env python3
"""
Simple test script to verify rpicam-vid MJPEG output
"""

import subprocess
import time
import sys

def test_rpicam_vid():
    print("Testing rpicam-vid MJPEG output...")
    
    cmd = [
        "rpicam-vid",
        "--timeout", "5000",  # 5 seconds
        "--width", "640",
        "--height", "480",
        "--framerate", "10",
        "--codec", "mjpeg",
        "--nopreview",
        "--output", "-"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        # Read data for a few seconds
        start_time = time.time()
        total_bytes = 0
        frame_count = 0
        
        data_buffer = b''
        
        while time.time() - start_time < 3:  # Read for 3 seconds
            chunk = proc.stdout.read(1024)
            if not chunk:
                break
                
            total_bytes += len(chunk)
            data_buffer += chunk
            
            # Count JPEG frames (look for SOI markers)
            frame_count += data_buffer.count(b'\xff\xd8')
            
            # Keep buffer reasonable size
            if len(data_buffer) > 100000:
                data_buffer = data_buffer[-50000:]
        
        proc.terminate()
        proc.wait()
        
        # Read stderr
        stderr_data = proc.stderr.read()
        
        print(f"Results after 3 seconds:")
        print(f"  Total bytes read: {total_bytes}")
        print(f"  Estimated frames: {frame_count}")
        print(f"  Estimated FPS: {frame_count / 3:.1f}")
        
        if stderr_data:
            print(f"  Stderr output: {stderr_data.decode(errors='ignore')}")
        
        if total_bytes > 0:
            print("✅ rpicam-vid is producing data")
            return True
        else:
            print("❌ rpicam-vid produced no data")
            return False
            
    except Exception as e:
        print(f"❌ Error testing rpicam-vid: {e}")
        return False

if __name__ == "__main__":
    success = test_rpicam_vid()
    sys.exit(0 if success else 1)
