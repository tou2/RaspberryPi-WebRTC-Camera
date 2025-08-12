# In the recv() method, replace the simplified decoding with:
async def recv(self):
    """Receive next video frame with Pi 5 hardware optimization."""
    pts, time_base = await self.next_timestamp()
    
    try:
        # Get H.264 NAL unit from queue with timeout
        nal_unit = frame_queue.get(timeout=0.05)  # 50ms timeout for low latency
        
        # For proper H.264 handling with official camera, you'd need:
        # 1. A proper H.264 decoder (using libav or similar)
        # 2. Or send the raw H.264 stream directly to WebRTC
        
        # Simplified approach - in practice you'd decode the H.264 properly
        # For now, we'll create a representative frame
        frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
        
        # Apply rotation if needed
        if self.rotation != 0:
            rotation_map = {
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE
            }
            if self.rotation in rotation_map:
                frame = cv2.rotate(frame, rotation_map[self.rotation])
        
        # Convert to VideoFrame
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        return av_frame
        
    except queue.Empty:
        # Return black frame if no frame available (maintains stream)
        pass
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
    
    # Return black frame on error or timeout
    black_frame = np.zeros((CONFIG["height"], CONFIG["width"], 3), dtype=np.uint8)
    av_frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
    av_frame.pts = pts
    av_frame.time_base = time_base
    return av_frame