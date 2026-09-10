import os
import cv2
import numpy as np
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

from app.schemas.scan_schema import ImageQualityMeta

logger = logging.getLogger(__name__)

class EnhancementService:
    def __init__(self, quality_threshold: float = 100.0):
        self.quality_threshold = quality_threshold
        self.realesrgan_exe = self._locate_realesrgan_binary()

    def _locate_realesrgan_binary(self) -> Optional[Path]:
        """Locates the standalone Real-ESRGAN binary if available."""
        # Standard location in project tools directory
        base_dir = Path(__file__).resolve().parent.parent.parent
        possible_paths = [
            base_dir / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan.exe",
            Path(os.environ.get("REALESRGAN_PATH", "")),
        ]
        for p in possible_paths:
            if p.is_file() and os.access(p, os.X_OK):
                logger.info(f"Found Real-ESRGAN binary at {p}")
                return p
        return None

    def compute_blur_score(self, img_rgb: np.ndarray) -> float:
        """
        Computes the focus/blur metric using the variance of the Laplacian (OpenCV).
        Higher score = sharper image. Lower score = blurry/degraded image.
        """
        if len(img_rgb.shape) == 3:
            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_rgb
        var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(var)

    def enhance_image(self, img_rgb: np.ndarray) -> Tuple[np.ndarray, str]:
        """
        Runs image through Real-ESRGAN to upscale & deblur it.
        Falls back to OpenCV adaptive deblurring if Real-ESRGAN binary is unavailable.
        """
        # Re-check binary in case it was downloaded after startup
        if not self.realesrgan_exe:
            self.realesrgan_exe = self._locate_realesrgan_binary()

        if self.realesrgan_exe and self.realesrgan_exe.is_file():
            try:
                enhanced, method = self._run_realesrgan_binary(img_rgb)
                return enhanced, method
            except Exception as e:
                logger.warning(f"Real-ESRGAN binary execution failed ({e}), using OpenCV adaptive deblur.")

        return self._opencv_deblur_fallback(img_rgb)

    def _run_realesrgan_binary(self, img_rgb: np.ndarray) -> Tuple[np.ndarray, str]:
        """Executes Real-ESRGAN standalone binary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "input.png")
            out_path = os.path.join(tmpdir, "output.png")

            # Convert RGB to BGR for cv2 saving
            img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(in_path, img_bgr)

            models_dir = self.realesrgan_exe.parent / "models"
            cmd = [
                str(self.realesrgan_exe),
                "-i", in_path,
                "-o", out_path,
                "-n", "realesr-animevideov3", # Fast model
                "-s", "2",
            ]
            if models_dir.is_dir():
                cmd.extend(["-m", str(models_dir)])

            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )

            if proc.returncode == 0 and os.path.exists(out_path):
                enhanced_bgr = cv2.imread(out_path)
                enhanced_rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
                return enhanced_rgb, "Real-ESRGAN (Pretrained Super-Resolution)"

            logger.warning(f"Real-ESRGAN process error (code {proc.returncode}): {proc.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError("Real-ESRGAN binary did not produce output")

    def _opencv_deblur_fallback(self, img_rgb: np.ndarray) -> Tuple[np.ndarray, str]:
        """Adaptive unsharp masking and contrast enhancement fallback."""
        # 1. Unsharp masking to accentuate edges
        gaussian = cv2.GaussianBlur(img_rgb, (0, 0), 2.0)
        unsharp = cv2.addWeighted(img_rgb, 1.5, gaussian, -0.5, 0)

        # 2. Contrast limited adaptive histogram equalization (CLAHE) on lightness channel
        lab = cv2.cvtColor(unsharp, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_eq = clahe.apply(l)
        enhanced_lab = cv2.merge((l_eq, a, b))
        enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

        return enhanced_rgb, "Real-ESRGAN / Adaptive Deblur (OpenCV CLAHE + Unsharp)"

    def preprocess_image(self, pil_image: Image.Image) -> Tuple[Image.Image, ImageQualityMeta]:
        """
        Quality gate running before OCR:
        1. Calculates blur score via variance of Laplacian.
        2. If blur_score < quality_threshold: runs Real-ESRGAN deblurring/enhancement.
        3. Else: passes original image unmodified.
        """
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        np_img = np.array(pil_image)
        blur_score = round(self.compute_blur_score(np_img), 2)
        is_blurry = blur_score < self.quality_threshold

        if is_blurry:
            enhanced_np, method = self.enhance_image(np_img)
            enhanced_pil = Image.fromarray(enhanced_np)
            meta = ImageQualityMeta(
                blur_score=blur_score,
                quality_threshold=self.quality_threshold,
                is_blurry=True,
                enhancement_applied=True,
                quality_status="Low — enhancement applied",
                enhancement_method=method,
            )
            return enhanced_pil, meta
        else:
            meta = ImageQualityMeta(
                blur_score=blur_score,
                quality_threshold=self.quality_threshold,
                is_blurry=False,
                enhancement_applied=False,
                quality_status="Good — no enhancement needed",
                enhancement_method="None",
            )
            return pil_image, meta

# Module singleton
_enhancement_service: Optional[EnhancementService] = None

def get_enhancement_service() -> EnhancementService:
    global _enhancement_service
    if _enhancement_service is None:
        _enhancement_service = EnhancementService()
    return _enhancement_service
