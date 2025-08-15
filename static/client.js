let pc = null;
let reconnectTimer = null;
let lastFrameTime = 0;
let latencyMeasurements = [];

document.addEventListener('DOMContentLoaded', () => {
    updateBatteryStatus();
    setInterval(updateBatteryStatus, 30000); // Update every 30 seconds
});

async function updateBatteryStatus() {
    try {
        const response = await fetch('/battery');
        if (!response.ok) {
            document.getElementById('batteryContainer').style.display = 'none';
            return;
        }

        const data = await response.json();
        const container = document.getElementById('batteryContainer');
        const iconEl = document.getElementById('batteryIcon');
        const levelEl = document.getElementById('batteryLevel');
        const barFillEl = document.getElementById('batteryBarFill');

        container.style.display = 'flex';
        levelEl.textContent = `${data.percentage}%`;
        barFillEl.style.width = `${data.percentage}%`;

        barFillEl.classList.remove('charging');
        if (data.state.includes('charging')) {
            iconEl.textContent = '(Charging)';
            barFillEl.classList.add('charging');
        } else {
            if (data.percentage > 80) iconEl.textContent = '(High)';
            else if (data.percentage > 20) iconEl.textContent = '(Medium)';
            else iconEl.textContent = '(Low)';
        }

        if (data.percentage <= 20) {
            barFillEl.style.backgroundColor = '#f44336'; // Red
        } else if (data.percentage <= 50) {
            barFillEl.style.backgroundColor = '#ff9800'; // Orange
        } else {
            barFillEl.style.backgroundColor = '#4CAF50'; // Green
        }

    } catch (error) {
        console.warn('Could not fetch battery status.', error);
        document.getElementById('batteryContainer').style.display = 'none';
    }
}

// Update quality value display
document.getElementById('quality').addEventListener('input', function () {
    document.getElementById('qualityValue').textContent = this.value;
});

// Update advanced settings displays
document.getElementById('sharpness').addEventListener('input', function () {
    document.getElementById('sharpnessValue').textContent = (this.value / 100).toFixed(1);
});

document.getElementById('contrast').addEventListener('input', function () {
    document.getElementById('contrastValue').textContent = (this.value / 100).toFixed(1);
});

document.getElementById('saturation').addEventListener('input', function () {
    document.getElementById('saturationValue').textContent = (this.value / 100).toFixed(1);
});

document.getElementById('brightness').addEventListener('input', function () {
    const value = (this.value / 100) - 1;
    document.getElementById('brightnessValue').textContent = value.toFixed(1);
});

// Set ultra-low latency as default
document.getElementById('latencyMode').value = 'ultra';
document.getElementById('resolution').value = '320,240';
document.getElementById('fps').value = '60';
document.getElementById('quality').value = '75';
document.getElementById('qualityValue').textContent = '75';

const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

