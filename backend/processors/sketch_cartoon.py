"""
PixelForge · processors/sketch_cartoon.py

Sketch
  bilateral pre-smooth → clamped dodge-burn → shadow-layer blend →
  Canny edge overlay → gamma brightening → line sharpening.

  Key fixes vs previous version:
  • dodge result is clamped to [0, 1] BEFORE darkness weight — prevents the
    metallic / silver-overflow artefact on mid-tone face / hair areas.
  • SKETCH_DODGE_SIGMA reduced 22 → 15 so the blur doesn't bleed sky brightness
    over the face region (was collapsing face to uniform grey).
  • Shadow layer: instead of multiplying by a weight (which left a
    grey residue), we blend a dark shadow map ADDITIVELY so dark clothing
    goes genuinely black while the paper background stays white.
  • Gamma 0.60 → 0.80: less aggressive brightening, avoiding blown-out
    mid-tones while still making the background paper-white.

Cartoon
  bilateral colour flatten → median merge → K-means (k=10) quantisation
  → Canny outlines (lowered to 30/100 to capture facial features)
  → post-smoothing bilateral to remove quantisation grain.

  Key fixes vs previous version:
  • sigma 80 → 60: bilateral no longer over-smooths the face before K-means,
    so the face cluster is distinct from clothing.
  • k=10 (was 14) with 8 attempts: stable convergence every run; skin, sky,
    white fabric, dark navy, hair, shadow each reliably get their own cluster.
  • Canny 30/100: catches fine lines around eyes and glasses.
  • Post-quantisation bilateral: smooths jagged cluster boundaries without
    destroying the black outlines painted on top.
  • Saturation boost raised 1.25 → 1.35 since flatter regions now benefit
    from a slightly stronger colour pop.
"""

import cv2
import numpy as np

import image_io
from config import (
    CARTOON_BILATERAL_D,
    CARTOON_BILATERAL_PASSES,
    CARTOON_BILATERAL_SIGMA,
    CARTOON_CANNY_HIGH,
    CARTOON_CANNY_LOW,
    CARTOON_EDGE_DILATE,
    CARTOON_KMEANS_ATTEMPTS,
    CARTOON_KMEANS_K,
    CARTOON_MEDIAN_K,
    SKETCH_BILATERAL_D,
    SKETCH_BILATERAL_SIGMA,
    SKETCH_DARKNESS_W,
    SKETCH_DODGE_SIGMA,
    SKETCH_EDGE_BLEND,
    SKETCH_GAMMA,
)


