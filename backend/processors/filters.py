"""
PixelForge · processors/filters.py
Category: Filters & Stylisation

Tools
  oil_painting      — xphoto.oilPainting (mode-filter per neighbourhood)
  watercolour       — pencilSketch colour layer + paper-grain texture
  hdr               — Drago / Reinhard / Mantiuk tone-mapping
  vintage           — shadow-lift fade + S-curve + luminance grain
  vignette          — radial Gaussian falloff darkening
  colour_grade      — Teal-Orange / Noir / Warm cinematic LUTs
  pixelate          — mosaic via downscale→INTER_NEAREST upscale
  glitch            — per-channel horizontal shift + scan-line noise
"""

import cv2
import numpy as np

import image_io
from config import (
    BOKEH_BLUR_K,
    HDR_GAMMA,
    HDR_SATURATION,
    OIL_DYNAMIC_RATIO,
    OIL_RADIUS,
    PIXELATE_BLOCK,
    TILT_BLUR_K,
    VINTAGE_FADE,
    VINTAGE_GRAIN_STD,
    VIGNETTE_SIGMA,
    WATERCOLOUR_SHADE,
    WATERCOLOUR_SIGMA_R,
    WATERCOLOUR_SIGMA_S,
    WATERCOLOUR_TEXTURE,
)


