# Use Python 3.11 as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HISTORY_DIR=/app/history
ENV DISPLAY=:99
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_RUN_ON_SAVE=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV CHROME_PATH=/ms-playwright/chromium-*/chrome-linux/chrome
ENV BROWSER_USE_LOGGING_LEVEL=info
ENV ANONYMIZED_TELEMETRY=false
ENV RESOLUTION=1920x1080x24
ENV RESOLUTION_WIDTH=1920
ENV RESOLUTION_HEIGHT=1080
ENV BROWSER_HEADLESS=true

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    netcat-traditional \
    gnupg \
    curl \
    unzip \
    xvfb \
    libgconf-2-4 \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    dbus \
    xauth \
    xvfb \
    python3-numpy \
    fontconfig \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    ffmpeg \
    imagemagick \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy to allow PDF operations
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml

# Update font cache
RUN mkdir -p /usr/share/fonts/truetype && \
    fc-cache -f -v

# Set working directory and create necessary directories
WORKDIR /app
RUN mkdir -p /app/history

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies and Playwright with system dependencies AS ROOT
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir playwright==1.49.0 && \
    playwright install --with-deps chromium && \
    playwright install-deps

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /ms-playwright

# Switch to non-root user
USER appuser

# Copy application files
COPY --chown=appuser:appuser . .

# Command to run the application
CMD ["python", "-m", "streamlit", "run", "src/app.py", "--server.port", "8080", "--server.address", "0.0.0.0"] 