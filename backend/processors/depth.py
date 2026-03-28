"""
PixelForge · processors/depth.py
Category: Depth & Spatial Effects

Tools
  bokeh             — rembg mask → blur background → composite (portrait mode)
  tilt_shift        — horizontal focus band; blur above and below
  perspective       — auto-straighten via Hough lines + homography
"""

import logging

import cv2
import numpy as np

import image_io
from config import BOKEH_BLUR_K, REMBG_MODEL, TILT_BLUR_K

log = logging.getLogger("pixelforge.depth")


class DepthProcessor:

    def __init__(self) -> None:
        self._rembg_session = None
        self._rembg_remove  = None
        self._load_rembg()

    def _load_rembg(self) -> None:
        try:
            from rembg import new_session, remove  # noqa
            self._rembg_session = new_session(REMBG_MODEL)
            self._rembg_remove  = remove
        except Exception as exc:
            log.warning("rembg not available for depth tools (%s)", exc)

    # ── Bokeh (Background Blur) ───────────────────────────────────────────────
    def bokeh(self, raw: bytes, blur_strength: int = 25) -> tuple[bytes, int]:
        """
        U2-Net foreground mask → blur background → composite.
        blur_strength: Gaussian sigma (1-50).
        """
        img = image_io.decode(raw)
        h, w = img.shape[:2]

        # Get alpha mask from rembg
        if self._rembg_session is not None:
            try:
                png_bytes = self._rembg_remove(raw, session=self._rembg_session)
                arr  = np.frombuffer(png_bytes, np.uint8)
                bgra = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
                alpha = bgra[:, :, 3].astype(np.float32) / 255.0
            except Exception as exc:
                log.warning("rembg bokeh failed (%s) — using centre mask", exc)
                alpha = self._centre_alpha(h, w)
        else:
            alpha = self._centre_alpha(h, w)

        # Blur background
        sigma  = max(3, int(blur_strength))
        k      = sigma * 4 + 1 if sigma * 4 + 1 % 2 == 1 else sigma * 4
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=sigma)

        # Composite: alpha * foreground + (1-alpha) * blurred background
        alpha3 = np.stack([alpha] * 3, axis=-1)
        result = (img.astype(np.float32) * alpha3 +
                  blurred.astype(np.float32) * (1.0 - alpha3))
        result = np.clip(result, 0, 255).astype(np.uint8)

        bg_blur = float((1.0 - alpha).mean() * blur_strength)
        score   = min(99, max(70, int(70 + bg_blur * 0.6)))
        return image_io.to_jpeg(result), score

    @staticmethod
    def _centre_alpha(h: int, w: int) -> np.ndarray:
        """Simple elliptical centre mask when rembg unavailable."""
        ys = np.linspace(-1, 1, h)
        xs = np.linspace(-1, 1, w)
        xv, yv = np.meshgrid(xs, ys)
        dist = np.sqrt((xv * 1.3) ** 2 + yv ** 2)
        return np.clip(1.0 - dist, 0, 1)

    # ── Tilt-Shift ────────────────────────────────────────────────────────────
    def tilt_shift(
        self,
        raw: bytes,
        focus_y: float = 0.5,
        focus_width: float = 0.25,
    ) -> tuple[bytes, int]:
        """
        focus_y      : vertical centre of sharp band (0-1, default middle)
        focus_width  : fraction of height that stays sharp (0.05-0.5)
        """
        img     = image_io.decode(raw)
        h, w    = img.shape[:2]
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=TILT_BLUR_K // 4)

        ys      = np.linspace(0, 1, h)
        centre  = np.clip(float(focus_y),    0.1, 0.9)
        half_w  = np.clip(float(focus_width), 0.05, 0.45) / 2.0

        # Smooth gradient mask: 1 in focus band, 0 far away
        dist    = np.abs(ys - centre) - half_w
        mask    = np.clip(1.0 - dist / half_w, 0, 1) ** 2
        mask    = mask[:, np.newaxis, np.newaxis]

        result  = (img.astype(np.float32) * mask +
                   blurred.astype(np.float32) * (1.0 - mask))
        result  = np.clip(result, 0, 255).astype(np.uint8)

        score   = min(99, max(72, int(76 + focus_width * 40)))
        return image_io.to_jpeg(result), score

    # ── Perspective Correction ────────────────────────────────────────────────
    def perspective(self, raw: bytes) -> tuple[bytes, int]:
        """
        Auto-detect dominant rectangle via Hough lines and correct perspective.
        Best for images of documents, whiteboards, or buildings.
        Falls back gracefully if no dominant rectangle is found.
        """
        img  = image_io.decode(raw)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Edge detection
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80,
                                minLineLength=w // 4, maxLineGap=20)

        if lines is None or len(lines) < 4:
            return image_io.to_jpeg(img), 70  # nothing to correct

        # Separate lines into roughly horizontal and vertical
        h_lines, v_lines = [], []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 20 or abs(angle) > 160:
                h_lines.append(line[0])
            elif 70 < abs(angle) < 110:
                v_lines.append(line[0])

        if len(h_lines) < 2 or len(v_lines) < 2:
            return image_io.to_jpeg(img), 70

        def line_to_eq(l):
            x1, y1, x2, y2 = l
            dx, dy = x2 - x1, y2 - y1
            if dx == 0:
                return (1, 0, -x1)
            m = dy / dx
            return (m, -1, y1 - m * x1)

        def intersect(l1, l2):
            a1, b1, c1 = l1
            a2, b2, c2 = l2
            det = a1 * b2 - a2 * b1
            if abs(det) < 1e-6:
                return None
            x = (c2 * b1 - c1 * b2) / det
            y = (a2 * c1 - a1 * c2) / det
            return (x, y)

        # Use extreme lines to find corners
        h_lines.sort(key=lambda l: (l[1] + l[3]) / 2)
        v_lines.sort(key=lambda l: (l[0] + l[2]) / 2)
        top, bottom = h_lines[0], h_lines[-1]
        left, right = v_lines[0], v_lines[-1]

        corners = [
            intersect(line_to_eq(top),    line_to_eq(left)),
            intersect(line_to_eq(top),    line_to_eq(right)),
            intersect(line_to_eq(bottom), line_to_eq(right)),
            intersect(line_to_eq(bottom), line_to_eq(left)),
        ]

        if any(c is None for c in corners):
            return image_io.to_jpeg(img), 70

        src = np.float32(corners)
        dst = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        M   = cv2.getPerspectiveTransform(src, dst)
        result = cv2.warpPerspective(img, M, (w, h),
                                     flags=cv2.INTER_LANCZOS4)
        return image_io.to_jpeg(result), 85
