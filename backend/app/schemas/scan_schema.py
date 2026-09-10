from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ComplianceVerdict(str, Enum):
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non-Compliant"
    ADVISORY = "Compliant — Packaging Advisory"

class FieldCompliance(BaseModel):
    field_id: str = Field(..., description="Unique machine key for declaration field")
    field_name: str = Field(..., description="Human-readable statutory declaration name")
    extracted_value: Optional[str] = Field(None, description="Parsed text declaration value from label")
    verdict: str = Field(..., description="'Compliant', 'Non-Compliant', or 'Compliant — Packaging Advisory'")
    reason: str = Field(..., description="One-line statutory justification or advisory reason")
    rule_reference: str = Field(..., description="Citation from Legal Metrology Rules, 2011")

class ComplianceReport(BaseModel):
    overall_verdict: str = Field(..., description="Final compliance tier verdict")
    summary: str = Field(..., description="One-line executive summary of label compliance status")
    total_checks: int = Field(default=6)
    passed_checks: int = Field(default=0)
    advisory_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    fields: List[FieldCompliance] = Field(default_factory=list)

class OcrLine(BaseModel):
    id: int = Field(..., description="1-indexed line order id")
    text: str = Field(..., description="Extracted line text")
    confidence: float = Field(..., description="Detection confidence between 0.0 and 1.0")
    box: List[List[float]] = Field(..., description="4-point polygon bounding box coordinates [x, y]")

class ImageQualityMeta(BaseModel):
    blur_score: float = Field(..., description="Variance of Laplacian blur metric")
    quality_threshold: float = Field(default=100.0, description="Blur score threshold for quality check")
    is_blurry: bool = Field(..., description="Whether image score was below threshold")
    enhancement_applied: bool = Field(..., description="Whether Real-ESRGAN deblurring was applied")
    quality_status: str = Field(..., description="Human-readable quality string")
    enhancement_method: str = Field(default="None", description="Enhancement engine applied")

class ScanResponse(BaseModel):
    success: bool = True
    scan_id: Optional[str] = None
    scan_timestamp: Optional[str] = None
    filename: str
    image_width: int
    image_height: int
    total_lines: int
    average_confidence: float
    lines: List[OcrLine]
    raw_text: str
    processing_time_ms: float
    ocr_engine: str = "PaddleOCR"
    image_quality: Optional[ImageQualityMeta] = None
    compliance: Optional[ComplianceReport] = None
    requires_human_review: bool = Field(default=False, description="Scan-level flag indicating if low confidence warrants human review")
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    ocr_available: bool
    ocr_engine: str
