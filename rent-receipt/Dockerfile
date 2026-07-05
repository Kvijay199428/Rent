# Use official lightweight Python image
# File: Dockerfile
FROM python:3.13-slim

# Set working directory to the project root
WORKDIR /code

# Copy and install dependencies first (caches this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application envelope
COPY ./app /code/app

# (Optional) Ensure storage directory exists at the root level, outside of the source code
RUN mkdir -p /code/storage

# Run the app via Uvicorn using module notation
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "20081", "--proxy-headers", "--forwarded-allow-ips", "*"]
