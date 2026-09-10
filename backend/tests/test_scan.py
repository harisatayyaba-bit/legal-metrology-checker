import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import sys
import os

# Add backend directory to sys.path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.services.compliance_service import ComplianceService, ComplianceVerdict

client = TestClient(app)

def create_test_image(text="TEST LABEL MRP Rs 250") -> bytes:
    """Helper to generate a synthetic image in memory."""
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 190], outline=(0, 0, 0), width=2)
    draw.text((30, 80), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "ocr_engine" in data

def test_scan_valid_image():
    image_bytes = create_test_image()
    files = {"file": ("test_label.png", image_bytes, "image/png")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "test_label.png"
    assert data["image_width"] == 400
    assert data["image_height"] == 200
    assert data["total_lines"] >= 1
    assert "raw_text" in data
    assert "compliance" in data
    assert data["compliance"] is not None
    assert "overall_verdict" in data["compliance"]
    assert "fields" in data["compliance"]
    assert len(data["compliance"]["fields"]) == 6

def test_scan_invalid_extension():
    files = {"file": ("test_document.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]

def test_scan_empty_file():
    files = {"file": ("empty.png", b"", "image/png")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_compliance_engine_fully_compliant():
    service = ComplianceService()
    lines = [
        "AMUL PURE GHEE 1L POUCH",
        "NET QUANTITY: 1 L (905 g)",
        "MRP Rs. 590.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 12/04/2026",
        "MFG BY: GUJARAT CO-OP MILK MKT FEDERATION LTD",
        "ANAND 388001, GUJARAT, INDIA",
        "CONSUMER CARE: 1800-258-3333 / customercare@amul.coop",
        "FSSAI LIC NO 10014021000001"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)
    assert report.overall_verdict == ComplianceVerdict.COMPLIANT.value
    assert report.failed_checks == 0
    assert report.passed_checks >= 5

def test_compliance_engine_advisory():
    service = ComplianceService()
    # Has MRP Rs 250, but omitted "inclusive of all taxes"
    lines = [
        "PARLE-G GLUCOSE BISCUITS",
        "NET WT: 250 g",
        "MRP: Rs. 25.00",
        "MFG DATE: 08/2026",
        "MFG BY: PARLE PRODUCTS PVT LTD, MUMBAI 400057",
        "CARE: 1800-222-111 / care@parle.biz",
        "FSSAI 10012022000111"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)
    # The MRP declaration without "inclusive of all taxes" should trigger an advisory
    assert report.overall_verdict == ComplianceVerdict.ADVISORY.value
    mrp_field = next(f for f in report.fields if f.field_id == "mrp_declaration")
    assert mrp_field.verdict == ComplianceVerdict.ADVISORY.value

def test_compliance_engine_non_compliant():
    service = ComplianceService()
    # Missing MRP entirely, missing manufacturer address
    lines = [
        "SOME UNBRANDED SNACK",
        "NET WT: 100 g",
        "EXP: 10/2026"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)
    assert report.overall_verdict == ComplianceVerdict.NON_COMPLIANT.value
    assert report.failed_checks >= 2

def test_image_quality_gate_sharp():
    # Sharp image has high variance of Laplacian
    image_bytes = create_test_image()
    files = {"file": ("sharp_label.png", image_bytes, "image/png")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "image_quality" in data
    quality = data["image_quality"]
    assert quality is not None
    assert "blur_score" in quality
    assert quality["blur_score"] > 0.0
    assert "enhancement_applied" in quality
    assert "quality_status" in quality

def test_image_quality_gate_blurry():
    from PIL import ImageFilter
    # Create intentionally blurred image
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 80), "BLURRED LABEL MRP RS 100", fill=(0, 0, 0))
    # Apply severe Gaussian blur
    blurred = img.filter(ImageFilter.GaussianBlur(radius=8))
    buf = io.BytesIO()
    blurred.save(buf, format="PNG")

    files = {"file": ("blurry_label.png", buf.getvalue(), "image/png")}
    response = client.post("/api/v1/scan", files=files)
    assert response.status_code == 200
    data = response.json()
    quality = data["image_quality"]
    assert quality is not None
    # Blur score should be low and enhancement applied
    assert quality["is_blurry"] is True
    assert quality["enhancement_applied"] is True
    assert "Low" in quality["quality_status"]


def test_compliance_engine_detergent_non_food():
    service = ComplianceService()
    lines = [
        "SURF EXCEL EASY WASH",
        "DETERGENT POWDER",
        "Net weight:",
        "1 kg (when packed)",
        "MRP Rs. 140.00 USP Rs. 0.14/g (incl. of all taxes)",
        "BATCH NO: B2026-99",
        "MFG. DATE: 08/2026",
        "MFG LIC NO: M/742/2018",
        "MANUFACTURED BY: HINDUSTAN HOMECARE LTD",
        "PLOT 12, SECTOR 3, HARIDWAR 249403, UK",
        "CONSUMER CARE: 1800-111-222 / care@homecare.in"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    # 1. Non-food commodity: FSSAI check should be skipped entirely (not shown as advisory)
    assert report.total_checks == 5
    assert not any(f.field_id == "fssai_license" for f in report.fields)
    assert report.advisory_checks == 0
    assert report.failed_checks == 0
    assert report.overall_verdict == ComplianceVerdict.COMPLIANT.value

    # 2. Net quantity: clean value with quantity number, not just "Net weight:"
    qty_field = next(f for f in report.fields if f.field_id == "net_quantity")
    assert "1 kg" in qty_field.extracted_value
    assert qty_field.extracted_value != "Net weight:"

    # 3. MRP: clean price value without USP Rs. 0.14/g mixed in
    mrp_field = next(f for f in report.fields if f.field_id == "mrp_declaration")
    assert "140.00" in mrp_field.extracted_value
    assert "0.14" not in mrp_field.extracted_value

    # 4. Manufacturer: clean entity name and address
    mfg_field = next(f for f in report.fields if f.field_id == "manufacturer_address")
    assert "HINDUSTAN HOMECARE LTD" in mfg_field.extracted_value
    assert "249403" in mfg_field.extracted_value


def test_compliance_engine_serving_size_distinction():
    """Verify Net Quantity extracts package weight (e.g. 500g) and ignores nutrition Serving Size (e.g. 30g)."""
    service = ComplianceService()
    lines = [
        "HEALTHY BITES OAT COOKIES",
        "NUTRITION INFORMATION",
        "Serving Size: 30 g",
        "Servings Per Container: Approx 16",
        "Per Serving: Energy 130 kcal, Protein 3 g, Fat 4 g",
        "NET WEIGHT: 500 g",
        "MRP Rs. 150.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 09/2026",
        "MANUFACTURED BY: HEALTH FOODS LTD, MUMBAI 400001",
        "CONSUMER CARE: 1800-222-333 / care@healthfoods.in",
        "FSSAI LIC NO 10019022000555"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    qty_field = next(f for f in report.fields if f.field_id == "net_quantity")
    assert qty_field.verdict == ComplianceVerdict.COMPLIANT.value
    # Must extract the 500 g net quantity, NOT the 30 g serving size or 3 g protein
    assert "500 g" in qty_field.extracted_value
    assert "30 g" not in qty_field.extracted_value
    assert "3 g" not in qty_field.extracted_value


def test_compliance_engine_nutrition_panel_only_not_detected():
    """Verify that if only nutrition Serving Size exists with no genuine Net Quantity declaration, it returns 'Not detected'."""
    service = ComplianceService()
    lines = [
        "CRUNCHY CRACKERS",
        "NUTRITION FACTS",
        "Serving Size: 28.35 g (1 oz)",
        "Servings Per Pack: 10",
        "Amount Per Serving: Calories 120",
        "Total Fat: 5 g",
        "Sodium: 140 mg",
        "Total Carbohydrate: 18 g",
        "Protein: 2 g",
        "MRP Rs. 60.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 08/2026",
        "MANUFACTURED BY: BAKERIES LTD, BENGALURU 560001",
        "CONSUMER CARE: 1800-444-555 / help@bakeries.com",
        "FSSAI 10018043000123"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    qty_field = next(f for f in report.fields if f.field_id == "net_quantity")
    # Must NOT substitute the 28.35g serving size or any nutrient amount
    assert qty_field.extracted_value == "Not detected"
    assert qty_field.verdict == ComplianceVerdict.NON_COMPLIANT.value
    assert "Rule 6(1)(b)" in qty_field.reason


def test_compliance_engine_manufacturer_only_name_no_false_pin_claim():
    """Verify that if only company name is present without an address or PIN, the verdict is Advisory and does NOT claim verified PIN."""
    service = ComplianceService()
    lines = [
        "PARLE-G GLUCOSE BISCUITS",
        "MARKETED BY: PARLE PRODUCTS PVT LTD",
        "NET WT: 250 g",
        "MRP Rs. 25.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 08/2026",
        "CARE: 1800-222-111 / care@parle.biz",
        "FSSAI 10012022000111"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    mfg_field = next(f for f in report.fields if f.field_id == "manufacturer_address")
    assert "PARLE PRODUCTS PVT LTD" in mfg_field.extracted_value
    # Extracted value does not have a PIN code
    assert not any(c.isdigit() for c in mfg_field.extracted_value.split(":")[-1])
    assert mfg_field.verdict == ComplianceVerdict.ADVISORY.value
    # Crucial assertion: Reason must NOT claim that a PIN code was verified!
    assert "PIN code verified" not in mfg_field.reason
    assert "missing" in mfg_field.reason.lower()


def test_compliance_engine_manufacturer_multiline_address_captured():
    """Verify that multi-line address blocks under manufacturer/marketer are captured into extracted_value."""
    service = ComplianceService()
    lines = [
        "PARLE-G GLUCOSE BISCUITS",
        "MARKETED BY: PARLE PRODUCTS PVT LTD",
        "NORTH WING, VILE PARLE (E)",
        "MUMBAI 400057, MAHARASHTRA",
        "NET WT: 250 g",
        "MRP Rs. 25.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 08/2026",
        "CARE: 1800-222-111 / care@parle.biz",
        "FSSAI 10012022000111"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    mfg_field = next(f for f in report.fields if f.field_id == "manufacturer_address")
    # All parts must be captured in the extracted value itself
    assert "PARLE PRODUCTS PVT LTD" in mfg_field.extracted_value
    assert "NORTH WING" in mfg_field.extracted_value or "VILE PARLE" in mfg_field.extracted_value
    assert "400057" in mfg_field.extracted_value
    assert mfg_field.verdict == ComplianceVerdict.COMPLIANT.value
    assert "400057" in mfg_field.reason


def test_compliance_engine_manufacturer_unattached_address_captured():
    """Verify that unattached postal address elsewhere on the label is captured as part of the manufacturer field."""
    service = ComplianceService()
    lines = [
        "SWEET DELIGHT CHOCOLATE",
        "MARKETED BY: DELIGHT BRANDS PVT LTD",
        "COMMODITY: CONFECTIONERY",
        "REGD. OFFICE: 45 PARK STREET",
        "KOLKATA 700016, WEST BENGAL",
        "NET WT: 150 g",
        "MRP Rs. 80.00 (INCL. OF ALL TAXES)",
        "MFG DATE: 07/2026",
        "CARE: 1800-999-888 / care@delight.in",
        "FSSAI 10017011000999"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    mfg_field = next(f for f in report.fields if f.field_id == "manufacturer_address")
    assert "DELIGHT BRANDS PVT LTD" in mfg_field.extracted_value
    assert "700016" in mfg_field.extracted_value
    assert mfg_field.verdict == ComplianceVerdict.COMPLIANT.value
    assert "700016" in mfg_field.reason


def test_compliance_engine_skincare_non_food_no_fssai():
    """Skincare/cosmetic product must be classified non-food and FSSAI check must be skipped."""
    service = ComplianceService()
    lines = [
        "K-GLOW HYDRATING FACIAL SERUM",
        "NET CONTENT: 50 ml",
        "MFG BY: SEOUL COSMETICS CO. LTD., SOUTH KOREA",
        "CUSTOMER CARE: 1800-111-222 / care@kglow.in",
        "MRP: Rs. 2790/- (INCL. OF ALL TAXES)",
        "MFD. DATE: 02/2024",
        "USE BEFORE: 02/2027",
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    # FSSAI must NOT appear for a cosmetic product
    assert not any(f.field_id == "fssai_license" for f in report.fields), \
        "FSSAI check must be skipped for skincare/cosmetic non-food products"
    assert report.total_checks == 5


def test_compliance_engine_consumer_care_plus91_phone_and_email():
    """Consumer care block with +91 phone and standard email must be marked Compliant."""
    service = ComplianceService()
    lines = [
        "BEAUTY PRODUCT",
        "NET WT: 200 ml",
        "MFG BY: XYZ PVT LTD, MUMBAI 400001",
        "MRP Rs. 450 (INCL. OF ALL TAXES)",
        "MFD. DATE: 03/2025",
        "TEL: +91-124-4567890",
        "EMAIL: customercare@xyz.in",
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    care_field = next(f for f in report.fields if f.field_id == "consumer_care")
    assert care_field.verdict == ComplianceVerdict.COMPLIANT.value, \
        f"Expected Compliant but got: {care_field.verdict} | value: {care_field.extracted_value}"
    assert "+91" in care_field.extracted_value
    assert "@" in care_field.extracted_value


def test_compliance_engine_mrp_not_from_rc_no():
    """MRP must never be extracted from RC NO. or registration certificate numbers."""
    service = ComplianceService()
    lines = [
        "SOME SKINCARE SERUM",
        "NET WT: 30 ml",
        "RC NO.: COS-003907",
        "MRP: Rs. 2790/- (INCL. OF ALL TAXES)",
        "MFD. DATE: 01/2025",
        "MFG BY: IMPORTER PVT LTD, DELHI 110001",
        "TEL: 1800-222-333 / care@importer.in",
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    mrp_field = next(f for f in report.fields if f.field_id == "mrp_declaration")
    assert "2790" in mrp_field.extracted_value, \
        f"MRP should extract 2790, got: {mrp_field.extracted_value}"
    assert "003907" not in mrp_field.extracted_value, \
        f"MRP must NOT contain RC NO. digits, got: {mrp_field.extracted_value}"


def test_compliance_engine_mfg_date_not_from_use_before():
    """Manufacture date must never be extracted from 'Use Before' or expiry lines."""
    service = ComplianceService()
    lines = [
        "FACE CREAM",
        "USE BEFORE: 02/2027",
        "MFD. DATE: 02/2024",
        "MFG BY: CREAM CO., PUNE 411001",
        "NET WT: 100 g",
        "MRP Rs. 250 (INCL. OF ALL TAXES)",
        "TEL: 1800-333-444 / care@cream.in",
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    mfg_field = next(f for f in report.fields if f.field_id == "mfg_date")
    assert "02/2024" in mfg_field.extracted_value, \
        f"Mfg date should be 02/2024, got: {mfg_field.extracted_value}"
    assert "02/2027" not in mfg_field.extracted_value, \
        f"Use Before date (02/2027) must never appear in mfg_date, got: {mfg_field.extracted_value}"
    assert mfg_field.verdict == ComplianceVerdict.COMPLIANT.value


def test_compliance_engine_skincare_full_scenario():
    """
    Full end-to-end skincare label regression test:
    - Foreign MFG BY (no Indian address)
    - Customer Care block with Indian address + PIN + +91 phone + email
    - RC NO. code (must NOT pollute MRP)
    - MRP with tax clause
    - Distinct MFD Date and Use Before (must not cross-contaminate)
    All 5 fields must be Compliant. No FSSAI check.
    """
    service = ComplianceService()
    lines = [
        "K-GLOW HYDRATING FACIAL SERUM",
        "NET CONTENT: 50 ml",
        "MFG BY: SEOUL COSMETICS CO. LTD., GANGNAM-GU, SEOUL, SOUTH KOREA",
        "FOR FEEDBACK / COMPLAINTS, CONTACT CUSTOMER CARE EXECUTIVE AT: BEAUTY IMPORTS INDIA PVT LTD",
        "PLOT NO. 45, UDYOG VIHAR PHASE IV, GURUGRAM, HARYANA 122015",
        "TEL: +91-124-4567890",
        "EMAIL: CUSTOMERCARE@BEAUTYIMPORTS.IN",
        "RC NO.: COS-003907",
        "MRP: Rs. 2790/- (INCL. OF ALL TAXES)",
        "MFD. DATE: 02/2024",
        "USE BEFORE: 02/2027",
        "BATCH NO.: B-2024/09"
    ]
    raw_text = "\n".join(lines)
    report = service.evaluate_compliance(raw_text, lines)

    # Must be non-food — no FSSAI check
    assert report.total_checks == 5
    assert not any(f.field_id == "fssai_license" for f in report.fields)

    # Manufacturer: should have Indian PIN from care block
    mfg_field = next(f for f in report.fields if f.field_id == "manufacturer_address")
    assert "SEOUL COSMETICS" in mfg_field.extracted_value
    assert "122015" in mfg_field.extracted_value
    assert mfg_field.verdict == ComplianceVerdict.COMPLIANT.value

    # Net quantity: 50 ml
    qty_field = next(f for f in report.fields if f.field_id == "net_quantity")
    assert "50 ml" in qty_field.extracted_value
    assert qty_field.verdict == ComplianceVerdict.COMPLIANT.value

    # MRP: Rs. 2790 — NOT RC NO.
    mrp_field = next(f for f in report.fields if f.field_id == "mrp_declaration")
    assert "2790" in mrp_field.extracted_value
    assert "003907" not in mrp_field.extracted_value
    assert mrp_field.verdict == ComplianceVerdict.COMPLIANT.value

    # Mfg date: 02/2024 — NOT Use Before 02/2027
    date_field = next(f for f in report.fields if f.field_id == "mfg_date")
    assert "02/2024" in date_field.extracted_value
    assert "02/2027" not in date_field.extracted_value
    assert date_field.verdict == ComplianceVerdict.COMPLIANT.value

    # Consumer care: +91 phone + email
    care_field = next(f for f in report.fields if f.field_id == "consumer_care")
    assert "+91" in care_field.extracted_value
    assert "@" in care_field.extracted_value
    assert care_field.verdict == ComplianceVerdict.COMPLIANT.value

    # Overall
    assert report.overall_verdict == ComplianceVerdict.COMPLIANT.value
