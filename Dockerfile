FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (build tools for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "ingestion/producer.py"]
