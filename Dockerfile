# ABOUTME: Multi-stage Docker build for Glimpser real-time monitoring application
# ABOUTME: Uses uv for fast dependency management and optimized layer caching

# Build stage
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies to virtual environment
RUN uv venv /opt/venv && \
    uv pip install --virtual-env /opt/venv -e . && \
    uv pip install --virtual-env /opt/venv gunicorn

# Runtime stage
FROM python:3.12-slim AS runtime

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libsqlite3-0 curl iputils-ping net-tools netcat-traditional \
    libsqlite3-dev libjpeg62-turbo libpng16-16 libtiff6 libfreetype6 \
    libwebp7 unzip poppler-utils xvfb ffmpeg libssl3 libffi8 libbz2-1.0 \
    libreadline8 libncurses5 libncursesw6 libxml2 libxslt1.1 \
    wget gnupg iproute2 wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -qO- https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -N http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/ \
    && unzip ~/chromedriver_linux64.zip -d ~/ \
    && rm ~/chromedriver_linux64.zip \
    && mv -f ~/chromedriver /usr/local/bin/chromedriver \
    && chown root:root /usr/local/bin/chromedriver \
    && chmod 0755 /usr/local/bin/chromedriver

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set work directory
WORKDIR /app

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=main.py \
    FLASK_RUN_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create necessary directories
RUN mkdir -p /app/db /app/logs /app/screenshots /app/videos /app/summaries

# Expose port
EXPOSE 8082

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8082", "wsgi:app"]
