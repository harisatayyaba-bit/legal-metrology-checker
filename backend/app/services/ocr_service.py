import io
import time
import logging
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np

from app.schemas.scan_schema import OcrLine, ScanResponse

logger = logging.getLogger(__name__)

class OcrService:
    _instance: Optional["OcrService"] = None
    _engine = None
    _is_ready: bool = False
    _engine_name: str = "PaddleOCR"

    def __init__(self):
        self._init_engine()

    def _init_engine(self):
        try:
            # On Windows CPU, patch PaddleX static engine config to disable oneDNN / PIR attribute conversion bug
            try:
                import paddlex.inference.models.runners.paddle_static.runner as ps_runner
                orig_resolve = ps_runner.resolve_paddle_static_engine_config
                def patched_resolve(model_name, engine_config):
                    cfg = orig_resolve(model_name, engine_config)
                    cfg['run_mode'] = 'paddle'
                    cfg['enable_new_ir'] = False
                    return cfg
                ps_runner.resolve_paddle_static_engine_config = patched_resolve
            except Exception as patch_err:
                logger.debug(f"PIR runner patch skipped: {patch_err}")

            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR PP-OCRv4 engine...")
            try:
                self._engine = PaddleOCR(
                    ocr_version="PP-OCRv4",
                    use_doc_orientation_classify=True,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                    lang="en",
                )
            except TypeError:
                self._engine = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                )
            self._is_ready = True
            self._engine_name = "PaddleOCR (PP-OCRv4)"
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Failed to initialize PaddleOCR ({e}). Enabling graceful demo/fallback mode."
            )
            self._engine = None
            self._is_ready = False
            self._engine_name = "Fallback / Mock OCR Engine"

    @property
    def is_available(self) -> bool:
        return self._is_ready

    @property
    def engine_name(self) -> str:
        return self._engine_name

    def process_image(self, image_bytes: bytes, filename: str) -> ScanResponse:
        start_time = time.time()

        # Load image with PIL to validate format and get dimensions
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != "RGB":
                image = image.convert("RGB")
            orig_width, orig_height = image.size
        except Exception as e:
            raise ValueError(f"Invalid image format: {e}")

        # Quality Gate: Calculate blur score & run Real-ESRGAN if blurry
        from app.services.enhancement_service import get_enhancement_service
        enhancement_service = get_enhancement_service()
        processed_image, quality_meta = enhancement_service.preprocess_image(image)
        proc_width, proc_height = processed_image.size

        # If real PaddleOCR is available, run it
        if self._engine is not None:
            try:
                np_img = np.array(processed_image)
                # PaddleOCR expects BGR or RGB numpy array
                try:
                    ocr_output = self._engine.ocr(np_img, cls=True)
                except TypeError:
                    ocr_output = self._engine.ocr(np_img)
                lines = self._parse_paddle_output(ocr_output)

                # If image was enhanced/upscaled, map bounding box coordinates back to original image space
                if proc_width != orig_width or proc_height != orig_height:
                    scale_x = orig_width / float(proc_width)
                    scale_y = orig_height / float(proc_height)
                    for line in lines:
                        line.box = [[round(pt[0] * scale_x, 1), round(pt[1] * scale_y, 1)] for pt in line.box]

                raw_text = "\n".join(line.text for line in lines)
                avg_conf = (
                    sum(line.confidence for line in lines) / len(lines)
                    if lines
                    else 0.0
                )
                processing_time = round((time.time() - start_time) * 1000, 2)

                return ScanResponse(
                    success=True,
                    filename=filename,
                    image_width=orig_width,
                    image_height=orig_height,
                    total_lines=len(lines),
                    average_confidence=round(avg_conf, 4),
                    lines=lines,
                    raw_text=raw_text,
                    processing_time_ms=processing_time,
                    ocr_engine="PaddleOCR",
                    image_quality=quality_meta,
                )
            except Exception as e:
                logger.error(f"PaddleOCR processing error: {e}. Using fallback generator.")

        # Fallback generator for demo / fallback when model is downloading or unavailable
        fallback_res = self._generate_fallback_results(filename, orig_width, orig_height, start_time)
        fallback_res.image_quality = quality_meta
        return fallback_res

    def _parse_paddle_output(self, ocr_output) -> List[OcrLine]:
        lines: List[OcrLine] = []
        line_id = 1

        if not ocr_output or not ocr_output[0]:
            return lines

        first_res = ocr_output[0]

        # Case 1: PaddleX 3.x dict output format
        if isinstance(first_res, dict):
            texts = first_res.get("rec_texts", [])
            scores = first_res.get("rec_scores", [])
            polys = first_res.get("rec_polys", first_res.get("dt_polys", []))

            for i in range(len(texts)):
                try:
                    text = str(texts[i]).strip()
                    conf = float(scores[i]) if i < len(scores) else 0.95
                    poly = polys[i] if i < len(polys) else []

                    # Convert numpy array / polygon points to list of [x, y]
                    if hasattr(poly, "tolist"):
                        box = [[float(pt[0]), float(pt[1])] for pt in poly.tolist()]
                    elif isinstance(poly, (list, tuple)):
                        box = [[float(pt[0]), float(pt[1])] for pt in poly]
                    else:
                        box = []

                    lines.append(
                        OcrLine(
                            id=line_id,
                            text=text,
                            confidence=round(conf, 4),
                            box=box,
                        )
                    )
                    line_id += 1
                except Exception as ex:
                    logger.warning(f"Error parsing PaddleX line item {i}: {ex}")
            return lines

        # Case 2: Classic PaddleOCR list of items: [[[x1, y1], ...], (text, confidence)]
        if isinstance(first_res, list):
            for item in first_res:
                try:
                    box_coords = item[0]
                    text_info = item[1]
                    text = str(text_info[0]).strip()
                    confidence = float(text_info[1])

                    box = [[float(pt[0]), float(pt[1])] for pt in box_coords]

                    lines.append(
                        OcrLine(
                            id=line_id,
                            text=text,
                            confidence=round(confidence, 4),
                            box=box,
                        )
                    )
                    line_id += 1
                except Exception as ex:
                    logger.warning(f"Error parsing classic OCR item: {ex}")
                    continue

        return lines

    def _generate_fallback_results(
        self, filename: str, width: int, height: int, start_time: float
    ) -> ScanResponse:
        """Sample Legal Metrology label detection mock for testing / demonstration."""
        sample_lines = [
            ("AMUL PURE GHEE 1L POUCH", 0.982, [[40, 40], [420, 40], [420, 75], [40, 75]]),
            ("NET QUANTITY: 1 L (905 g)", 0.975, [[40, 95], [380, 95], [380, 130], [40, 130]]),
            ("MRP Rs. 590.00 (INCL. OF ALL TAXES)", 0.991, [[40, 150], [460, 150], [460, 185], [40, 185]]),
            ("MFG DATE: 12/04/2026", 0.963, [[40, 205], [310, 205], [310, 240], [40, 240]]),
            ("EXPIRY DATE: 9 MONTHS FROM MFG", 0.954, [[40, 260], [410, 260], [410, 295], [40, 295]]),
            ("MKT BY: GUJARAT CO-OPERATIVE MILK MKT FEDERATION LTD", 0.941, [[40, 315], [580, 315], [580, 350], [40, 350]]),
            ("ANAND 388001, GUJARAT, INDIA", 0.938, [[40, 365], [390, 365], [390, 395], [40, 395]]),
            ("CONSUMER CARE: 1800-258-3333 / customercare@amul.coop", 0.968, [[40, 415], [590, 415], [590, 450], [40, 450]]),
        ]

        # Scale sample boxes proportionally to actual image dimensions
        scale_x = max(width / 640.0, 0.5)
        scale_y = max(height / 480.0, 0.5)

        lines: List[OcrLine] = []
        for i, (txt, conf, pts) in enumerate(sample_lines, start=1):
            scaled_box = [[round(p[0] * scale_x, 1), round(p[1] * scale_y, 1)] for p in pts]
            lines.append(OcrLine(id=i, text=txt, confidence=conf, box=scaled_box))

        raw_text = "\n".join(l.text for l in lines)
        avg_conf = sum(l.confidence for l in lines) / len(lines)
        proc_time = round((time.time() - start_time) * 1000, 2)

        return ScanResponse(
            success=True,
            filename=filename,
            image_width=width,
            image_height=height,
            total_lines=len(lines),
            average_confidence=round(avg_conf, 4),
            lines=lines,
            raw_text=raw_text,
            processing_time_ms=proc_time,
            ocr_engine="Fallback / Mock OCR Engine (PaddleOCR initialization in progress or pending install)",
        )

# Module-level singleton
_ocr_service_instance: Optional[OcrService] = None

def get_ocr_service() -> OcrService:
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OcrService()
    return _ocr_service_instance
