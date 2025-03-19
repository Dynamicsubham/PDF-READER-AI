# Start from a lightweight Python image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy our FastAPI code
COPY main.py /app/main.py

# Expose the FastAPI port
EXPOSE 8000

# Set environment variable for AWS (optionally set or pass at runtime)
ENV AWS_REGION
ENV BUCKET_NAME
ENV AWS_SECRET_ACCESS_KEY
ENV AWS_ACCESS_KEY

# Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
