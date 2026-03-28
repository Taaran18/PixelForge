"""
PixelForge · processors/analysis.py
Category: Analysis & Diagnostics

Tools
  histogram       — overlay R/G/B/L channel histograms below the image
  noise_map       — local noise level rendered as a heat-map overlay
  sharpness_map   — Laplacian-variance heat-map (blue=soft, red=sharp)
  exposure_map    — highlight blown (>250) and crushed (<5) pixel regions
"""

import cv2
import numpy as np

import image_io


class AnalysisProcessor:

    # ── Histogram Viewer ──────────────────────────────────────────────────────
    def histogram(self, raw: bytes) -> tuple[bytes, int]:
        img    = image_io.decode(raw)
        h, w   = img.shape[:2]

        hist_h = max(180, h // 3)
        hist_w = w
        canvas = np.ones((hist_h, hist_w, 3), dtype=np.uint8) * 28  # dark bg

        # Grid lines
        for i in range(1, 4):
            gx = hist_w * i // 4
            cv2.line(canvas, (gx, 0), (gx, hist_h), (50, 50, 50), 1)

        colors  = [(255, 60, 60), (60, 220, 60), (60, 60, 255)]  # B G R (display)
        labels  = ["B", "G", "R"]

        for c_idx, (color, label) in enumerate(zip(colors, labels)):
            hist = cv2.calcHist([img], [c_idx], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, hist_h - 20, cv2.NORM_MINMAX)
            pts = hist.astype(np.int32).flatten()

            for x in range(1, 256):
                x1 = (x - 1) * hist_w // 256
                x2 = x       * hist_w // 256
                y1 = hist_h - pts[x - 1]
                y2 = hist_h - pts[x]
                cv2.line(canvas, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

            # Channel label
            cv2.putText(canvas, label, (8 + c_idx * 30, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        # Luminance in white
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist_l = cv2.calcHist([gray], [0], None, [256], [0, 256])
        cv2.normalize(hist_l, hist_l, 0, hist_h - 20, cv2.NORM_MINMAX)
        pts_l = hist_l.astype(np.int32).flatten()
        for x in range(1, 256):
            x1 = (x - 1) * hist_w // 256
            x2 = x       * hist_w // 256
            y1 = hist_h - pts_l[x - 1]
            y2 = hist_h - pts_l[x]
            cv2.line(canvas, (x1, y1), (x2, y2), (200, 200, 200), 1, cv2.LINE_AA)

        sep    = np.ones((3, w, 3), dtype=np.uint8) * 60
        result = np.vstack([img, sep, canvas])

        # Score = dynamic range spread (wider histogram → better exposed)
        nonzero = np.where(hist_l.flatten() > 0)[0]
        spread  = int(nonzero[-1] - nonzero[0]) if len(nonzero) > 1 else 0
        score   = min(99, max(50, int(50 + spread / 255 * 49)))
        return image_io.to_jpeg(result), score

    # ── Noise Level Map ───────────────────────────────────────────────────────
    def noise_map(self, raw: bytes) -> tuple[bytes, int]:
        img    = image_io.decode(raw)
        h, w   = img.shape[:2]
        gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Local noise: difference between pixel and its Gaussian-smoothed version
        smooth   = cv2.GaussianBlur(gray, (7, 7), 0)
        noise    = np.abs(gray - smooth)

        # Normalise to 0-255 for colour mapping
        noise_n  = cv2.normalize(noise, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heat     = cv2.applyColorMap(noise_n, cv2.COLORMAP_JET)

        # Overlay at 50% opacity
        overlay  = cv2.addWeighted(img, 0.5, heat, 0.5, 0)

        # Legend bar
        legend   = self._colourbar(w, 30, cv2.COLORMAP_JET,
                                   left_label="Low noise", right_label="High noise")
        sep      = np.ones((3, w, 3), dtype=np.uint8) * 60
        result   = np.vstack([overlay, sep, legend])

        mean_noise = float(noise.mean())
        score      = min(99, max(50, int(99 - mean_noise * 2)))
        return image_io.to_jpeg(result), score

    # ── Sharpness Map ─────────────────────────────────────────────────────────
    def sharpness_map(self, raw: bytes) -> tuple[bytes, int]:
        img    = image_io.decode(raw)
        h, w   = img.shape[:2]
        gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Local Laplacian magnitude as sharpness proxy
        lap     = cv2.Laplacian(gray, cv2.CV_32F)
        lap_abs = np.abs(lap)

        # Smooth map for cleaner visualisation
        lap_s   = cv2.GaussianBlur(lap_abs, (15, 15), 0)
        norm    = cv2.normalize(lap_s, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heat    = cv2.applyColorMap(norm, cv2.COLORMAP_TURBO)

        overlay = cv2.addWeighted(img, 0.45, heat, 0.55, 0)

        legend  = self._colourbar(w, 30, cv2.COLORMAP_TURBO,
                                  left_label="Soft", right_label="Sharp")
        sep     = np.ones((3, w, 3), dtype=np.uint8) * 60
        result  = np.vstack([overlay, sep, legend])

        score   = min(99, max(50, int(50 + np.log1p(lap_abs.mean()) * 10)))
        return image_io.to_jpeg(result), score

    # ── Exposure Heatmap ──────────────────────────────────────────────────────
    def exposure_map(self, raw: bytes) -> tuple[bytes, int]:
        img       = image_io.decode(raw)
        h, w      = img.shape[:2]
        gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        result    = img.copy()

        # Blown highlights (>250) → vivid red overlay
        blown     = gray > 250
        result[blown] = np.clip(
            result[blown].astype(np.int16) + np.array([0, 0, 80], np.int16), 0, 255
        ).astype(np.uint8)

        # Crushed shadows (<5) → vivid blue overlay
        crushed   = gray < 5
        result[crushed] = np.clip(
            result[crushed].astype(np.int16) + np.array([80, 0, 0], np.int16), 0, 255
        ).astype(np.uint8)

        # Add legend text
        blown_pct   = float(blown.mean()) * 100
        crushed_pct = float(crushed.mean()) * 100
        cv2.putText(result, f"Blown: {blown_pct:.1f}%",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 255), 2, cv2.LINE_AA)
        cv2.putText(result, f"Crushed: {crushed_pct:.1f}%",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 80, 80), 2, cv2.LINE_AA)

        # Score = well-exposed fraction
        well_exposed = 1.0 - blown_pct / 100 - crushed_pct / 100
        score        = min(99, max(50, int(well_exposed * 99)))
        return image_io.to_jpeg(result), score

    # ── Helper: colour bar legend ──────────────────────────────────────────────
    @staticmethod
    def _colourbar(
        width: int,
        height: int,
        cmap: int,
        left_label: str = "",
        right_label: str = "",
    ) -> np.ndarray:
        bar_1d = np.arange(256, dtype=np.uint8).reshape(1, 256)
        bar    = cv2.resize(bar_1d, (width, height), interpolation=cv2.INTER_LINEAR)
        bar    = cv2.applyColorMap(bar, cmap)
        if left_label:
            cv2.putText(bar, left_label, (4, height - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        if right_label:
            tw = cv2.getTextSize(right_label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0][0]
            cv2.putText(bar, right_label, (width - tw - 4, height - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        return bar
