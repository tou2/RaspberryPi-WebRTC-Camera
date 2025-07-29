# Use multi-stage build for smaller image
FROM python:3.11-slim-bullseye as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff5-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    gfortran \
    libssl-dev \
    libffi-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install Python packages
WORKDIR /app
COPY requirements.txt .
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim-bullseye

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libavcodec58 \
    libavformat58 \
    libswscale5 \
    libv4l-0 \
    libxvidcore4 \
    libx264-160 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff5 \
    libgtk-3-0 \
    libatlas3-base \
    libssl1.1 \
    libffi7 \
    libopus0 \
    libvpx6 \
    libsrtp2-1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Copy application files
WORKDIR /app
COPY *.py ./
COPY config.ini ./
COPY requirements.txt ./

# Create non-root user
RUN useradd -r -s /bin/false webrtc && \
    chown -R webrtc:webrtc /app

USER webrtc

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/stats || exit 1

# Environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/venv/bin:$PATH"

# Start command
CMD ["python", "enhanced_server.py"]
