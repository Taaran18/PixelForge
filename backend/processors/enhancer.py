"""
PixelForge · processors/enhancer.py
Realistic photo enhancement.

Pipeline
  1. fastNlMeansDenoisingColored  — noise removal (h=5, hColor=5).
  2. Adaptive CLAHE on LAB L-channel — clip limit scaled to input contrast:
       flat/washed-out images → high clip; contrasty images → low clip.
  3. Masked unsharp masking       — sharpens only textured regions;
                                    flat areas (sky, fabric) are protected
                                    via a Laplacian flatness mask to avoid
                                    the circular wave artifact.
  4. Selective vibrance           — boosts dull/muted colours strongly;
                                    already-vivid pixels are left untouched
                                    (prevents over-saturated skies / neon skin).

Score (0–99) is a perceptual blend of:
  - Sharpness improvement  (Laplacian variance ratio)  — 50%
  - Contrast improvement   (luminance std-dev ratio)   — 30%
  - Saturation improvement (mean saturation ratio)     — 20%
"""

import cv2
import numpy as np

import image_io
from config import (
    CLAHE_CLIP_HIGH,
    CLAHE_CLIP_LOW,
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID,
    DENOISE_H,
    DENOISE_H_COLOR,
    DENOISE_SEARCH_WIN,
    DENOISE_TEMPLATE_WIN,
    ENHANCE_VIBRANCE_STRENGTH,
    UNSHARP_BLUR_W,
    UNSHARP_FLAT_THRESH,
    UNSHARP_SHARP_W,
    UNSHARP_SIGMA,
)


class Enhancer:

    def process(self, raw: bytes) -> tuple[bytes, int]:
        original = image_io.decode(raw)
        img = self._denoise(original)
        img = self._adaptive_clahe(img)
        img = self._masked_unsharp(img)
        img = self._selective_vibrance(img)
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
    def _adaptive_clahe(img: np.ndarray) -> np.ndarray:
        """
        Measure the input image's luminance standard deviation to decide
        how aggressively to apply CLAHE.

        - Low contrast (std < 40):  boost hard  → CLAHE_CLIP_HIGH
        - High contrast (std > 80): boost gently → CLAHE_CLIP_LOW
        - In between: linear interpolation
        """
        lab      = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b  = cv2.split(lab)

        lum_std = float(l.std())
        t = np.clip((lum_std - 40.0) / 40.0, 0.0, 1.0)   # 0 = flat, 1 = contrasty
        clip = CLAHE_CLIP_HIGH * (1.0 - t) + CLAHE_CLIP_LOW * t

        l = cv2.createCLAHE(clipLimit=clip, tileGridSize=CLAHE_TILE_GRID).apply(l)
        return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    @staticmethod
    def _masked_unsharp(img: np.ndarray) -> np.ndarray:
        """
        Unsharp masking applied only where the image has texture.
        Flat regions (Laplacian variance < UNSHARP_FLAT_THRESH per tile) are
        blended back toward the original to prevent wave/circular artefacts on
        uniform areas like clear sky or plain fabric.
        """
        blurred   = cv2.GaussianBlur(img, (0, 0), sigmaX=UNSHARP_SIGMA)
        sharpened = cv2.addWeighted(img, UNSHARP_SHARP_W, blurred, UNSHARP_BLUR_W, 0)

        # Build a per-pixel texture mask from the L channel
        gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        lap       = cv2.Laplacian(gray, cv2.CV_32F)
        lap_sq    = lap ** 2

        # Local variance via box filter (surrogate for "is this region textured?")
        tile      = 32
        local_var = cv2.boxFilter(lap_sq, -1, (tile, tile))
        local_var = np.sqrt(np.clip(local_var, 0, None))

        # Normalise to 0–1; values below threshold → 0 (protect flat areas)
        mask  = np.clip((local_var - UNSHARP_FLAT_THRESH) / (UNSHARP_FLAT_THRESH * 4), 0, 1)
        mask  = cv2.GaussianBlur(mask, (31, 31), 0)   # smooth mask edges
        mask3 = np.stack([mask] * 3, axis=-1)

        result = (sharpened.astype(np.float32) * mask3 +
                  img.astype(np.float32) * (1.0 - mask3))
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _selective_vibrance(img: np.ndarray) -> np.ndarray:
        """
        Selective vibrance: pixels with low saturation receive a large boost,
        pixels that are already vivid receive almost none.

        boost_factor = 1 + strength * (1 - s_normalised)

        At s=0   → boost ≈ 1 + strength   (maximum lift for grey/dull tones)
        At s=255 → boost ≈ 1.0            (fully vivid pixels untouched)
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        s   = hsv[:, :, 1]
        s_norm  = s / 255.0                                       # 0-1
        boost   = 1.0 + ENHANCE_VIBRANCE_STRENGTH * (1.0 - s_norm)
        hsv[:, :, 1] = np.clip(s * boost, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    @staticmethod
    def _score(original: np.ndarray, result: np.ndarray) -> int:
        """
        Perceptual quality blend:
          50% sharpness improvement  (Laplacian variance ratio)
          30% contrast improvement   (luminance std-dev ratio)
          20% saturation improvement (mean HSV-S ratio)
        """
        def lap_var(img: np.ndarray) -> float:
            return max(
                cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var(),
                1.0
            )

        def lum_std(img: np.ndarray) -> float:
            return max(float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).std()), 1.0)

        def mean_sat(img: np.ndarray) -> float:
            return max(float(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1].mean()), 1.0)

        sharpness = lap_var(result) / lap_var(original)
        contrast  = lum_std(result)  / lum_std(original)
        vibrance  = mean_sat(result) / mean_sat(original)

        combined  = sharpness * 0.50 + contrast * 0.30 + vibrance * 0.20

        # Map combined ≈ 1.0 → ~65, higher improvements push toward 99
        return min(99, max(55, int(55 + (combined - 1.0) * 35)))