function updateStatus(message, className) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${className}`;
}

function updateStats() {
    if (!pc) return;

    pc.getStats().then(stats => {
        const statsDiv = document.getElementById('stats');
        statsDiv.style.display = 'block';

        stats.forEach(report => {
            if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
                document.getElementById('bytesReceived').textContent = report.bytesReceived || '-';
                document.getElementById('packetsReceived').textContent = report.packetsReceived || '-';
                document.getElementById('packetsLost').textContent = report.packetsLost || '-';

                if (report.framesPerSecond) {
                    document.getElementById('frameRate').textContent = report.framesPerSecond.toFixed(1) + ' fps';
                }
            }
        });

        document.getElementById('connectionState').textContent = pc.connectionState;
        document.getElementById('iceConnectionState').textContent = pc.iceConnectionState;

        // Update resolution info
        const resolutionSelect = document.getElementById('resolution');
        const resolution = resolutionSelect.value;
        document.getElementById('resolutionInfo').textContent = resolution;
    });
}

function toggleAdvancedSettings() {
    const settings = document.getElementById('advancedSettings');
    settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
}

function resetAdvancedSettings() {
    document.getElementById('sharpness').value = 100;
    document.getElementById('contrast').value = 100;
    document.getElementById('saturation').value = 100;
    document.getElementById('brightness').value = 100;

    document.getElementById('sharpnessValue').textContent = '1.0';
    document.getElementById('contrastValue').textContent = '1.0';
    document.getElementById('saturationValue').textContent = '1.0';
    document.getElementById('brightnessValue').textContent = '0.0';
}

async function start() {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const latencyModeSelect = document.getElementById('latencyMode');
    const resolutionSelect = document.getElementById('resolution');
    const fpsSelect = document.getElementById('fps');

    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    startBtn.disabled = true;
    latencyModeSelect.disabled = true;
    resolutionSelect.disabled = true;
    fpsSelect.disabled = true;
    updateStatus('Connecting...', 'connecting');

    try {
        pc = new RTCPeerConnection(configuration);

        pc.onconnectionstatechange = () => {
            console.log('Connection state:', pc.connectionState);
            if (pc.connectionState === 'connected') {
                updateStatus('Connected - Ultra-Low Latency', 'connected');
                setInterval(updateStats, 1000);
                if (reconnectTimer) {
                    clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                console.log('Connection failed or disconnected, attempting to reconnect...');
                updateStatus('Connection lost, reconnecting...', 'connecting');
                if (pc) {
                    pc.close();
                    pc = null;
                }
                if (!reconnectTimer) {
                    reconnectTimer = setTimeout(start, 5000);
                }
            }
        };

        pc.oniceconnectionstatechange = () => {
            console.log('ICE connection state:', pc.iceConnectionState);
        };

        pc.ontrack = (event) => {
            console.log('Received remote stream');
            const video = document.getElementById('video');
            video.srcObject = event.streams[0];

            // Add frame timing for latency measurement
            video.addEventListener('timeupdate', () => {
                if (lastFrameTime) {
                    const latency = (Date.now() - lastFrameTime);
                    latencyMeasurements.push(latency);
                    if (latencyMeasurements.length > 10) {
                        latencyMeasurements.shift();
                    }
                    const avgLatency = latencyMeasurements.reduce((a, b) => a + b, 0) / latencyMeasurements.length;
                    document.getElementById('latency').textContent = avgLatency.toFixed(0);
                }
                lastFrameTime = Date.now();
            });
        };

        // Get settings from UI
        const latencyMode = latencyModeSelect.value;
        const resolution = resolutionSelect.value.split(',');
        const width = parseInt(resolution[0], 10);
        const height = parseInt(resolution[1], 10);
        const fps = parseInt(fpsSelect.value, 10);
        const quality = parseInt(document.getElementById('quality').value);
        const sharpness = parseFloat(document.getElementById('sharpness').value) / 100;
        const contrast = parseFloat(document.getElementById('contrast').value) / 100;
        const saturation = parseFloat(document.getElementById('saturation').value) / 100;
        const brightness = (parseFloat(document.getElementById('brightness').value) / 100) - 1;

        // Create offer for video only
        const offer = await pc.createOffer({
            offerToReceiveVideo: true,
            offerToReceiveAudio: false
        });
        await pc.setLocalDescription(offer);

        // Send offer to server
        const response = await fetch('/offer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
                width: width,
                height: height,
                fps: fps,
                quality: quality,
                sharpness: sharpness,
                contrast: contrast,
                saturation: saturation,
                brightness: brightness,
                latencyMode: latencyMode
            }),
        });

        const answer = await response.json();
        await pc.setRemoteDescription(new RTCSessionDescription(answer));

        stopBtn.disabled = false;
        document.getElementById('fullscreenBtn').disabled = false;
        document.getElementById('rotateBtn').disabled = false;
        document.getElementById('snapshotBtn').disabled = false;

    } catch (error) {
        console.error('Error starting stream:', error);
        updateStatus('Connection failed', 'disconnected');
        startBtn.disabled = false;
        latencyModeSelect.disabled = false;
        resolutionSelect.disabled = false;
        fpsSelect.disabled = false;
    }
}

function stop() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statsDiv = document.getElementById('stats');
    const latencyModeSelect = document.getElementById('latencyMode');
    const resolutionSelect = document.getElementById('resolution');
    const fpsSelect = document.getElementById('fps');

    if (pc) {
        pc.close();
        pc = null;
    }

    const video = document.getElementById('video');
    video.srcObject = null;

    updateStatus('Disconnected', 'disconnected');
    statsDiv.style.display = 'none';

    startBtn.disabled = false;
    stopBtn.disabled = true;
    document.getElementById('fullscreenBtn').disabled = true;
    document.getElementById('rotateBtn').disabled = true;
    document.getElementById('snapshotBtn').disabled = true;
    latencyModeSelect.disabled = false;
    resolutionSelect.disabled = false;
    fpsSelect.disabled = false;

    // Reset latency measurements
    latencyMeasurements = [];
    lastFrameTime = 0;
}

async function rotate() {
    console.log('Requesting camera rotation');
    try {
        const response = await fetch('/rotate', { method: 'POST' });
        if (response.ok) {
            console.log('Camera rotation request successful');
        } else {
            console.error('Failed to rotate camera');
        }
    } catch (error) {
        console.error('Error rotating camera:', error);
    }
}

function takeSnapshot() {
    const video = document.getElementById('video');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Create download link
    const link = document.createElement('a');
    link.download = 'snapshot-' + new Date().toISOString().slice(0, 19).replace(/:/g, '-') + '.png';
    link.href = canvas.toDataURL();
    link.click();
}

function toggleFullScreen() {
    const video = document.getElementById('video');
    if (!document.fullscreenElement) {
        video.requestFullscreen().catch(err => {
            alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}
