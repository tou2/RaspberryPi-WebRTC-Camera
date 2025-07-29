#!/usr/bin/env python3
"""
Performance test script for WebRTC camera streaming.
Tests camera performance and system capabilities.
"""

import time
import cv2
import psutil
import threading
import sys
from statistics import mean, stdev

def test_camera_performance():
    """Test camera capture performance."""
    print("🎥 Testing camera performance...")
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return None
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        frame_times = []
        frame_count = 0
        test_duration = 10  # seconds
        start_time = time.time()
        
        print(f"Capturing frames for {test_duration} seconds...")
        
        while time.time() - start_time < test_duration:
            frame_start = time.time()
            ret, frame = cap.read()
            frame_end = time.time()
            
            if ret:
                frame_times.append(frame_end - frame_start)
                frame_count += 1
            else:
                print("⚠️  Failed to capture frame")
        
        cap.release()
        
        if frame_times:
            avg_fps = frame_count / test_duration
            avg_frame_time = mean(frame_times) * 1000  # ms
            frame_time_std = stdev(frame_times) * 1000 if len(frame_times) > 1 else 0
            
            print(f"✅ Camera Performance Results:")
            print(f"   Average FPS: {avg_fps:.1f}")
            print(f"   Average frame time: {avg_frame_time:.1f}ms")
            print(f"   Frame time std dev: {frame_time_std:.1f}ms")
            print(f"   Total frames captured: {frame_count}")
            
            return {
                'fps': avg_fps,
                'frame_time_ms': avg_frame_time,
                'frame_time_std': frame_time_std,
                'total_frames': frame_count
            }
        else:
            print("❌ No frames captured")
            return None
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return None

def test_system_performance():
    """Test system performance metrics."""
    print("\n🖥️  Testing system performance...")
    
    # CPU test
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    
    # Memory test
    memory = psutil.virtual_memory()
    
    # Disk test
    disk = psutil.disk_usage('/')
    
    # Temperature (if available)
    temperature = None
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temperature = float(f.read()) / 1000.0
    except:
        pass
    
    print(f"✅ System Performance Results:")
    print(f"   CPU cores: {cpu_count}")
    print(f"   CPU usage: {cpu_percent}%")
    print(f"   Memory total: {memory.total / (1024**3):.1f}GB")
    print(f"   Memory available: {memory.available / (1024**3):.1f}GB")
    print(f"   Memory usage: {memory.percent}%")
    print(f"   Disk free: {disk.free / (1024**3):.1f}GB")
    if temperature:
        print(f"   Temperature: {temperature}°C")
    
    return {
        'cpu_cores': cpu_count,
        'cpu_percent': cpu_percent,
        'memory_total_gb': memory.total / (1024**3),
        'memory_available_gb': memory.available / (1024**3),
        'memory_percent': memory.percent,
        'disk_free_gb': disk.free / (1024**3),
        'temperature': temperature
    }

def test_encoding_performance():
    """Test video encoding performance."""
    print("\n🎬 Testing video encoding performance...")
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera for encoding test")
            return None
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Test different encoding parameters
        encoding_times = []
        test_frames = 30
        
        print(f"Testing encoding on {test_frames} frames...")
        
        for i in range(test_frames):
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Simulate WebRTC processing
            start_time = time.time()
            
            # Convert BGR to RGB (typical WebRTC step)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Simulate some processing
            processed_frame = cv2.resize(rgb_frame, (640, 480))
            
            end_time = time.time()
            encoding_times.append(end_time - start_time)
        
        cap.release()
        
        if encoding_times:
            avg_encoding_time = mean(encoding_times) * 1000  # ms
            max_possible_fps = 1000 / avg_encoding_time if avg_encoding_time > 0 else 0
            
            print(f"✅ Encoding Performance Results:")
            print(f"   Average encoding time: {avg_encoding_time:.1f}ms")
            print(f"   Max theoretical FPS: {max_possible_fps:.1f}")
            print(f"   Frames processed: {len(encoding_times)}")
            
            return {
                'avg_encoding_time_ms': avg_encoding_time,
                'max_fps': max_possible_fps,
                'frames_processed': len(encoding_times)
            }
        else:
            print("❌ No frames processed")
            return None
            
    except Exception as e:
        print(f"❌ Encoding test failed: {e}")
        return None

def generate_recommendations(camera_results, system_results, encoding_results):
    """Generate performance recommendations."""
    print("\n💡 Performance Recommendations:")
    
    if not camera_results or not system_results:
        print("❌ Cannot generate recommendations - insufficient test data")
        return
    
    # Camera recommendations
    if camera_results['fps'] < 15:
        print("📹 Camera: Consider reducing resolution or frame rate")
    elif camera_results['fps'] > 25:
        print("📹 Camera: Good performance, can handle high frame rates")
    
    # System recommendations
    if system_results['cpu_percent'] > 80:
        print("🖥️  CPU: High usage detected, consider optimizations")
    if system_results['memory_percent'] > 80:
        print("💾 Memory: High usage detected, monitor for memory leaks")
    if system_results['temperature'] and system_results['temperature'] > 70:
        print("🌡️  Temperature: Consider adding cooling")
    
    # Encoding recommendations
    if encoding_results and encoding_results['max_fps'] < 20:
        print("🎬 Encoding: Consider using lower resolution or quality settings")
    
    # Suggested configuration
    print("\n⚙️  Suggested Configuration:")
    
    if camera_results['fps'] >= 25 and system_results['cpu_percent'] < 60:
        print("   Resolution: 640x480 or higher")
        print("   FPS: 25-30")
        print("   Bitrate: 800-1200 kbps")
    elif camera_results['fps'] >= 15:
        print("   Resolution: 640x480")
        print("   FPS: 15-20")
        print("   Bitrate: 400-800 kbps")
    else:
        print("   Resolution: 320x240 or 480x360")
        print("   FPS: 10-15")
        print("   Bitrate: 200-400 kbps")

def main():
    """Run all performance tests."""
    print("🚀 WebRTC Camera Performance Test")
    print("==================================")
    
    # Test camera
    camera_results = test_camera_performance()
    
    # Test system
    system_results = test_system_performance()
    
    # Test encoding
    encoding_results = test_encoding_performance()
    
    # Generate recommendations
    generate_recommendations(camera_results, system_results, encoding_results)
    
    print("\n✅ Performance testing complete!")
    print("\nUse these results to optimize your config.ini file")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
