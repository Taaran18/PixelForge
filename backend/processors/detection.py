"""
PixelForge · processors/detection.py
Category: Detection & Smart Features

Tools
  face_blur     — detect faces (DNN or Haar) → blur / pixelate each face box
  portrait      — rembg foreground + solid/gradient background colour fill
"""

import logging
import os

import cv2
import numpy as np

import image_io
from config import (
    FACE_CASCADE,
    FACE_MIN_SIZE,
    FACE_NEIGHBORS,
    FACE_SCALE,
    REMBG_MODEL,
)

log = logging.getLogger("pixelforge.detection")

# Haar cascade is shipped with opencv — works without any model download
_CASCADE_PATH = cv2.data.haarcascades + FACE_CASCADE


class DetectionProcessor:

    def __init__(self) -> None:
        self._cascade        = None
        self._rembg_session  = None
        self._rembg_remove   = None
        self._load()

    def _load(self) -> None:
        # Face cascade
        if os.path.isfile(_CASCADE_PATH):
            self._cascade = cv2.CascadeClassifier(_CASCADE_PATH)
            log.info("Haar face cascade loaded.")
        else:
            log.warning("Haar cascade not found at %s", _CASCADE_PATH)

        # rembg for portrait mode
        try:
            from rembg import new_session, remove  # noqa
            self._rembg_session = new_session(REMBG_MODEL)
            self._rembg_remove  = remove
        except Exception as exc:
            log.warning("rembg not available for portrait (%s)", exc)

    # ── Face Blur / Pixelate ──────────────────────────────────────────────────
    def face_blur(self, raw: bytes, mode: str = "blur") -> tuple[bytes, int]:
        img  = image_io.decode(raw)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = []
        if self._cascade is not None:
            faces = self._cascade.detectMultiScale(
                gray,
                scaleFactor=FACE_SCALE,
                minNeighbors=FACE_NEIGHBORS,
                minSize=FACE_MIN_SIZE,
            )

        if len(faces) == 0:
            return image_io.to_jpeg(img), 60  # no faces found

        result = img.copy()
        for (x, y, fw, fh) in faces:
            # Add padding around detected box
            pad  = int(max(fw, fh) * 0.1)
            x1   = max(0, x - pad);       y1 = max(0, y - pad)
            x2   = min(img.shape[1], x + fw + pad)
            y2   = min(img.shape[0], y + fh + pad)
            face_roi = result[y1:y2, x1:x2]

            if mode == "pixelate":
                small = cv2.resize(face_roi, (max(1, fw // 10), max(1, fh // 10)),
                                   interpolation=cv2.INTER_LINEAR)
                result[y1:y2, x1:x2] = cv2.resize(
                    small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST
                )
            else:  # blur
                k = (max(fw, fh) | 1) * 2 + 1   # ensure odd, scale with face size
                result[y1:y2, x1:x2] = cv2.GaussianBlur(face_roi, (k | 1, k | 1), 0)

        score = min(99, max(70, int(70 + len(faces) * 8)))
        return image_io.to_jpeg(result), score

    # ── Object Remover (user-drawn mask → inpaint) ───────────────────────────
    def remove_object(self, raw: bytes, mask_raw: bytes, radius: int = 12) -> tuple[bytes, int]:
        img      = image_io.decode(raw)
        h, w     = img.shape[:2]

        mask_arr = np.frombuffer(mask_raw, np.uint8)
        mask_dec = cv2.imdecode(mask_arr, cv2.IMREAD_UNCHANGED)
        if mask_dec is None:
            return image_io.to_jpeg(img), 95

        # If RGBA use alpha channel as mask, else convert to gray
        if mask_dec.ndim == 3 and mask_dec.shape[2] == 4:
            mask_gray = mask_dec[:, :, 3]
        elif mask_dec.ndim == 3:
            mask_gray = cv2.cvtColor(mask_dec, cv2.COLOR_BGR2GRAY)
        else:
            mask_gray = mask_dec

        if mask_gray.shape[:2] != (h, w):
            mask_gray = cv2.resize(mask_gray, (w, h), interpolation=cv2.INTER_NEAREST)

        _, mask_bin = cv2.threshold(mask_gray, 50, 255, cv2.THRESH_BINARY)

        if mask_bin.max() == 0:
            return image_io.to_jpeg(img), 95

        # Dilate slightly to cover brush edges
        k        = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_bin = cv2.dilate(mask_bin, k, iterations=2)

        result   = cv2.inpaint(img, mask_bin, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
        coverage = float((mask_bin > 0).mean())
        score    = min(99, max(65, int(95 - coverage * 150)))
        return image_io.to_jpeg(result), score

    # ── Remove People (HOG detector → inpaint) ───────────────────────────────
    def remove_people(self, raw: bytes) -> tuple[bytes, int]:
        img  = image_io.decode(raw)
        h, w = img.shape[:2]

        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        boxes, _ = hog.detectMultiScale(
            img,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )

        if len(boxes) == 0:
            return image_io.to_jpeg(img), 60

        mask = np.zeros((h, w), np.uint8)
        for (x, y, bw, bh) in boxes:
            pad = int(max(bw, bh) * 0.12)
            x1 = max(0, x - pad);  y1 = max(0, y - pad)
            x2 = min(w, x + bw + pad); y2 = min(h, y + bh + pad)
            mask[y1:y2, x1:x2] = 255

        k    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.dilate(mask, k, iterations=2)

        result = cv2.inpaint(img, mask, inpaintRadius=18, flags=cv2.INPAINT_TELEA)
        score  = min(99, max(65, int(65 + len(boxes) * 8)))
        return image_io.to_jpeg(result), score

    # ── Portrait Mode ─────────────────────────────────────────────────────────
    def portrait(self, raw: bytes, bg_style: str = "blur") -> tuple[bytes, int]:
        """
        bg_style options:
          "blur"      — blurred original as background
          "white"     — solid white background
          "black"     — solid black background
          "gradient"  — vertical purple→cyan gradient
        """
        img  = image_io.decode(raw)
        h, w = img.shape[:2]

        # Get foreground mask
        if self._rembg_session is not None:
            try:
                png_bytes = self._rembg_remove(raw, session=self._rembg_session)
                arr  = np.frombuffer(png_bytes, np.uint8)
                bgra = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
                alpha = bgra[:, :, 3].astype(np.float32) / 255.0
            except Exception as exc:
                log.warning("rembg portrait failed (%s)", exc)
                alpha = np.ones((h, w), np.float32)
        else:
            alpha = np.ones((h, w), np.float32)

        # Build background
        if bg_style == "blur":
            bg = cv2.GaussianBlur(img, (0, 0), sigmaX=25)
        elif bg_style == "white":
            bg = np.full_like(img, 255)
        elif bg_style == "black":
            bg = np.zeros_like(img)
        else:  # gradient purple→cyan
            grad = np.zeros((h, w, 3), np.uint8)
            for row in range(h):
                t = row / h
                # purple (124,58,237) → cyan (6,182,212) in BGR
                b = int((1 - t) * 237 + t * 212)
                g = int((1 - t) * 58  + t * 182)
                r = int((1 - t) * 124 + t * 6)
                grad[row] = (b, g, r)
            bg = grad

        alpha3 = np.stack([alpha] * 3, axis=-1)
        result = (img.astype(np.float32) * alpha3 +
                  bg.astype(np.float32) * (1.0 - alpha3))
        result = np.clip(result, 0, 255).astype(np.uint8)

        coverage = float(alpha.mean())
        score    = min(99, max(65, int(65 + coverage * 30)))
        return image_io.to_jpeg(result), score
