# Handwriting Font Generator — Production Docker Image
# Uses Debian base with Python, potrace, and FontForge pre-installed
FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    potrace \
    fontforge \
    python3-fontforge \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p uploads outputs extracted_letters

# Pre-generate templates so they exist immediately on startup
RUN python generate_template.py template.png && \
    python generate_symbol_template.py symbol_template.png

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Expose port
EXPOSE 8000

# Production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "app:app"]
