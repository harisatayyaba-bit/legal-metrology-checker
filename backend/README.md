---
title: Legal Metrology Compliance Checker Backend
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Legal Metrology Packaged Commodities Compliance Checker (Backend)

Backend API service built with **FastAPI** and **PaddleOCR (PP-OCRv4)** to scan packaged commodity product labels, extract textual declarations, perform OCR bounding box detection, and evaluate compliance with the Legal Metrology (Packaged Commodities) Rules.

## Features

- **FastAPI Core Engine**: High-performance asynchronous REST API with auto-generated OpenAPI documentation.
- **PaddleOCR (PP-OCRv4)**: Deep-learning text detection and recognition engine optimized for package labels.
- **Image Enhancement Pipeline**: Quality-gating and image preprocessing using OpenCV (CLAHE contrast equalization and unsharp masking) to maximize OCR accuracy on blurry scans.
- **Hugging Face Spaces Ready**: Containerized with the Hugging Face Docker SDK, non-root user permissions, and pre-downloaded model weights for near-instant cold starts.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service health status and API metadata |
| `GET` | `/docs` | Interactive Swagger UI documentation |
| `GET` | `/redoc` | ReDoc API documentation |
| `POST` | `/api/v1/scan` | Upload product label image (multipart/form-data) for OCR and compliance analysis |

### Sample Scan Request

```bash
curl -X POST "http://localhost:7860/api/v1/scan" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@label_image.jpg"
```

## Running Locally with Docker

### 1. Build the Docker Image

```bash
docker build -t legal-metrology-backend .
```

### 2. Run the Container

```bash
docker run -p 7860:7860 legal-metrology-backend
```

Navigate to [http://localhost:7860/docs](http://localhost:7860/docs) in your browser to test endpoints directly.

## Deployment on Hugging Face Spaces

1. Create a new Space on [Hugging Face](https://huggingface.co/spaces).
2. Select **Docker** as the Space SDK.
3. Push or connect this backend repository to your Hugging Face Space repository.
4. The service will automatically build using the included `Dockerfile` and expose port `7860`.
