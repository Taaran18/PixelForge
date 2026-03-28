"""
PixelForge · processors/colour.py
Category: Colour Operations

Tools
  splash          — keep one hue range in colour, desaturate the rest
  replace         — remap a source hue range to a target hue
  sepia           — warm brown matrix transform (or duotone variant)
  palette         — K-means dominant-colour swatches rendered on image
  bw_mixer        — weighted RGB→greyscale with channel sliders
"""

import cv2
import numpy as np

import image_io
from config import SPLASH_HUE_RANGE


class ColourProcessor:

    # ── Colour Splash ─────────────────────────────────────────────────────────
    def splash(self, raw: bytes, hue: int = 120, hue_range: int = SPLASH_HUE_RANGE) -> tuple[bytes, int]:
        """Keep pixels near `hue` in colour; desaturate everything else."""
        img = image_io.decode(raw)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_ch = hsv[:, :, 0].astype(np.int16)   # OpenCV hue: 0-179

        # Target hue in OpenCV scale (0-179)
        target = int(hue / 2)
        hr     = int(hue_range / 2)

        # Build circular distance mask
        diff = np.abs(h_ch - target)
        diff = np.minimum(diff, 180 - diff)

        keep_mask = (diff <= hr).astype(np.uint8)

        # Greyscale version as BGR
        gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        mask3    = np.stack([keep_mask] * 3, axis=-1)
        result   = np.where(mask3, img, gray_bgr)

        kept_frac = float(keep_mask.mean())
        score = min(99, max(65, int(70 + kept_frac * 80)))
        return image_io.to_jpeg(result), score

    # ── Colour Replacement ────────────────────────────────────────────────────
    def replace(
        self,
        raw: bytes,
        from_hue: int = 120,
        to_hue: int = 0,
        hue_range: int = 25,
    ) -> tuple[bytes, int]:
        """Shift pixels near `from_hue` to `to_hue`."""
        img  = image_io.decode(raw)
        hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int16)
        h_ch = hsv[:, :, 0]

        src  = int(from_hue / 2)
        tgt  = int(to_hue   / 2)
        hr   = int(hue_range / 2)

        diff = np.abs(h_ch - src)
        diff = np.minimum(diff, 180 - diff)
        mask = diff <= hr

        shift        = tgt - src
        hsv[:, :, 0] = np.where(mask, (h_ch + shift) % 180, h_ch)

        result = cv2.cvtColor(hsv.clip(0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
        changed_frac = float(mask.mean())
        score = min(99, max(65, int(72 + changed_frac * 80)))
        return image_io.to_jpeg(result), score

    # ── Sepia / Duotone ───────────────────────────────────────────────────────
    def sepia(self, raw: bytes, style: str = "sepia") -> tuple[bytes, int]:
        img   = image_io.decode(raw).astype(np.float32) / 255.0
        b, g, r = cv2.split(img)

        if style == "sepia":
            r_out = np.clip(r * 0.393 + g * 0.769 + b * 0.189, 0, 1)
            g_out = np.clip(r * 0.349 + g * 0.686 + b * 0.168, 0, 1)
            b_out = np.clip(r * 0.272 + g * 0.534 + b * 0.131, 0, 1)
        elif style == "cool":
            # Blue-teal duotone
            gray  = 0.114 * b + 0.587 * g + 0.299 * r
            r_out = np.clip(gray * 0.6,  0, 1)
            g_out = np.clip(gray * 0.85, 0, 1)
            b_out = np.clip(gray * 1.2,  0, 1)
        else:  # "purple" duotone
            gray  = 0.114 * b + 0.587 * g + 0.299 * r
            r_out = np.clip(gray * 0.9,  0, 1)
            g_out = np.clip(gray * 0.6,  0, 1)
            b_out = np.clip(gray * 1.1,  0, 1)

        result = np.clip(cv2.merge([b_out, g_out, r_out]) * 255, 0, 255).astype(np.uint8)
        return image_io.to_jpeg(result), 88

    # ── Colour Palette Extractor ──────────────────────────────────────────────
    def palette(self, raw: bytes, n_colors: int = 6) -> tuple[bytes, int]:
        """Return the original image with a row of dominant-colour swatches below it."""
        img   = image_io.decode(raw)
        h, w  = img.shape[:2]

        pixels   = img.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, n_colors, None, criteria, 5, cv2.KMEANS_PP_CENTERS
        )

        # Sort colours by frequency
        counts  = np.bincount(labels.flatten(), minlength=n_colors)
        order   = np.argsort(-counts)
        centers = centers[order].astype(np.uint8)

        # Build swatch row
        swatch_h   = max(60, h // 8)
        swatch_row = np.zeros((swatch_h, w, 3), dtype=np.uint8)
        sw         = w // n_colors
        for i, color in enumerate(centers):
            x1 = i * sw
            x2 = x1 + sw if i < n_colors - 1 else w
            swatch_row[:, x1:x2] = color

        # Add thin separator
        sep    = np.ones((4, w, 3), dtype=np.uint8) * 240
        result = np.vstack([img, sep, swatch_row])

        return image_io.to_jpeg(result), 92

    # ── Channel Mixer B&W ─────────────────────────────────────────────────────
    def bw_mixer(
        self,
        raw: bytes,
        r_weight: float = 0.299,
        g_weight: float = 0.587,
        b_weight: float = 0.114,
    ) -> tuple[bytes, int]:
        """Custom weighted greyscale conversion (weights normalised to sum=1)."""
        img = image_io.decode(raw).astype(np.float32)
        b_ch, g_ch, r_ch = cv2.split(img)

        total    = abs(r_weight) + abs(g_weight) + abs(b_weight)
        total    = max(total, 1e-6)
        rw       = r_weight / total
        gw       = g_weight / total
        bw       = b_weight / total

        gray   = np.clip(rw * r_ch + gw * g_ch + bw * b_ch, 0, 255).astype(np.uint8)

        # Micro-contrast boost for B&W
        clahe  = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray   = clahe.apply(gray)

        result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        score   = min(99, max(65, int(65 + np.log1p(lap_var) * 4)))
        return image_io.to_jpeg(result), score
