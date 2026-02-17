# ----------------------------------------------------
# Base Image (Amazon ECR Public mirror of Docker Hub)
# ----------------------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# ----------------------------------------------------
# Set working directory for SageMaker Processing
# ----------------------------------------------------
WORKDIR /opt/ml/processing/code

# ----------------------------------------------------
# Install system dependencies (minimal)
# ----------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------
# Install Python dependencies
# ----------------------------------------------------
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    boto3

# ----------------------------------------------------
# Copy your data quality script
# ----------------------------------------------------
COPY data_quality.py .

# ----------------------------------------------------
# Default command
# ----------------------------------------------------
ENTRYPOINT ["python3", "/opt/ml/processing/code/data_quality.py"]
