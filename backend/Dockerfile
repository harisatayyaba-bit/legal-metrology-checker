# Use official Python 3.10 slim
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Install essential system dependencies for OpenCV and PaddlePaddle/PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user with UID 1000 (required for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set working directory inside user home
WORKDIR /home/user/app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy and install python dependencies
COPY --chown=user:user requirements.txt /home/user/app/
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download PaddleOCR PP-OCRv4 models during build to ensure fast cold starts on Hugging Face Spaces
USER user
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(ocr_version='PP-OCRv4', lang='en')" || true

# Copy remaining application source code
USER root
COPY --chown=user:user . /home/user/app/

# Switch to non-root user for security and Hugging Face Spaces compliance
USER user

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Start FastAPI application using uvicorn on port 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
