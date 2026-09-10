# Legal Metrology Packaged Commodities Compliance Checker

[![SIH Problem Statement 26034](https://img.shields.io/badge/SIH%20Problem%20Statement-26034-blue.svg)](https://www.sih.gov.in/)
[![Ministry](https://img.shields.io/badge/Ministry-DoCA%20%28Consumer%20Affairs%29-1e3a8a.svg)](https://consumeraffairs.nic.in/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![OCR Engine](https://img.shields.io/badge/OCR-PaddleOCR-orange.svg)](https://github.com/PaddlePaddle/PaddleOCR)

An automated AI-driven compliance inspection system for packaged commodities under the **Legal Metrology (Packaged Commodities) Rules, 2011**, developed for the **Ministry of Consumer Affairs, Food & Public Distribution (DoCA)**.

---

## 🎯 The Problem & Goal

The Legal Metrology (Packaged Commodities) Rules, 2011 mandate critical declarations on all pre-packaged commodities sold in India:
1. **Name & Address of Manufacturer / Packer / Importer**
2. **Generic or Common Name of Commodity**
3. **Net Quantity** (in standard units of weight, measure, or number)
4. **Month and Year of Manufacture / Packing / Import**
5. **Maximum Retail Price (MRP)** (inclusive of all taxes, with unit sale price)
6. **Consumer Care Details** (name, address, telephone, email of the grievance officer)

Field enforcement officers and consumer protection bodies currently perform manual inspections, which is slow, prone to oversight, and difficult to scale across millions of retail SKUs.

### Key Differentiators (vs. existing scanners)
- **Active Image Quality / Blur Correction**: Flags low-quality photos and applies targeted enhancement rather than silently failing or hallucinating text.
- **Context-Aware Structured Extraction**: Bounding box coordinates and spatial layout are analyzed as structured fields before rules are evaluated — eliminating false positives (e.g., a batch code "250" is never mistaken for MRP).
- **Automated Audit Reports**: Generates formal inspection certificates with highlighted violation regions.

---

## 🏗️ Phase 1 Architecture (Scaffold & OCR)

This initial scaffold establishes the end-to-end capture, OCR recognition, and interactive visual verification pipeline:

```
┌────────────────────────────────────────────────────────┐
│                   React 18 Frontend                    │
│  - Drag & Drop Upload Zone (supports high-res images)  │
│  - Interactive SVG Bounding Box Overlay with Hover Sync │
│  - Raw Extracted Text & Tabbed Line Coordinate Viewer   │
│  - Instant Preloaded Commodity Samples (Amul, Biscuits) │
└───────────────────────────┬────────────────────────────┘
                            │ POST /api/v1/scan (multipart/form-data)
                            ▼
┌────────────────────────────────────────────────────────┐
│                    FastAPI Backend                     │
│  - File type validation & stream ingestion             │
│  - PaddleOCR Engine (detection + recognition + angle)  │
│  - Polygon bounding box coordinate extraction [x, y]   │
│  - Confidence scoring & processing metrics             │
│  - Graceful fallback/mock engine for offline testing   │
└────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
legal-metrology-checker/
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI entrypoint + CORS setup
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py            # Global settings & upload limits
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── scan_schema.py       # Pydantic schemas (OcrLine, ScanResponse)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── ocr_service.py       # PaddleOCR interface & coordinate parser
│   │   └── api/
│   │       ├── __init__.py
│   │       └── scan.py              # /api/v1/scan and /api/v1/health endpoints
│   └── tests/
│       ├── __init__.py
│       └── test_scan.py             # Pytest suite with synthetic image tests
└── frontend/
    ├── package.json
    ├── vite.config.js               # Dev server configuration with API proxy
    ├── index.html
    └── src/
        ├── App.jsx                  # Main dashboard controller
        ├── App.css                  # UI styling with responsive design
        ├── main.jsx                 # React root
        └── components/
            ├── Header.jsx           # SIH 26034 header & backend status pill
            ├── FileUpload.jsx       # Drag & drop upload & sample picker
            ├── ImagePreview.jsx     # SVG bounding box overlay & confidence heatmap
            └── OcrResults.jsx       # Raw text, line table, and JSON inspector
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10 - 3.12** (PaddlePaddle wheels support up to Python 3.12)
- **Node.js 18+** and `npm`

---

### 2. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a Python virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend test suite
pytest tests/

# Launch the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **API Root**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

### 3. Frontend Setup

```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

Open your browser to: **[http://localhost:5173](http://localhost:5173)**

---

## 📡 API Specification

### `POST /api/v1/scan`
Uploads a commodity label photo and performs OCR recognition.

**Request**:
- `Content-Type`: `multipart/form-data`
- `file`: Image binary (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`)

**Response Example (200 OK)**:
```json
{
  "success": true,
  "filename": "amul_pouch_label.png",
  "image_width": 640,
  "image_height": 480,
  "total_lines": 8,
  "average_confidence": 0.9631,
  "processing_time_ms": 142.5,
  "ocr_engine": "PaddleOCR",
  "lines": [
    {
      "id": 1,
      "text": "MRP Rs. 590.00 (INCL. OF ALL TAXES)",
      "confidence": 0.991,
      "box": [
        [40.0, 150.0],
        [460.0, 150.0],
        [460.0, 185.0],
        [40.0, 185.0]
      ]
    }
  ],
  "raw_text": "AMUL PURE GHEE 1L POUCH\nNET QUANTITY: 1 L (905 g)\nMRP Rs. 590.00 (INCL. OF ALL TAXES)..."
}
```

---

## 🛣️ Build Phases Roadmap

- [x] **Phase 1: Scaffold & OCR Pipeline (Current)**
  - Project scaffolding, React UI upload, FastAPI `/scan` endpoint, bounding box coordinate parsing, visual SVG overlay.
- [ ] **Phase 2: Blur Detection & Super-Resolution**
  - OpenCV Laplacian variance blur scoring + Real-ESRGAN enhancement for degraded mobile photos.
- [ ] **Phase 3: Structured Field Extraction**
  - LLM / regex field parser extracting `mrp`, `net_quantity`, `mfg_date`, `consumer_care`, and `manufacturer`.
- [ ] **Phase 4: Legal Metrology Rule Validation Engine**
  - Configurable rules: MRP declaration format, unit sale price presence, consumer care hotline, date freshness.
- [ ] **Phase 5: Automated Compliance Reports & Enforcement Portal**
  - PDF export (`reportlab`), editable Word docs (`python-docx`), role-based enforcement audit dashboard.
