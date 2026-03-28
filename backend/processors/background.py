"""
PixelForge · processors/background.py

Primary  → rembg (U2-Net ONNX) — DL salient-object segmentation.
Fallback → GrabCut + morphological cleanup + alpha feathering.

Score = foreground coverage + alpha edge cleanliness, normalised to 0-99.
"""

import logging

import cv2
import numpy as np

import image_io
from config import (
    GRABCUT_BG_BORDER,
    GRABCUT_EDGE_BLUR,
    GRABCUT_FG_INSET,
    GRABCUT_ITERATIONS,
    GRABCUT_MORPH_K,
    REMBG_MODEL,
)

log = logging.getLogger("pixelforge.background")


class BackgroundRemover:

    def __init__(self) -> None:
        self._session = None
        self._remove  = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from rembg import new_session, remove  # noqa: PLC0415
            self._session = new_session(REMBG_MODEL)
            self._remove  = remove
            log.info("U2-Net loaded — DL background removal active.")
        except Exception as exc:
            log.warning("rembg unavailable (%s). Will use GrabCut fallback.", exc)

    @property
    def backend(self) -> str:
        return "u2net" if self._session else "grabcut"

    def process(self, raw: bytes) -> tuple[bytes, int]:
        """Return (png_bytes, quality_score)."""
        if self._session is not None:
            try:
                result_bytes = self._remove(raw, session=self._session)
                score = self._score_from_png(result_bytes)
                return result_bytes, score
            except Exception as exc:
                log.warning("U2-Net inference failed (%s). Falling back to GrabCut.", exc)

        img  = image_io.decode(raw)
        bgra = self._grabcut(img)
        score = self._score_bgra(bgra)
        return image_io.to_png(bgra), score

    # ── scoring ────────────────────────────────────────────────────────────────

    @staticmethod
    def _score_from_png(png_bytes: bytes) -> int:
        arr  = np.frombuffer(png_bytes, np.uint8)
        bgra = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if bgra is None or bgra.shape[2] < 4:
            return 70
        return BackgroundRemover._score_bgra(bgra)

    @staticmethod
    def _score_bgra(bgra: np.ndarray) -> int:
        alpha = bgra[:, :, 3].astype(np.float32) / 255.0
        # Coverage: ratio of foreground pixels
        fg_ratio = float((alpha > 0.5).mean())
        # Edge cleanness: penalise pixels stuck in the 0.1-0.9 (half-transparent) range
        messy = float(((alpha > 0.1) & (alpha < 0.9)).mean())
        cleanness = max(0.0, 1.0 - messy * 3.0)
        # Reward sensible FG coverage (0.05-0.70 is realistic for a portrait)
        cov_score = 1.0 - abs(fg_ratio - 0.35) * 1.5
        cov_score = max(0.0, min(1.0, cov_score))
        combined = cov_score * 0.5 + cleanness * 0.5
        return min(99, max(55, int(combined * 99)))

    # ── GrabCut fallback ───────────────────────────────────────────────────────

    @staticmethod
    def _grabcut(img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]

        mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
        y1 = int(h * GRABCUT_FG_INSET);  y2 = int(h * (1 - GRABCUT_FG_INSET))
        x1 = int(w * GRABCUT_FG_INSET);  x2 = int(w * (1 - GRABCUT_FG_INSET))
        mask[y1:y2, x1:x2] = cv2.GC_PR_FGD

        brd = max(3, int(min(h, w) * GRABCUT_BG_BORDER))
        mask[:brd, :]  = mask[-brd:, :] = cv2.GC_BGD
        mask[:, :brd]  = mask[:, -brd:] = cv2.GC_BGD

        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        cv2.grabCut(
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
            mask, None, bgd, fgd,
            GRABCUT_ITERATIONS, cv2.GC_INIT_WITH_MASK,
        )

        fg = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)

        k  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (GRABCUT_MORPH_K,) * 2)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k, iterations=3)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  k, iterations=1)

        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
        if n > 1:
            best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            fg   = np.where(labels == best, 255, 0).astype(np.uint8)

        fg = cv2.GaussianBlur(fg, (GRABCUT_EDGE_BLUR,) * 2, sigmaX=1.5)

        bgra        = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = fg
        return bgra
