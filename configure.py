#!/usr/bin/env python3
"""
Configuration wizard for WebRTC camera streaming.
Helps users optimize settings based on their hardware.
"""

import configparser
import os
import subprocess
import sys

def get_pi_model():
    """Detect Raspberry Pi model."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        
        if 'Pi Zero' in cpuinfo:
            return 'Pi Zero'
        elif 'Pi 4' in cpuinfo:
            return 'Pi 4'
        elif 'Pi 3' in cpuinfo:
            return 'Pi 3'
        elif 'Pi 2' in cpuinfo:
            return 'Pi 2'
        else:
            return 'Unknown Pi'
    except:
        return 'Not a Pi'

def test_camera():
    """Test if camera is available."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret
        return False
    except:
        return False

def get_memory_info():
    """Get system memory information."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return memory.total / (1024**3)  # GB
    except:
        return None

def create_config(settings):
    """Create configuration file with user settings."""
    config = configparser.ConfigParser()
    
    config['camera'] = {
        'device_index': '0',
        'width': str(settings['width']),
        'height': str(settings['height']),
        'fps': str(settings['fps']),
        'buffer_size': '1'
    }
    
    config['encoding'] = {
        'bitrate': str(settings['bitrate']),
        'h264_profile': settings['h264_profile'],
        'keyframe_interval': '2'
    }
    
    config['network'] = {
        'host': '0.0.0.0',
        'port': str(settings['port']),
        'max_connections': str(settings['max_connections'])
    }
    
    config['performance'] = {
        'use_gpu_acceleration': 'true',
        'video_threads': str(settings['video_threads']),
        'low_latency_mode': 'true' if settings['low_latency'] else 'false',
        'frame_drop_strategy': 'smart'
    }
    
    config['logging'] = {
        'level': 'INFO',
        'log_performance': 'true',
        'log_file': ''
    }
    
    config['advanced'] = {
        'raspberry_pi_optimizations': 'true',
        'use_mmap': 'true'
    }
    
    with open('config.ini', 'w') as f:
        config.write(f)
    
    print("✅ Configuration saved to config.ini")

def main():
    """Main configuration wizard."""
    print("🔧 WebRTC Camera Configuration Wizard")
    print("=====================================")
    
    # Detect hardware
    pi_model = get_pi_model()
    memory_gb = get_memory_info()
    camera_available = test_camera()
    
    print(f"\n🖥️  Detected hardware:")
    print(f"   Device: {pi_model}")
    if memory_gb:
        print(f"   Memory: {memory_gb:.1f}GB")
    print(f"   Camera: {'✅ Available' if camera_available else '❌ Not available'}")
    
    if not camera_available:
        print("\n⚠️  Camera not detected! Please check:")
        print("   - Camera is properly connected")
        print("   - Camera is enabled in raspi-config")
        print("   - No other processes are using the camera")
        sys.exit(1)
    
    # Get user preferences
    print(f"\n📝 Configuration questions:")
    
    # Use case
    print(f"\n1. What's your primary use case?")
    print("   a) Security monitoring (low latency)")
    print("   b) Streaming/broadcasting (quality)")
    print("   c) Remote monitoring (balanced)")
    
    use_case = input("Choice (a/b/c): ").lower().strip()
    
    # Quality preference
    print(f"\n2. Quality preference:")
    print("   a) Maximum performance (lower quality)")
    print("   b) Balanced")
    print("   c) Maximum quality (lower performance)")
    
    quality = input("Choice (a/b/c): ").lower().strip()
    
    # Network
    print(f"\n3. Network environment:")
    print("   a) Local network only")
    print("   b) Internet streaming")
    
    network = input("Choice (a/b): ").lower().strip()
    
    # Advanced settings
    print(f"\n4. Show advanced options? (y/n): ")
    advanced = input().lower().strip() == 'y'
    
    # Generate settings based on responses
    settings = {}
    
    # Base settings by device
    if 'Zero' in pi_model:
        base_settings = {
            'width': 480, 'height': 360, 'fps': 15, 'bitrate': 300000,
            'h264_profile': 'baseline', 'video_threads': 1, 'max_connections': 2
        }
    elif 'Pi 4' in pi_model:
        base_settings = {
            'width': 1280, 'height': 720, 'fps': 30, 'bitrate': 1500000,
            'h264_profile': 'high', 'video_threads': 4, 'max_connections': 5
        }
    else:
        base_settings = {
            'width': 640, 'height': 480, 'fps': 20, 'bitrate': 800000,
            'h264_profile': 'main', 'video_threads': 2, 'max_connections': 3
        }
    
    settings.update(base_settings)
    
    # Adjust based on use case
    if use_case == 'a':  # Security
        settings['low_latency'] = True
        settings['fps'] = min(settings['fps'], 20)
    elif use_case == 'b':  # Broadcasting
        settings['low_latency'] = False
        settings['bitrate'] = int(settings['bitrate'] * 1.5)
    else:  # Balanced
        settings['low_latency'] = True
    
    # Adjust based on quality preference
    if quality == 'a':  # Performance
        settings['width'] = int(settings['width'] * 0.75)
        settings['height'] = int(settings['height'] * 0.75)
        settings['bitrate'] = int(settings['bitrate'] * 0.7)
    elif quality == 'c':  # Quality
        settings['bitrate'] = int(settings['bitrate'] * 1.3)
        settings['h264_profile'] = 'high'
    
    # Adjust for network
    if network == 'b':  # Internet
        settings['bitrate'] = min(settings['bitrate'], 1000000)  # Cap at 1Mbps
    
    # Default port and advanced settings
    settings['port'] = 8080
    
    # Advanced configuration
    if advanced:
        print(f"\n🔧 Advanced Settings:")
        
        try:
            width = int(input(f"Video width [{settings['width']}]: ") or settings['width'])
            height = int(input(f"Video height [{settings['height']}]: ") or settings['height'])
            fps = int(input(f"Frame rate [{settings['fps']}]: ") or settings['fps'])
            bitrate = int(input(f"Bitrate (bps) [{settings['bitrate']}]: ") or settings['bitrate'])
            port = int(input(f"Server port [{settings['port']}]: ") or settings['port'])
            
            settings.update({
                'width': width, 'height': height, 'fps': fps,
                'bitrate': bitrate, 'port': port
            })
        except ValueError:
            print("⚠️  Invalid input, using defaults")
    
    # Show final configuration
    print(f"\n📋 Final Configuration:")
    print(f"   Resolution: {settings['width']}x{settings['height']}")
    print(f"   Frame rate: {settings['fps']} fps")
    print(f"   Bitrate: {settings['bitrate']/1000:.0f} kbps")
    print(f"   Server port: {settings['port']}")
    print(f"   H.264 profile: {settings['h264_profile']}")
    print(f"   Low latency: {settings['low_latency']}")
    print(f"   Max connections: {settings['max_connections']}")
    
    # Confirm
    confirm = input(f"\n💾 Save this configuration? (y/n): ").lower().strip()
    
    if confirm == 'y':
        create_config(settings)
        
        print(f"\n🚀 Next steps:")
        print(f"   1. Start the server: ./start_stream.sh")
        print(f"   2. Open browser: http://[PI_IP]:{settings['port']}")
        print(f"   3. Monitor performance: ./status.sh")
        
        # Performance warning for Pi Zero
        if 'Zero' in pi_model and (settings['width'] > 640 or settings['fps'] > 20):
            print(f"\n⚠️  Performance Warning:")
            print(f"   Your settings may be too demanding for Pi Zero")
            print(f"   Consider reducing resolution or frame rate if you experience issues")
    else:
        print("❌ Configuration not saved")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Configuration cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Configuration failed: {e}")
        sys.exit(1)
