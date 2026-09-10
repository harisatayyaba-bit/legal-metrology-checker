import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Response
from app.schemas.scan_schema import ScanResponse, HealthResponse
from app.services.ocr_service import OcrService, get_ocr_service
from app.services.compliance_service import ComplianceService, get_compliance_service
from app.services.report_service import ReportService, get_report_service
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", response_model=HealthResponse, summary="Backend health check")
async def health_check(ocr_service: OcrService = Depends(get_ocr_service)):
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        ocr_available=ocr_service.is_available,
        ocr_engine=ocr_service.engine_name
    )

@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Scan packaged commodity label image and extract text with bounding boxes"
)
async def scan_label(
    file: UploadFile = File(..., description="Packaged commodity label image file"),
    ocr_service: OcrService = Depends(get_ocr_service),
    compliance_service: ComplianceService = Depends(get_compliance_service),
    report_service: ReportService = Depends(get_report_service)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded or filename missing")

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(settings.ALLOWED_IMAGE_EXTENSIONS))}"
        )

    # Read image content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
        )

    # Process OCR
    try:
        result = ocr_service.process_image(content, file.filename)
        # Evaluate Legal Metrology compliance
        line_texts = [line.text for line in result.lines]
        compliance_report = compliance_service.evaluate_compliance(result.raw_text, line_texts)
        result.compliance = compliance_report

        # Assign unique scan ID and audit timestamp
        scan_id = uuid.uuid4().hex[:12]
        scan_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        result.scan_id = scan_id
        result.scan_timestamp = scan_timestamp

        # Scan-level confidence/review recommendation signal based on blur and extraction certainty
        is_low_quality = bool(result.image_quality and (
            result.image_quality.enhancement_applied or result.image_quality.is_blurry
        ))
        has_low_certainty = bool(
            result.average_confidence < 0.70
            or any(l.confidence < 0.60 for l in result.lines)
        )
        result.requires_human_review = bool(is_low_quality or has_low_certainty)

        # Persist scan data for export
        report_service.save_scan(
            scan_id=scan_id,
            filename=file.filename,
            image_bytes=content,
            scan_result=result.model_dump(),
            timestamp=scan_timestamp
        )

        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Unexpected error during OCR scanning")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.get(
    "/report/{scan_id}",
    summary="Download statutory compliance audit report (PDF or DOCX)"
)
async def download_report(
    scan_id: str,
    format: str = "pdf",
    report_service: ReportService = Depends(get_report_service)
):
    scan_data = report_service.get_scan(scan_id)
    if not scan_data:
        raise HTTPException(
            status_code=404,
            detail=f"Audit scan record '{scan_id}' not found or session expired."
        )

    fmt = format.lower().strip()
    if fmt == "pdf":
        file_bytes = report_service.generate_pdf_report(scan_data)
        media_type = "application/pdf"
        out_ext = "pdf"
    elif fmt in ["docx", "doc", "word"]:
        file_bytes = report_service.generate_docx_report(scan_data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        out_ext = "docx"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{format}'. Allowed formats: 'pdf', 'docx'"
        )

    filename = f"packtrue_compliance_report_{scan_id}.{out_ext}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(file_bytes)),
        "Cache-Control": "no-cache"
    }
    return Response(content=file_bytes, media_type=media_type, headers=headers)

