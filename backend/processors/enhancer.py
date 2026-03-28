"""
PixelForge · processors/enhancer.py
Realistic photo enhancement.

Pipeline
  1. fastNlMeansDenoisingColored  — gentle noise removal.
  2. CLAHE on LAB L-channel       — adaptive local contrast (clip=1.8).
  3. Masked unsharp masking       — sharpens only textured regions;
                                    flat areas (sky, fabric) are protected
                                    via a Laplacian flatness mask to avoid
                                    the circular wave artifact.
  4. Saturation boost             — +12% vibrance via HSV.
"""

import cv2
import numpy as np

import image_io
from config import (
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID,
    DENOISE_H,
    DENOISE_H_COLOR,
    DENOISE_SEARCH_WIN,
    DENOISE_TEMPLATE_WIN,
    ENHANCE_SAT_BOOST,
    UNSHARP_BLUR_W,
    UNSHARP_FLAT_THRESH,
    UNSHARP_SHARP_W,
    UNSHARP_SIGMA,
)


class Enhancer:

    def process(self, raw: bytes) -> tuple[bytes, int]:
        original = image_io.decode(raw)
        img = self._denoise(original)
        img = self._clahe(img)
        img = self._masked_unsharp(img)
        img = self._vibrance(img)
        score = self._score(original, img)
        return image_io.to_jpeg(img), score

    # ── pipeline steps ─────────────────────────────────────────────────────────

    @staticmethod
    def _denoise(img: np.ndarray) -> np.ndarray:
        return cv2.fastNlMeansDenoisingColored(
            img, None,
            h=DENOISE_H,
            hColor=DENOISE_H_COLOR,
            templateWindowSize=DENOISE_TEMPLATE_WIN,
            searchWindowSize=DENOISE_SEARCH_WIN,
        )

    @staticmethod
    def _clahe(img: np.ndarray) -> np.ndarray:
        lab     = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l       = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID).apply(l)
        return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    @staticmethod
    def _masked_unsharp(img: np.ndarray) -> np.ndarray:
        """
        Unsharp masking applied only where the image has texture.
        Flat regions (Laplacian variance < UNSHARP_FLAT_THRESH per tile) are
        blended back toward the original to prevent wave/circular artefacts on
        uniform areas like clear sky or plain fabric.
        """
        blurred  = cv2.GaussianBlur(img, (0, 0), sigmaX=UNSHARP_SIGMA)
        sharpened = cv2.addWeighted(img, UNSHARP_SHARP_W, blurred, UNSHARP_BLUR_W, 0)

        # Build a per-pixel texture mask from the L channel
        gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        lap    = cv2.Laplacian(gray, cv2.CV_32F)
        lap_sq = lap ** 2

        # Local variance via box filter (surrogate for "is this region textured?")
        tile  = 32
        local_var = cv2.boxFilter(lap_sq, -1, (tile, tile))
        local_var = np.sqrt(np.clip(local_var, 0, None))

        # Normalise to 0-1; values below threshold → 0 (protect flat areas)
        mask = np.clip((local_var - UNSHARP_FLAT_THRESH) / (UNSHARP_FLAT_THRESH * 4), 0, 1)
        mask = cv2.GaussianBlur(mask, (31, 31), 0)   # smooth mask edges
        mask3 = np.stack([mask] * 3, axis=-1)

        result = (sharpened.astype(np.float32) * mask3 +
                  img.astype(np.float32) * (1.0 - mask3))
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _vibrance(img: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * ENHANCE_SAT_BOOST, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    @staticmethod
    def _score(original: np.ndarray, result: np.ndarray) -> int:
        def lap(img: np.ndarray) -> float:
            return cv2.Laplacian(
                cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F
            ).var()

        ratio    = lap(result) / max(lap(original), 1.0)
        in_std   = float(cv2.cvtColor(original, cv2.COLOR_BGR2GRAY).std())
        out_std  = float(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).std())
        contrast = out_std / max(in_std, 1.0)
        combined = ratio * 0.65 + contrast * 0.35
        return min(99, max(55, int(50 + (combined - 1.0) * 28)))
