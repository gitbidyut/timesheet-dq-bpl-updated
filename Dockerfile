FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python libraries
RUN pip install --no-cache-dir pandas numpy pyarrow

# SageMaker standard paths
RUN mkdir -p /opt/ml/processing/input \
             /opt/ml/processing/output \
             /opt/ml/processing/code

# Copy script into image (optional – S3 override still works)
COPY data_quality.py /opt/ml/processing/code/data_quality.py

WORKDIR /opt/ml/processing/code

ENTRYPOINT ["python3", "/opt/ml/processing/code/data_quality.py"]