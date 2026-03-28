"""
PixelForge · processors/sketch_cartoon.py

Sketch
  bilateral pre-smooth → dodge-burn divide → darkness preservation →
  Canny edge blend → gamma brightening → line sharpening.

  Key fix: after dodge-burn, dark areas (navy clothing) were becoming
  medium-grey because gamma < 1 lifts ALL tones uniformly.  We now
  multiply the dodge-burn result by a "darkness weight" derived from
  the original luminance so areas that were genuinely dark stay dark,
  while the light/paper background brightens correctly.

Cartoon
  bilateral colour flatten → median merge → K-means (k=14) quantisation
  → Canny outlines (lower thresholds: 50/130 capture facial features).

  Key fix: sigma was 120 (too aggressive → merged face+hair+glasses into
  a single blob).  Reduced to 80 with k=14 so skin, hair, and clothing
  each get their own colour cluster.
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
        gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
        orig_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2 — Dodge-burn: extract line structure
        inv_blurred = cv2.GaussianBlur(255 - gray, (0, 0), sigmaX=SKETCH_DODGE_SIGMA)
        dodge = cv2.divide(gray, 255 - inv_blurred, scale=256.0).astype(np.float32)

        # 3 — Darkness preservation: areas originally dark → darker lines on paper
        #     Without this, uniform dark clothing turns grey after gamma lift.
        #     Formula: weight = 1 - DARKNESS_W * (orig_luminance / 255)
        #     → dark pixels (low luminance) → weight near 1.0 (lines preserved)
        #     → light pixels (high luminance) → weight near (1 - DARKNESS_W) (lines faded)
        orig_norm    = orig_gray.astype(np.float32) / 255.0
        dark_weight  = 1.0 - SKETCH_DARKNESS_W * orig_norm
        dodge        = dodge * dark_weight

        # 4 — Canny structural edges: reinforce boundaries of dark objects
        #     Blended in to give clean outlines at clothing/skin boundaries
        canny = cv2.Canny(
            cv2.GaussianBlur(orig_gray, (5, 5), 0), 40, 120
        ).astype(np.float32) / 255.0
        # Canny edges → dark on paper (invert: edge=0, background=1 on paper)
        # Blend: where Canny fires, push toward black (0)
        dodge = dodge * (1.0 - SKETCH_EDGE_BLEND * canny)

        # 5 — Gamma LUT: lift mid-tones to paper-white (less aggressive now)
        lut    = np.array(
            [int((i / 255.0) ** SKETCH_GAMMA * 255) for i in range(256)],
            dtype=np.uint8,
        )
        sketch = cv2.LUT(np.clip(dodge, 0, 255).astype(np.uint8), lut)

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

        # 1 — Moderate bilateral: flatten colours, preserve facial structure
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

        # 3 — K-means colour quantisation (k=14 gives distinct clusters for
        #     skin / hair / clothing / background / highlights)
        pixels   = smooth.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
        _, labels, centers = cv2.kmeans(
            pixels,
            CARTOON_KMEANS_K,
            None,
            criteria,
            CARTOON_KMEANS_ATTEMPTS,
            cv2.KMEANS_PP_CENTERS,
        )
        quantized = centers[labels.flatten()].astype(np.uint8).reshape(h, w, 3)

        # 4 — Canny edges on ORIGINAL image (not smoothed) for facial details
        #     Lower thresholds (50/130) catch eyes, nose bridge, lip lines
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

        # 5 — Overlay black outlines on quantised canvas
        result = quantized.copy()
        result[edges > 0] = 0

        # 6 — Saturation boost so flat colours feel vivid
        hsv              = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1]     = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
        result           = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Score: colour variance reduction (more reduction = cleaner cartoon)
        step       = 4
        orig_var   = float(img[::step, ::step].reshape(-1, 3).astype(np.float32).var(axis=0).mean())
        res_var    = float(result[::step, ::step].reshape(-1, 3).astype(np.float32).var(axis=0).mean())
        reduction  = 1.0 - res_var / max(orig_var, 1.0)
        score      = min(99, max(60, int(reduction * 130)))

        return result, score
