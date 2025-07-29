# Camera Test Script

This script (`camera_test.sh`) provides comprehensive testing and troubleshooting for Raspberry Pi cameras used with the WebRTC streaming setup.

## Usage

On your Raspberry Pi, make the script executable and run it:

```bash
chmod +x camera_test.sh
./camera_test.sh
```

## What it tests

1. **System Information** - Shows Pi model and OS version
2. **Camera Device Detection** - Checks for `/dev/video*` devices and permissions
3. **Hardware Detection** - Uses `vcgencmd get_camera` to check if camera is detected
4. **Boot Configuration** - Verifies camera settings in `/boot/config.txt`
5. **Kernel Modules** - Checks if camera modules are loaded
6. **Hardware Test** - Uses `raspistill` to test camera hardware
7. **OpenCV Test** - Tests camera with OpenCV (multiple indices and frame capture)
8. **Process Check** - Shows if any processes are using the camera
9. **System Resources** - Displays memory, temperature, and disk usage
10. **Quick Fixes** - Applies common fixes automatically

## When to use

- Camera not working after installation
- "Camera opened but could not capture frame" errors
- Before running the WebRTC server to verify camera functionality
- Troubleshooting camera hardware issues
- Checking camera permissions and configuration

## Common fixes applied

The script automatically tries:
- Loading the `bcm2835-v4l2` camera module
- Adding user to the `video` group for camera access
- Checking and reporting configuration issues

## Troubleshooting output

The script provides color-coded output:
- 🟢 **Green**: Success/working correctly
- 🟡 **Yellow**: Warnings or recommendations
- 🔴 **Red**: Errors or failures
- 🔵 **Blue**: Section headers

## Next steps

If the camera test passes, you can start the WebRTC stream:
```bash
./start_stream.sh
```

If tests fail, follow the troubleshooting recommendations provided by the script.
