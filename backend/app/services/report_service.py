import os
import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from PIL import Image as PILImage

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# python-docx imports
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

logger = logging.getLogger(__name__)

# Base storage directory for scans
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "scans"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, letter[0] - 36, 32)

        # Footer text
        footer_text = "PackTrue Compliance Engine • Legal Metrology (Packaged Commodities) Rules, 2011"
        self.drawString(36, 20, footer_text)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 20, page_str)
        self.restoreState()


class ReportService:
    """Manages scan persistence and generates statutory PDF and DOCX reports."""

    def __init__(self):
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def save_scan(
        self,
        scan_id: str,
        filename: str,
        image_bytes: bytes,
        scan_result: dict,
        timestamp: str
    ) -> None:
        """Saves scan data in memory and to disk cache."""
        record = {
            "scan_id": scan_id,
            "filename": filename,
            "image_bytes": image_bytes,
            "scan_result": scan_result,
            "timestamp": timestamp,
        }
        self._memory_store[scan_id] = record

        # Persist to disk
        try:
            scan_folder = STORAGE_DIR / scan_id
            scan_folder.mkdir(parents=True, exist_ok=True)

            meta_file = scan_folder / "metadata.json"
            clean_result = {k: v for k, v in scan_result.items() if k != "image_bytes"}
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump({
                    "scan_id": scan_id,
                    "filename": filename,
                    "timestamp": timestamp,
                    "scan_result": clean_result,
                }, f, indent=2)

            ext = os.path.splitext(filename)[1] or ".png"
            img_file = scan_folder / f"evidence{ext}"
            with open(img_file, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            logger.warning(f"Failed to persist scan {scan_id} to disk: {e}")

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves scan data from memory or disk cache."""
        if scan_id in self._memory_store:
            return self._memory_store[scan_id]

        # Check disk
        scan_folder = STORAGE_DIR / scan_id
        meta_file = scan_folder / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                img_files = list(scan_folder.glob("evidence.*"))
                if img_files:
                    with open(img_files[0], "wb") as f:
                        img_bytes = img_files[0].read_bytes()
                else:
                    img_bytes = b""

                record = {
                    "scan_id": scan_id,
                    "filename": meta.get("filename", "label.png"),
                    "image_bytes": img_bytes,
                    "scan_result": meta.get("scan_result", {}),
                    "timestamp": meta.get("timestamp", ""),
                }
                self._memory_store[scan_id] = record
                return record
            except Exception as e:
                logger.error(f"Error loading scan {scan_id} from disk: {e}")

        return None

    def generate_pdf_report(self, scan_data: Dict[str, Any]) -> bytes:
        """Generates a professional Legal Metrology compliance audit report in PDF format."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=42
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        # Custom Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0284c7")
        )
        tagline_style = ParagraphStyle(
            "Tagline",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        meta_style = ParagraphStyle(
            "MetaText",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            alignment=2 # Right
        )
        section_h2 = ParagraphStyle(
            "SectionH2",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=6
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        table_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0f172a")
        )
        table_cell_mono = ParagraphStyle(
            "TableCellMono",
            parent=normal_style,
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a")
        )
        caption_style = ParagraphStyle(
            "FigureCaption",
            parent=normal_style,
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748b"),
            alignment=1 # Center
        )

        elements = []

        # 1. Header Banner
        header_table_data = [
            [
                Paragraph("<b>PackTrue</b><br/><font size=9 color='#475569'>Legal Metrology Packaged Commodities Pre-Screening</font>", title_style),
                Paragraph(f"<b>Scan ID:</b> <code>{scan_data['scan_id']}</code><br/><b>Timestamp:</b> {scan_data.get('timestamp', 'N/A')}<br/><b>Status:</b> AI-Assisted Pre-Screening — Requires Officer Confirmation", meta_style)
            ]
        ]
        header_table = Table(header_table_data, colWidths=[360, 180])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

        # Clear legal pre-screening notice
        disclaimer_style = ParagraphStyle(
            "ReportDisclaimer",
            parent=normal_style,
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569")
        )
        disclaimer_data = [
            [Paragraph("<b>Notice:</b> This is an automated pre-screening tool. Findings are not a legal determination and require confirmation by an authorized Legal Metrology officer before any enforcement action.", disclaimer_style)]
        ]
        disclaimer_table = Table(disclaimer_data, colWidths=[540])
        disclaimer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(disclaimer_table)
        elements.append(Spacer(1, 8))

        # 2. Overall Preliminary Assessment Callout
        result = scan_data.get("scan_result", {})
        compliance = result.get("compliance") or {}
        overall_verdict = compliance.get("overall_verdict", "Non-Compliant")
        summary = compliance.get("summary", "Statutory pre-screening assessment of mandatory declarations.")
        passed = compliance.get("passed_checks", 0)
        advisories = compliance.get("advisory_checks", 0)
        failed = compliance.get("failed_checks", 0)

        # Scan-level confidence/review recommendation signal
        img_quality = result.get("image_quality") or {}
        is_low_quality = bool(img_quality.get("enhancement_applied") or img_quality.get("is_blurry"))
        has_low_certainty = bool(result.get("average_confidence", 1.0) < 0.70 or result.get("requires_human_review"))
        is_low_confidence = is_low_quality or has_low_certainty

        if is_low_confidence:
            low_conf_style = ParagraphStyle(
                "LowConfAlert",
                parent=normal_style,
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=12,
                textColor=colors.HexColor("#92400e")
            )
            low_conf_data = [
                [Paragraph("⚠ <b>Low Confidence — Human Review Recommended:</b> Image quality was degraded or enhancement was applied during scanning. Pre-screening findings require officer physical confirmation.", low_conf_style)]
            ]
            low_conf_table = Table(low_conf_data, colWidths=[540])
            low_conf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fefce8")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(low_conf_table)
            elements.append(Spacer(1, 8))

        # Assessment theme colors
        if overall_verdict == "Compliant":
            v_bg = colors.HexColor("#ecfdf5")
            v_border = colors.HexColor("#10b981")
            v_text = colors.HexColor("#065f46")
            assessment_title = "PRELIMINARY ASSESSMENT: Compliant"
        elif "Advisory" in overall_verdict:
            v_bg = colors.HexColor("#fefce8")
            v_border = colors.HexColor("#eab308")
            v_text = colors.HexColor("#854d0e")
            assessment_title = "PRELIMINARY ASSESSMENT: Packaging Advisories Flagged"
        else:
            v_bg = colors.HexColor("#fef2f2")
            v_border = colors.HexColor("#ef4444")
            v_text = colors.HexColor("#991b1b")
            assessment_title = "PRELIMINARY ASSESSMENT: Potential Violations Flagged"

        verdict_p_style = ParagraphStyle(
            "VerdictText",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=v_text
        )
        verdict_summary_style = ParagraphStyle(
            "VerdictSum",
            parent=normal_style,
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=v_text
        )

        verdict_data = [
            [
                Paragraph(f"<b>{assessment_title}</b>", verdict_p_style),
                Paragraph(f"<b>Passed:</b> {passed}/6 &nbsp;|&nbsp; <b>Advisories:</b> {advisories} &nbsp;|&nbsp; <b>Violations:</b> {failed}", meta_style)
            ],
            [
                Paragraph(summary, verdict_summary_style),
                Paragraph(f"<b>File:</b> {scan_data.get('filename', 'Unknown')}", meta_style)
            ]
        ]
        verdict_table = Table(verdict_data, colWidths=[380, 160])
        verdict_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), v_bg),
            ('BOX', (0, 0), (-1, -1), 1.5, v_border),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.transparent),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(verdict_table)
        elements.append(Spacer(1, 10))

        # 3. Label Evidence Section (Attached original label image)
        image_bytes = scan_data.get("image_bytes")
        if image_bytes and len(image_bytes) > 0:
            try:
                pil_img = PILImage.open(BytesIO(image_bytes))
                orig_w, orig_h = pil_img.size
                aspect = orig_h / float(orig_w) if orig_w else 1.0

                # Fit into max 380 width x 160 height
                max_w = 340.0
                max_h = 160.0
                target_w = max_w
                target_h = max_w * aspect
                if target_h > max_h:
                    target_h = max_h
                    target_w = max_h / aspect

                img_flowable = RLImage(BytesIO(image_bytes), width=target_w, height=target_h)

                evidence_table_data = [
                    [Paragraph("<b>Figure 1: Visual Label Evidence Attached for Regulatory Records</b>", section_h2)],
                    [img_flowable],
                    [Paragraph(f"Submitted Packaging Artwork: <code>{scan_data.get('filename', 'label.png')}</code> ({orig_w}x{orig_h} px)", caption_style)]
                ]
                evidence_table = Table(evidence_table_data, colWidths=[540])
                evidence_table.setStyle(TableStyle([
                    ('ALIGN', (0, 1), (0, 1), 'CENTER'),
                    ('ALIGN', (0, 2), (0, 2), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(evidence_table)
                elements.append(Spacer(1, 8))
            except Exception as e:
                logger.warning(f"Failed to embed image in PDF: {e}")

        # 4. Mandatory Declarations Table
        elements.append(Paragraph("<b>Statutory Mandatory Declarations Pre-Screening Table</b>", section_h2))
        elements.append(Paragraph("<font size=8 color='#64748b'>Evaluated under Legal Metrology (Packaged Commodities) Rules, 2011 [Rule 6 & Rule 12]</font>", normal_style))
        elements.append(Spacer(1, 4))

        fields = compliance.get("fields", [])
        table_rows = [
            [
                Paragraph("<b>Mandatory Declaration & Citation</b>", table_cell_bold),
                Paragraph("<b>Extracted Value</b>", table_cell_bold),
                Paragraph("<b>Preliminary Status</b>", table_cell_bold),
                Paragraph("<b>Statutory Finding & Justification</b>", table_cell_bold),
            ]
        ]

        for field in fields:
            f_name = field.get("field_name", "Declaration")
            f_rule = field.get("rule_reference", "Rule 6")
            f_val = field.get("extracted_value") or "None detected"
            f_verdict = field.get("verdict", "Non-Compliant")
            f_reason = field.get("reason", "")

            if f_verdict == "Compliant":
                v_color = "#065f46"
                v_bg_cell = "#ecfdf5"
            elif "Advisory" in f_verdict:
                v_color = "#854d0e"
                v_bg_cell = "#fefce8"
            else:
                v_color = "#991b1b"
                v_bg_cell = "#fef2f2"

            table_rows.append([
                Paragraph(f"<b>{f_name}</b><br/><font size=7 color='#0284c7'>{f_rule}</font>", table_cell_style),
                Paragraph(f"<font color='#0f172a'>{f_val}</font>", table_cell_mono),
                Paragraph(f"<font color='{v_color}'><b>{f_verdict}</b></font>", table_cell_style),
                Paragraph(f"{f_reason}", table_cell_style),
            ])

        declarations_table = Table(table_rows, colWidths=[140, 120, 80, 200])
        declarations_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(declarations_table)
        elements.append(Spacer(1, 14))

        # 5. Enforcement Officer Verification Block
        officer_data = [
            [
                Paragraph("<b>Inspecting Legal Metrology Officer:</b> ___________________________", table_cell_style),
                Paragraph("<b>Official Seal / Signature:</b> ___________________________", table_cell_style)
            ],
            [
                Paragraph("<b>Designation & Jurisdiction:</b> ___________________________", table_cell_style),
                Paragraph("<b>Inspection Date & Determination:</b> ___________________________", table_cell_style)
            ]
        ]
        officer_table = Table(officer_data, colWidths=[270, 270])
        officer_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(KeepTogether([
            Paragraph("<b>Enforcement Officer Verification & Sign-off</b>", section_h2),
            officer_table
        ]))

        doc.build(elements, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    def generate_docx_report(self, scan_data: Dict[str, Any]) -> bytes:
        """Generates an editable Legal Metrology compliance audit report in DOCX format with officer notes section."""
        doc = docx.Document()

        # Set standard margins (0.75 in)
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)

        # Header Title
        title_p = doc.add_paragraph()
        run_title = title_p.add_run("PackTrue — Statutory Compliance Pre-Screening Report")
        run_title.bold = True
        run_title.font.size = Pt(18)
        run_title.font.color.rgb = RGBColor(2, 132, 199)

        sub_p = doc.add_paragraph()
        run_sub = sub_p.add_run("Legal Metrology (Packaged Commodities) Rules, 2011 • Department of Consumer Affairs")
        run_sub.font.size = Pt(9.5)
        run_sub.font.color.rgb = RGBColor(71, 85, 105)

        # Clear legal pre-screening notice
        disc_p = doc.add_paragraph()
        disc_run = disc_p.add_run(
            "Notice: This is an automated pre-screening tool. Findings are not a legal determination and require confirmation by an authorized Legal Metrology officer before any enforcement action."
        )
        disc_run.italic = True
        disc_run.font.size = Pt(8.5)
        disc_run.font.color.rgb = RGBColor(100, 116, 139)

        # Meta Details
        meta_table = doc.add_table(rows=2, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_table.autofit = True

        result = scan_data.get("scan_result", {})
        compliance = result.get("compliance") or {}
        overall_verdict = compliance.get("overall_verdict", "Non-Compliant")
        summary = compliance.get("summary", "Statutory pre-screening assessment of mandatory declarations.")
        passed = compliance.get("passed_checks", 0)
        advisories = compliance.get("advisory_checks", 0)
        failed = compliance.get("failed_checks", 0)

        # Scan-level confidence/review recommendation signal
        img_quality = result.get("image_quality") or {}
        is_low_quality = bool(img_quality.get("enhancement_applied") or img_quality.get("is_blurry"))
        has_low_certainty = bool(result.get("average_confidence", 1.0) < 0.70 or result.get("requires_human_review"))
        is_low_confidence = is_low_quality or has_low_certainty

        r0c0 = meta_table.rows[0].cells[0].paragraphs[0]
        r0c0.add_run(f"Scan ID: ").bold = True
        r0c0.add_run(scan_data.get("scan_id", "N/A"))

        r0c1 = meta_table.rows[0].cells[1].paragraphs[0]
        r0c1.add_run(f"Timestamp: ").bold = True
        r0c1.add_run(scan_data.get("timestamp", "N/A"))

        r1c0 = meta_table.rows[1].cells[0].paragraphs[0]
        r1c0.add_run(f"Submitted File: ").bold = True
        r1c0.add_run(scan_data.get("filename", "Unknown"))

        r1c1 = meta_table.rows[1].cells[1].paragraphs[0]
        r1c1.add_run(f"Status: ").bold = True
        r1c1.add_run("AI-Assisted Pre-Screening — Requires Officer Confirmation")

        doc.add_paragraph() # Spacer

        # Conditional Low Confidence Banner
        if is_low_confidence:
            conf_box = doc.add_table(rows=1, cols=1)
            conf_box.alignment = WD_TABLE_ALIGNMENT.CENTER
            c_cell = conf_box.rows[0].cells[0]
            c_cell.width = Inches(7.0)
            tcPr = c_cell._tc.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FEFCE8"/>')
            tcPr.append(shd)
            cp = c_cell.paragraphs[0]
            c_run = cp.add_run("⚠ Low Confidence — Human Review Recommended\n")
            c_run.bold = True
            c_run.font.size = Pt(10)
            c_run.font.color.rgb = RGBColor(180, 83, 9)
            sub_c = cp.add_run("Image quality was degraded or enhancement was applied during scanning. Pre-screening findings require officer physical confirmation.")
            sub_c.font.size = Pt(9)
            sub_c.font.color.rgb = RGBColor(146, 64, 14)
            doc.add_paragraph() # Spacer

        # Overall Preliminary Assessment Callout Box
        verdict_box = doc.add_table(rows=1, cols=1)
        verdict_box.alignment = WD_TABLE_ALIGNMENT.CENTER
        v_cell = verdict_box.rows[0].cells[0]
        v_cell.width = Inches(7.0)

        # Color shading and title on cell
        if overall_verdict == "Compliant":
            shading_color = "ECFDF5"
            assessment_title_docx = "PRELIMINARY ASSESSMENT: Compliant"
        elif "Advisory" in overall_verdict:
            shading_color = "FEFCE8"
            assessment_title_docx = "PRELIMINARY ASSESSMENT: Packaging Advisories Flagged"
        else:
            shading_color = "FEF2F2"
            assessment_title_docx = "PRELIMINARY ASSESSMENT: Potential Violations Flagged"

        tcPr = v_cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{shading_color}"/>')
        tcPr.append(shd)

        vp = v_cell.paragraphs[0]
        v_run = vp.add_run(f"{assessment_title_docx}\n")
        v_run.bold = True
        v_run.font.size = Pt(13)

        vp.add_run(f"{summary}\n\n")
        stats_run = vp.add_run(f"Checks Passed: {passed}/6   |   Packaging Advisories: {advisories}   |   Potential Violations Flagged: {failed}")
        stats_run.bold = True
        stats_run.font.size = Pt(9.5)

        doc.add_paragraph() # Spacer

        # 1. Attached Visual Evidence
        h1 = doc.add_heading("1. Visual Packaging Evidence", level=2)
        h1.runs[0].font.color.rgb = RGBColor(15, 23, 42)

        image_bytes = scan_data.get("image_bytes")
        if image_bytes and len(image_bytes) > 0:
            try:
                img_stream = BytesIO(image_bytes)
                doc.add_picture(img_stream, width=Inches(4.5))
                cap = doc.add_paragraph()
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cap_run = cap.add_run(f"Figure 1: Packaged commodity label submitted for statutory pre-screening ({scan_data.get('filename')})")
                cap_run.italic = True
                cap_run.font.size = Pt(8.5)
                cap_run.font.color.rgb = RGBColor(100, 116, 139)
            except Exception as e:
                logger.warning(f"Failed to embed picture in DOCX: {e}")

        # 2. Mandatory Declarations Audit Table
        h2 = doc.add_heading("2. Statutory Mandatory Declarations Checklist", level=2)
        h2.runs[0].font.color.rgb = RGBColor(15, 23, 42)

        fields = compliance.get("fields", [])
        table = doc.add_table(rows=1, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        hdr_cells = table.rows[0].cells
        headers = ["Statutory Declaration & Rule", "Extracted Value", "Preliminary Status", "Statutory Finding / Reason"]
        for i, title in enumerate(headers):
            hdr_cells[i].text = title
            hdr_cells[i].paragraphs[0].runs[0].bold = True
            hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            cell_tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
            hdr_shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="0284C7"/>')
            cell_tcPr.append(hdr_shd)

        for field in fields:
            row_cells = table.add_row().cells
            row_cells[0].text = f"{field.get('field_name', '')}\n({field.get('rule_reference', '')})"
            row_cells[1].text = field.get("extracted_value") or "None detected"
            row_cells[2].text = field.get("verdict", "")
            row_cells[3].text = field.get("reason", "")

        # Set column widths
        col_widths = [Inches(1.8), Inches(1.5), Inches(1.2), Inches(2.5)]
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = width

        doc.add_paragraph() # Spacer

        # 3. Enforcement Officer Notes & Manual Determination (Editable Section)
        h3 = doc.add_heading("3. Enforcement Officer Notes & Official Determination", level=2)
        h3.runs[0].font.color.rgb = RGBColor(15, 23, 42)

        doc.add_paragraph(
            "This editable section is reserved for the inspecting Legal Metrology officer to document manual findings, "
            "physical measurement verification results, administrative notices, or compound determinations."
        )

        officer_form = doc.add_table(rows=4, cols=2)
        officer_form.alignment = WD_TABLE_ALIGNMENT.CENTER
        officer_fields = [
            ("Inspecting Officer Name:", "Designation & ID:"),
            ("Station / District:", "Physical Inspection Date:"),
            ("Commodity Lot / Batch Verified:", "Statutory Action Recommended:"),
            ("Notice Ref / Summon No:", "Case Determination (Compound/Seize/Clear):"),
        ]
        for row_idx, (col1, col2) in enumerate(officer_fields):
            c1 = officer_form.rows[row_idx].cells[0].paragraphs[0]
            c1.add_run(f"{col1} ____________________________________").font.size = Pt(9.5)
            c2 = officer_form.rows[row_idx].cells[1].paragraphs[0]
            c2.add_run(f"{col2} ____________________________________").font.size = Pt(9.5)

        doc.add_paragraph() # Spacer

        # Notes Box
        doc.add_paragraph("Officer Observations & Final Regulatory Notes:").runs[0].bold = True
        notes_box = doc.add_table(rows=1, cols=1)
        notes_cell = notes_box.rows[0].cells[0]
        notes_cell.width = Inches(7.0)
        notes_p = notes_cell.paragraphs[0]
        notes_run = notes_p.add_run(
            "\n[ Enter officer notes, physical measurement observations, or compounded settlement remarks here... ]\n\n\n\n\n"
        )
        notes_run.italic = True
        notes_run.font.color.rgb = RGBColor(148, 163, 184)

        # Signature Line
        doc.add_paragraph()
        sig_p = doc.add_paragraph()
        sig_p.add_run(
            "Officer Signature: ___________________________________               Date: ________________________"
        ).bold = True

        out = BytesIO()
        doc.save(out)
        return out.getvalue()


# Singleton instance
report_service = ReportService()

def get_report_service() -> ReportService:
    return report_service