class SketchCartoon:

    def process(self, raw: bytes, mode: str) -> tuple[bytes, int]:
        img = image_io.decode(raw)
        if mode == "sketch":
            result, score = self._sketch(img)
        else:
            result, score = self._cartoon(img)
        return image_io.to_jpeg(result), score

    # ── Sketch ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _sketch(img: np.ndarray) -> tuple[np.ndarray, int]:
        # 1 — Bilateral pre-smooth: flatten texture, keep hard edges
        smooth = cv2.bilateralFilter(
            img,
            d=SKETCH_BILATERAL_D,
            sigmaColor=SKETCH_BILATERAL_SIGMA,
            sigmaSpace=SKETCH_BILATERAL_SIGMA,
        )
        gray      = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
        orig_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2 — Dodge-burn: extract line structure
        #     Clamp to [0, 1] BEFORE any weighting to prevent metallic overflow
        inv_blurred = cv2.GaussianBlur(255 - gray, (0, 0), sigmaX=SKETCH_DODGE_SIGMA)
        denom       = (255 - inv_blurred).astype(np.float32)
        denom       = np.where(denom < 1.0, 1.0, denom)          # avoid divide-by-zero
        dodge       = np.clip(gray.astype(np.float32) / denom, 0.0, 1.0)

        # 3 — Shadow layer blend: dark areas in original pull the sketch toward black.
        #     We compute a shadow map from original luminance and subtract it so that
        #     navy clothing → genuinely dark ink, not metallic grey.
        #     shadow = DARKNESS_W × (1 − orig_norm)  [dark pixels → large subtraction]
        orig_norm  = orig_gray.astype(np.float32) / 255.0
        shadow     = SKETCH_DARKNESS_W * (1.0 - orig_norm)       # 0=light, DARKNESS_W=dark
        dodge      = np.clip(dodge - shadow, 0.0, 1.0)

        # 4 — Canny structural edges: reinforce clothing / skin boundaries
        canny = cv2.Canny(
            cv2.GaussianBlur(orig_gray, (5, 5), 0), 40, 120
        ).astype(np.float32) / 255.0
        # Where Canny fires, push toward black (0)
        dodge = dodge * (1.0 - SKETCH_EDGE_BLEND * canny)

        # 5 — Gamma LUT: lift paper regions to white
        lut    = np.array(
            [int((i / 255.0) ** SKETCH_GAMMA * 255) for i in range(256)],
            dtype=np.uint8,
        )
        sketch = cv2.LUT(np.clip(dodge * 255, 0, 255).astype(np.uint8), lut)

        # 6 — Gentle line sharpening
        kernel = np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]], np.float32)
        sketch = np.clip(cv2.filter2D(sketch, -1, kernel), 0, 255).astype(np.uint8)

        # Score: edge-line alignment
        orig_edges   = cv2.Canny(cv2.GaussianBlur(orig_gray, (5, 5), 0), 50, 150)
        sketch_lines = (sketch < 200).astype(np.uint8)
        overlap      = np.logical_and(orig_edges > 0, sketch_lines > 0).sum()
        edge_total   = max((orig_edges > 0).sum(), 1)
        score        = min(99, max(60, int(overlap / edge_total * 300)))

        return sketch, score

    # ── Cartoon ────────────────────────────────────────────────────────────────

    @staticmethod
    def _cartoon(img: np.ndarray) -> tuple[np.ndarray, int]:
        h, w = img.shape[:2]

        # 1 — Bilateral: flatten colours while preserving facial structure
        #     sigma=60 (was 80) keeps the face-clothing boundary intact
        smooth = img.copy()
        for _ in range(CARTOON_BILATERAL_PASSES):
            smooth = cv2.bilateralFilter(
                smooth,
                d=CARTOON_BILATERAL_D,
                sigmaColor=CARTOON_BILATERAL_SIGMA,
                sigmaSpace=CARTOON_BILATERAL_SIGMA,
            )

        # 2 — Median blur: remove remaining speckle without destroying face edges
        smooth = cv2.medianBlur(smooth, CARTOON_MEDIAN_K)

        # 3 — K-means colour quantisation (k=10 with 8 attempts gives stable
        #     convergence; distinct clusters for skin / sky / clothing / fabric /
        #     hair / shadow)
        pixels   = smooth.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels,
            CARTOON_KMEANS_K,
            None,
            criteria,
            CARTOON_KMEANS_ATTEMPTS,
            cv2.KMEANS_PP_CENTERS,
        )
        quantized = centers[labels.flatten()].astype(np.uint8).reshape(h, w, 3)

        # 4 — Post-quantisation bilateral: smooth jagged cluster boundaries
        #     Use gentle params (sigma=40) so grain disappears but outlines survive
        quantized = cv2.bilateralFilter(quantized, d=7, sigmaColor=40, sigmaSpace=40)

        # 5 — Canny edges on ORIGINAL image (not smoothed) for facial details
        #     Lower thresholds (30/100) catch eyes, nose bridge, lip lines
        orig_gray = cv2.GaussianBlur(
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0
        )
        edges = cv2.Canny(orig_gray, CARTOON_CANNY_LOW, CARTOON_CANNY_HIGH)

        # Dilate slightly so outlines are visible at normal viewing size
        if CARTOON_EDGE_DILATE > 0:
            edges = cv2.dilate(
                edges,
                np.ones((CARTOON_EDGE_DILATE + 1,) * 2, np.uint8),
                iterations=1,
            )

        # 6 — Overlay black outlines on quantised canvas
        result = quantized.copy()
        result[edges > 0] = 0

        # 7 — Saturation boost so flat colours feel vivid
        #     Raised to 1.35 (was 1.25) since k=10 large uniform regions
        #     benefit from stronger pop
        hsv              = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1]     = np.clip(hsv[:, :, 1] * 1.35, 0, 255)
        result           = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Score: colour variance reduction (more reduction = cleaner cartoon)
        step       = 4
        orig_var   = float(img[::step, ::step].reshape(-1, 3).astype(np.float32).var(axis=0).mean())
        res_var    = float(result[::step, ::step].reshape(-1, 3).astype(np.float32).var(axis=0).mean())
        reduction  = 1.0 - res_var / max(orig_var, 1.0)
        score      = min(99, max(60, int(reduction * 130)))

        return result, score
