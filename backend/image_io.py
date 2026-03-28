"""
PixelForge · image_io.py
Stateless helpers for decoding uploaded images and encoding results.
"""

from http import HTTPStatus

import cv2
import numpy as np
from fastapi import HTTPException

from config import JPEG_QUALITY


def decode(raw: bytes) -> np.ndarray:
    """Decode raw upload bytes into a BGR ndarray."""
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Cannot decode image.")
    return img


def to_png(img: np.ndarray) -> bytes:
    """Encode a BGRA (or BGR) ndarray to PNG bytes."""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, "PNG encoding failed.")
    return buf.tobytes()


def to_jpeg(img: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    """Encode a BGR ndarray to JPEG bytes."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, "JPEG encoding failed.")
    return buf.tobytes()