class FiltersProcessor:

    # ── Oil Painting ───────────────────────────────────────────────────────────
    def oil_painting(self, raw: bytes) -> tuple[bytes, int]:
        img = image_io.decode(raw)
        try:
            result = cv2.xphoto.oilPainting(img, OIL_RADIUS, OIL_DYNAMIC_RATIO)
        except AttributeError:
            # Fallback: repeated bilateral gives a comparable painterly look
            result = img.copy()
            for _ in range(6):
                result = cv2.bilateralFilter(result, 9, 75, 75)
        score = self._score_stylisation(img, result)
        return image_io.to_jpeg(result), score

    # ── Watercolour ───────────────────────────────────────────────────────────
    def watercolour(self, raw: bytes) -> tuple[bytes, int]:
        img = image_io.decode(raw)
        try:
            _, colour = cv2.pencilSketch(
                img,
                sigma_s=WATERCOLOUR_SIGMA_S,
                sigma_r=WATERCOLOUR_SIGMA_R,
                shade_factor=WATERCOLOUR_SHADE,
            )
            result = colour
        except AttributeError:
            result = cv2.edgePreservingFilter(img, flags=1, sigma_s=60, sigma_r=0.4)

        # Paper-grain texture overlay
        h, w = result.shape[:2]
        grain = np.random.normal(255, 15, (h, w)).clip(0, 255).astype(np.uint8)
        grain_bgr = cv2.cvtColor(grain, cv2.COLOR_GRAY2BGR)
        result = cv2.addWeighted(result, 1.0 - WATERCOLOUR_TEXTURE,
                                 grain_bgr, WATERCOLOUR_TEXTURE, 0)

        # Desaturate edges slightly for a washed look
        lab     = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        a = (a.astype(np.float32) * 0.85).clip(0, 255).astype(np.uint8)
        b = (b.astype(np.float32) * 0.85).clip(0, 255).astype(np.uint8)
        result  = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        score = self._score_stylisation(img, result)
        return image_io.to_jpeg(result), score

    # ── HDR Tone Mapping ──────────────────────────────────────────────────────
    def hdr(self, raw: bytes, method: str = "drago") -> tuple[bytes, int]:
        img    = image_io.decode(raw)
        hdr_f  = img.astype(np.float32) / 255.0

        tonemap_map = {
            "drago":    cv2.createTonemapDrago(HDR_GAMMA, HDR_SATURATION),
            "reinhard": cv2.createTonemapReinhard(HDR_GAMMA, 0, HDR_SATURATION, 0),
            "mantiuk":  cv2.createTonemapMantiuk(HDR_GAMMA, HDR_SATURATION, 0.85),
        }
        tonemap = tonemap_map.get(method, tonemap_map["drago"])
        ldr     = tonemap.process(hdr_f)
        result  = np.clip(ldr * 255, 0, 255).astype(np.uint8)

        score = self._score_contrast(img, result)
        return image_io.to_jpeg(result), score

    # ── Vintage / Film ────────────────────────────────────────────────────────
    def vintage(self, raw: bytes) -> tuple[bytes, int]:
        img = image_io.decode(raw).astype(np.float32) / 255.0

        # 1 — Lift shadows (fade highlights toward white)
        img = img * (1.0 - VINTAGE_FADE) + VINTAGE_FADE * 0.5

        # 2 — S-curve per channel (warm highlights, cool shadows)
        def scurve(x: np.ndarray, lift: float = 0.0, gain: float = 1.05) -> np.ndarray:
            return np.clip(gain * x + lift, 0, 1)

        b, g, r = cv2.split(img)
        r = scurve(r,  lift=0.02,  gain=1.06)   # warm reds
        g = scurve(g,  lift=0.00,  gain=1.00)
        b = scurve(b,  lift=-0.02, gain=0.93)   # cool blues
        img = cv2.merge([b, g, r])

        # 3 — Luminance grain
        h, w = img.shape[:2]
        grain = np.random.normal(0, VINTAGE_GRAIN_STD / 255.0, (h, w, 1))
        img   = np.clip(img + grain, 0, 1)

        result = (img * 255).astype(np.uint8)
        score  = self._score_contrast(
            image_io.decode(raw), result
        )
        return image_io.to_jpeg(result), score

    # ── Vignette ──────────────────────────────────────────────────────────────
    def vignette(self, raw: bytes, strength: float = 0.7) -> tuple[bytes, int]:
        img     = image_io.decode(raw)
        h, w    = img.shape[:2]

        # Radial distance mask (0 at centre, 1 at corners)
        ys = np.linspace(-1, 1, h)
        xs = np.linspace(-1, 1, w)
        xv, yv = np.meshgrid(xs, ys)
        dist = np.sqrt(xv**2 + yv**2)

        # Gaussian-like falloff
        sigma  = VIGNETTE_SIGMA
        mask   = np.exp(-0.5 * (dist / sigma) ** 2)
        mask   = 1.0 - strength * (1.0 - mask)
        mask   = mask[:, :, np.newaxis]

        result = np.clip(img.astype(np.float32) * mask, 0, 255).astype(np.uint8)
        score  = min(99, max(70, int(75 + strength * 20)))
        return image_io.to_jpeg(result), score

    # ── Cinematic Colour Grade ────────────────────────────────────────────────
    def colour_grade(self, raw: bytes, style: str = "teal-orange") -> tuple[bytes, int]:
        img = image_io.decode(raw).astype(np.float32) / 255.0
        b, g, r = cv2.split(img)

        if style == "teal-orange":
            # Shadows → teal, highlights → orange
            r = np.clip(r * 1.15 + 0.03, 0, 1)
            g = np.clip(g * 0.97,         0, 1)
            b = np.clip(b * 0.80 - 0.03, 0, 1)
        elif style == "noir":
            # High contrast black & white with slight blue cast
            gray = 0.114 * b + 0.587 * g + 0.299 * r
            gray = np.clip(gray * 1.3 - 0.1, 0, 1)   # boost contrast
            r = gray * 0.95
            g = gray * 0.97
            b = gray * 1.05
        elif style == "warm":
            r = np.clip(r * 1.12 + 0.05, 0, 1)
            g = np.clip(g * 1.03,         0, 1)
            b = np.clip(b * 0.88 - 0.05, 0, 1)

        result = np.clip(cv2.merge([b, g, r]) * 255, 0, 255).astype(np.uint8)
        score  = self._score_contrast(image_io.decode(raw), result)
        return image_io.to_jpeg(result), score

    # ── Pixelate ──────────────────────────────────────────────────────────────
    def pixelate(self, raw: bytes, block_size: int = PIXELATE_BLOCK) -> tuple[bytes, int]:
        img    = image_io.decode(raw)
        h, w   = img.shape[:2]
        bs     = max(4, min(block_size, 64))
        small  = cv2.resize(img, (w // bs, h // bs), interpolation=cv2.INTER_LINEAR)
        result = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        score  = min(99, max(70, int(80 + (64 - bs) / 60 * 15)))
        return image_io.to_jpeg(result), score

    # ── Glitch / Chromatic Aberration ─────────────────────────────────────────
    def glitch(self, raw: bytes) -> tuple[bytes, int]:
        img         = image_io.decode(raw)
        h, w        = img.shape[:2]
        b, g, r     = cv2.split(img)

        rng = np.random.default_rng(42)

        def shift_channel(ch: np.ndarray, dx: int, dy: int = 0) -> np.ndarray:
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            return cv2.warpAffine(ch, M, (w, h))

        r = shift_channel(r,  dx=rng.integers(4, 10))
        b = shift_channel(b,  dx=-rng.integers(4, 10))

        # Scan-line noise: random horizontal bands brightened
        for _ in range(rng.integers(4, 12)):
            y  = rng.integers(0, h)
            bh = rng.integers(2, 6)
            noise = rng.integers(0, 40, (bh, w), dtype=np.int16)
            for ch in (r, g, b):
                band = ch[y:y + bh].astype(np.int16) + noise
                ch[y:y + bh] = np.clip(band, 0, 255).astype(np.uint8)

        result = cv2.merge([b, g, r])
        return image_io.to_jpeg(result), 82

    # ── Shared scoring helpers ─────────────────────────────────────────────────
    @staticmethod
    def _score_stylisation(original: np.ndarray, result: np.ndarray) -> int:
        """How much the style changed relative to the original."""
        diff = cv2.absdiff(original, result).astype(np.float32).mean()
        return min(99, max(65, int(60 + diff * 0.9)))

    @staticmethod
    def _score_contrast(original: np.ndarray, result: np.ndarray) -> int:
        orig_std = float(cv2.cvtColor(original, cv2.COLOR_BGR2GRAY).std())
        res_std  = float(cv2.cvtColor(result,   cv2.COLOR_BGR2GRAY).std())
        ratio    = res_std / max(orig_std, 1.0)
        return min(99, max(60, int(55 + ratio * 30)))
