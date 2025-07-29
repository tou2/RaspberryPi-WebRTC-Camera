# Raspberry Pi OS Recommendations for WebRTC Camera Streaming

Since you don't need a UI for camera streaming, here are the best OS options:

## Recommended: Raspberry Pi OS Lite (64-bit)

### Download Links:
- **Official Imager**: https://www.raspberrypi.org/software/
- **Direct Download**: https://downloads.raspberrypi.org/raspios_lite_arm64/images/

### Why Raspberry Pi OS Lite?

#### Performance Benefits:
- **No desktop environment** = more resources for streaming
- **Minimal background processes** = lower CPU usage
- **Smaller memory footprint** = more RAM for video processing
- **Faster boot time** = quick camera startup
- **Less heat generation** = better sustained performance

#### Storage Benefits:
- **~500MB smaller** than full OS
- **Fewer packages** to update
- **Less SD card wear** from background processes
- **More space** for logs and recordings

#### Streaming Benefits:
- **Better network performance** (no GUI network manager conflicts)
- **Consistent performance** (no random desktop processes)
- **Easier automation** (headless operation)
- **Remote management** via SSH only

---

## OS Versions by Pi Model:

| Pi Model | Recommended OS | Architecture | Notes |
|----------|---------------|--------------|-------|
| Pi Zero W | RPi OS Lite 32-bit | ARM32 | Use 32-bit for best compatibility |
| Pi Zero 2 W | RPi OS Lite 64-bit | ARM64 | 64-bit gives better performance |
| Pi 3 | RPi OS Lite 64-bit | ARM64 | 64-bit recommended |
| Pi 4 | RPi OS Lite 64-bit | ARM64 | Definitely use 64-bit |
| Pi 5 | RPi OS Lite 64-bit | ARM64 | Only 64-bit available |

---

## Installation Steps:

### 1. **Download Raspberry Pi Imager**
```bash
# Or use direct download links above
```

### 2. **Flash SD Card with Imager**
- Choose "Raspberry Pi OS Lite (64-bit)" 
- Click gear icon for advanced options
- **Enable SSH** (very important!)
- Set **username/password**
- Configure **WiFi** (if using wireless)

### 3. **Essential Settings in Imager:**
```
Enable SSH
Set username: pi (or your choice)
Set password: (strong password)
Configure WiFi SSID/password
Set WiFi country
Enable camera (if option available)
```

### 4. **First Boot Setup:**
```bash
# SSH into your Pi
ssh pi@[PI_IP_ADDRESS]

# Update system
sudo apt update && sudo apt upgrade -y

# Enable camera (if not done in imager)
sudo raspi-config nonint do_camera 0

# Reboot
sudo reboot
```

---

## Alternative: Custom Minimal Setup

If you want even more performance optimization:

### **Ubuntu Server 22.04 LTS (64-bit)**
- **Even more minimal** than RPi OS Lite
- **Better for Pi 4/5** with lots of RAM
- **Longer support** lifecycle
- **More challenging** setup for beginners

### **Raspberry Pi OS Lite (32-bit)**
- **For Pi Zero W only** (better compatibility)
- **Slightly lower memory usage**
- **Some packages** may perform better

---

## Pro Tips:

### For Maximum Performance:
1. **Disable unnecessary services:**
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl disable hciuart
   sudo systemctl disable avahi-daemon
   ```

2. **Optimize GPU memory split:**
   ```bash
   # Add to /boot/config.txt
   gpu_mem=128  # For camera usage
   ```

3. **Disable swap (on fast SD cards):**
   ```bash
   sudo dphys-swapfile swapoff
   sudo systemctl disable dphys-swapfile
   ```

### For Remote Management:
- **Install screen/tmux** for persistent sessions
- **Set up key-based SSH** for security
- **Configure static IP** for consistent access
- **Enable wake-on-LAN** if supported

---

## Bottom Line:

**Use Raspberry Pi OS Lite (64-bit)** unless you have a specific reason not to:

- **Pi Zero W**: RPi OS Lite 32-bit (for compatibility)
- **Pi Zero 2 W**: RPi OS Lite 64-bit (best performance)
- **Pi 3/4/5**: RPi OS Lite 64-bit (definitely!)

The installation script (`install.sh`) will handle all the optimization and setup automatically once you have the base OS running!
