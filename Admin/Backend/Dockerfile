FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy our code
COPY main_admin.py /app/main_admin.py

EXPOSE 8100

ENV AWS_REGION
ENV BUCKET_NAME
ENV AWS_SECRET_ACCESS_KEY
ENV AWS_ACCESS_KEY

CMD ["uvicorn", "main_admin:app", "--host", "0.0.0.0", "--port", "8100"]
