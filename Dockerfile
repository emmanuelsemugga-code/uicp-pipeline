# Use Python 3.12 slim image
FROM python:3.12.13-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir Flask==3.0.0

# Copy entire UICP codebase
COPY engines/ engines/
COPY extraction/ extraction/
COPY export/ export/
COPY tests/ tests/
COPY app/ app/

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1

# Default environment variables (can be overridden at runtime)
ENV API_KEY="sk-test-default-key-change-me"
ENV CONSTRAINT_SET_PATH="/etc/constraint_set.json"
ENV PORT=5000

# Run Flask app
CMD ["python", "-m", "app.api"]
