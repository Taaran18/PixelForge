"""
PixelForge · processors/restoration.py
Category: Restoration & Repair

Tools
  super_resolution  — DNN upscaling (EDSR/ESPCN/FSRCNN) via opencv-contrib
                      falls back to Lanczos4 when the .pb model is absent
  deblur            — Wiener deconvolution in frequency domain
  dejpeg            — NL-Means tuned for JPEG block-noise removal
  inpaint           — auto-detect damage mask + Telea inpainting
"""

import logging
import os

import cv2
import numpy as np

import image_io
from config import (
    JPEG_QUALITY,
    SR_DEFAULT_SCALE,
    SR_MODEL_DIR,
    SR_MODEL_NAME,
)

log = logging.getLogger("pixelforge.restoration")

# Pre-build SR model mapping: (name, scale) → filename
_SR_MODELS = {
    ("EDSR",   2): "EDSR_x2.pb",
    ("EDSR",   4): "EDSR_x4.pb",
    ("ESPCN",  2): "ESPCN_x2.pb",
    ("ESPCN",  4): "ESPCN_x4.pb",
    ("FSRCNN", 2): "FSRCNN_x2.pb",
    ("FSRCNN", 4): "FSRCNN_x4.pb",
    ("LAPSRN", 2): "LapSRN_x2.pb",
    ("LAPSRN", 4): "LapSRN_x4.pb",
}


class RestorationProcessor:

    # ── Super Resolution ──────────────────────────────────────────────────────
    def super_resolution(self, raw: bytes, scale: int = SR_DEFAULT_SCALE) -> tuple[bytes, int]:
        img   = image_io.decode(raw)
        scale = int(scale) if scale in (2, 4) else SR_DEFAULT_SCALE

        model_file = os.path.join(
            SR_MODEL_DIR, _SR_MODELS.get((SR_MODEL_NAME, scale), "")
        )

        if os.path.isfile(model_file):
            try:
                sr = cv2.dnn_superres.DnnSuperResImpl_create()
                sr.readModel(model_file)
                sr.setModel(SR_MODEL_NAME.lower(), scale)
                result = sr.upsample(img)
                log.info("SR via DNN (%s x%d)", SR_MODEL_NAME, scale)
            except Exception as exc:
                log.warning("DNN SR failed (%s) — using Lanczos4 fallback", exc)
                result = self._lanczos_upscale(img, scale)
        else:
            log.info("SR model not found at %s — using Lanczos4 fallback", model_file)
            result = self._lanczos_upscale(img, scale)

        h_in, w_in = img.shape[:2]
        h_out, w_out = result.shape[:2]
        actual_scale = h_out / max(h_in, 1)
        score = min(99, max(70, int(70 + actual_scale * 8)))
        return image_io.to_jpeg(result), score

    @staticmethod
    def _lanczos_upscale(img: np.ndarray, scale: int) -> np.ndarray:
        h, w = img.shape[:2]
        return cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_LANCZOS4)

    # ── Deblur (Wiener deconvolution) ─────────────────────────────────────────
    def deblur(self, raw: bytes, snr: float = 25.0) -> tuple[bytes, int]:
        """
        Frequency-domain Wiener filter.
        snr (signal-to-noise ratio estimate): higher = trust signal more = sharper
        """
        img    = image_io.decode(raw)
        result = np.zeros_like(img)

        for c in range(3):
            ch    = img[:, :, c].astype(np.float64)
            F     = np.fft.fft2(ch)
            # Simple motion-blur PSF estimate (5px horizontal)
            psf        = np.zeros_like(ch)
            psf[0, :5] = 1.0 / 5
            PSF        = np.fft.fft2(psf)
            PSF_conj   = np.conj(PSF)
            denom      = PSF_conj * PSF + (1.0 / snr)
            wiener     = PSF_conj / denom
            restored   = np.fft.ifft2(F * wiener).real
            result[:, :, c] = np.clip(restored, 0, 255).astype(np.uint8)

        # Sharpness improvement score
        def lap(x): return cv2.Laplacian(
            cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        ratio = lap(result) / max(lap(img), 1.0)
        score = min(99, max(60, int(60 + ratio * 15)))
        return image_io.to_jpeg(result), score

    # ── JPEG Artefact Removal ─────────────────────────────────────────────────
    def dejpeg(self, raw: bytes) -> tuple[bytes, int]:
        """
        NL-Means with parameters tuned for JPEG block-noise:
        higher h + large template window to average over block boundaries.
        """
        img    = image_io.decode(raw)
        result = cv2.fastNlMeansDenoisingColored(
            img, None,
            h=10,
            hColor=10,
            templateWindowSize=9,
            searchWindowSize=27,
        )
        # Gentle sharpening to recover any edge softening
        blurred = cv2.GaussianBlur(result, (0, 0), sigmaX=0.8)
        result  = cv2.addWeighted(result, 1.2, blurred, -0.2, 0)

        def lap(x): return cv2.Laplacian(
            cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        ratio = lap(result) / max(lap(img), 1.0)
        score = min(99, max(60, int(62 + ratio * 18)))
        return image_io.to_jpeg(result), score

    # ── Auto Inpaint ──────────────────────────────────────────────────────────
    def inpaint(self, raw: bytes, radius: int = 8) -> tuple[bytes, int]:
        """
        Auto-detect damage mask from:
          - Very dark blobs (dust, scratches): near-black isolated pixels
          - Very bright blobs (burn marks, sensor dust): near-white clusters
        Then fill with cv2.INPAINT_TELEA.
        """
        img  = image_io.decode(raw)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect dark artefacts (scratches)
        _, dark_mask  = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY_INV)
        # Detect bright artefacts (dust, glare spots)
        _, light_mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)

        mask = cv2.bitwise_or(dark_mask, light_mask)

        # Morphological open to remove noise from mask
        k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

        # Only inpaint if meaningful damage found (>0.05% of pixels)
        damage_frac = float((mask > 0).mean())
        if damage_frac < 0.0005:
            # Nothing to fix — return original
            return image_io.to_jpeg(img), 95

        result = cv2.inpaint(img, mask, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)

        score = min(99, max(65, int(65 + (1.0 - damage_frac * 10) * 30)))
        return image_io.to_jpeg(result), score
