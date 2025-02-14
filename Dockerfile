# Use Playwright's Python image as base with Python 3.11
FROM mcr.microsoft.com/playwright/python:v1.41.0-focal

# Set working directory
WORKDIR /app

# Install Python 3.11 and required system dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.11 \
    python3.11-distutils \
    python3.11-dev \
    python3.11-venv \
    ffmpeg \
    imagemagick \
    fonts-dejavu \
    ttf-dejavu \
    fonts-liberation \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --set python3 /usr/bin/python3.11 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick policy to allow GIF operations
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="coder" rights="none" pattern="PS" \/>/<policy domain="coder" rights="read|write" pattern="PS" \/>/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="coder" rights="none" pattern="XPS" \/>/<policy domain="coder" rights="read|write" pattern="XPS" \/>/' /etc/ImageMagick-6/policy.xml

# Create font cache directory and update font cache
RUN mkdir -p /usr/share/fonts/truetype && \
    fc-cache -f -v

# Create and switch to a non-root user
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Create and activate virtual environment
RUN python3.11 -m venv /app/venv && \
    chown -R appuser:appuser /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/venv"

# Install pip in the virtual environment
RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    /app/venv/bin/python3.11 get-pip.py && \
    rm get-pip.py

# Set history directory environment variable
ENV HISTORY_DIR=/testronai/history

# Copy requirements file
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies as appuser
RUN su appuser -c "/app/venv/bin/pip install --no-cache-dir -r requirements.txt"

# Copy the entire project
COPY --chown=appuser:appuser . .

# Expose port 8080 for Railway
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create an entrypoint script
COPY <<'EOF' /app/entrypoint.sh
#!/bin/bash
# Create history directory with root permissions
mkdir -p $HISTORY_DIR
# Set permissions for appuser
chown -R appuser:appuser $HISTORY_DIR

# Switch to appuser and run the app with proper environment
exec su appuser -c "/app/venv/bin/python3.11 -m streamlit run src/app.py"
EOF

RUN chmod +x /app/entrypoint.sh

# Command to run the app
CMD ["/app/entrypoint.sh"] 