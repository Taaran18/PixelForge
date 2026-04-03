"""
PixelForge · main.py
App factory, CORS, lifespan, and all route handlers.

Routes are grouped by category tag:
  core          — Background Removal, Enhancement, Sketch/Cartoon
  filters       — Oil Painting, Watercolour, HDR, Vintage, Vignette,
                  Colour Grade, Pixelate, Glitch
  colour        — Splash, Replace, Sepia, Palette, B&W Mixer
  restoration   — Super Resolution, Deblur, De-JPEG, Inpaint
  depth         — Bokeh, Tilt-Shift, Perspective
  detection     — Face Blur, Portrait Mode
  analysis      — Histogram, Noise Map, Sharpness Map, Exposure Map
  meta          — Health check
"""

import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from processors import (
    AnalysisProcessor,
    BackgroundRemover,
    ColourProcessor,
    DepthProcessor,
    DetectionProcessor,
    Enhancer,
    FiltersProcessor,
    RestorationProcessor,
    SketchCartoon,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger("pixelforge")

# ── Processor singletons ──────────────────────────────────────────────────────
bg_remover    = BackgroundRemover()
enhancer      = Enhancer()
sketch_cart   = SketchCartoon()
filters       = FiltersProcessor()
colour        = ColourProcessor()
restoration   = RestorationProcessor()
depth         = DepthProcessor()
detection     = DetectionProcessor()
analysis      = AnalysisProcessor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("PixelForge ready  |  BG: %s", bg_remover.backend)
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="PixelForge API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Transform-Score"],
)


def _resp(content: bytes, mime: str, score: int) -> Response:
    return Response(content=content, media_type=mime,
                    headers={"X-Transform-Score": str(score)})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# META
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "bg_backend": bg_remover.backend}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CORE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/remove-background", tags=["core"])
async def remove_background(file: UploadFile = File(...)):
    raw = await file.read()
    png, score = bg_remover.process(raw)
    return _resp(png, "image/png", score)


@app.post("/enhance", tags=["core"])
async def enhance(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = enhancer.process(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/sketch-cartoon", tags=["core"])
async def sketch_cartoon(
    file: UploadFile = File(...),
    mode: str = Form("sketch"),
):
    if mode not in ("sketch", "cartoon"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "mode: 'sketch' | 'cartoon'")
    raw = await file.read()
    jpg, score = sketch_cart.process(raw, mode)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FILTERS & STYLISATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/filters/oil-painting", tags=["filters"])
async def oil_painting(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = filters.oil_painting(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/watercolour", tags=["filters"])
async def watercolour(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = filters.watercolour(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/hdr", tags=["filters"])
async def hdr(
    file: UploadFile = File(...),
    method: str = Form("drago"),
):
    if method not in ("drago", "reinhard", "mantiuk"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "method: 'drago'|'reinhard'|'mantiuk'")
    raw = await file.read()
    jpg, score = filters.hdr(raw, method)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/vintage", tags=["filters"])
async def vintage(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = filters.vintage(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/vignette", tags=["filters"])
async def vignette(
    file: UploadFile = File(...),
    strength: float = Form(0.7),
):
    raw = await file.read()
    jpg, score = filters.vignette(raw, strength)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/colour-grade", tags=["filters"])
async def colour_grade(
    file: UploadFile = File(...),
    style: str = Form("teal-orange"),
):
    if style not in ("teal-orange", "noir", "warm"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "style: 'teal-orange'|'noir'|'warm'")
    raw = await file.read()
    jpg, score = filters.colour_grade(raw, style)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/pixelate", tags=["filters"])
async def pixelate(
    file: UploadFile = File(...),
    block_size: int = Form(16),
):
    raw = await file.read()
    jpg, score = filters.pixelate(raw, block_size)
    return _resp(jpg, "image/jpeg", score)


@app.post("/filters/glitch", tags=["filters"])
async def glitch(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = filters.glitch(raw)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLOUR OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/colour/splash", tags=["colour"])
async def colour_splash(
    file: UploadFile = File(...),
    hue: int = Form(120),
    hue_range: int = Form(25),
):
    raw = await file.read()
    jpg, score = colour.splash(raw, hue, hue_range)
    return _resp(jpg, "image/jpeg", score)


@app.post("/colour/replace", tags=["colour"])
async def colour_replace(
    file: UploadFile = File(...),
    from_hue: int = Form(120),
    to_hue: int = Form(0),
    hue_range: int = Form(25),
):
    raw = await file.read()
    jpg, score = colour.replace(raw, from_hue, to_hue, hue_range)
    return _resp(jpg, "image/jpeg", score)


@app.post("/colour/sepia", tags=["colour"])
async def sepia(
    file: UploadFile = File(...),
    style: str = Form("sepia"),
):
    if style not in ("sepia", "cool", "purple"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "style: 'sepia'|'cool'|'purple'")
    raw = await file.read()
    jpg, score = colour.sepia(raw, style)
    return _resp(jpg, "image/jpeg", score)


@app.post("/colour/palette", tags=["colour"])
async def palette(
    file: UploadFile = File(...),
    n_colors: int = Form(6),
):
    raw = await file.read()
    jpg, score = colour.palette(raw, n_colors)
    return _resp(jpg, "image/jpeg", score)


@app.post("/colour/bw-mixer", tags=["colour"])
async def bw_mixer(
    file: UploadFile = File(...),
    r_weight: float = Form(0.299),
    g_weight: float = Form(0.587),
    b_weight: float = Form(0.114),
):
    raw = await file.read()
    jpg, score = colour.bw_mixer(raw, r_weight, g_weight, b_weight)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESTORATION & REPAIR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/restoration/super-resolution", tags=["restoration"])
async def super_resolution(
    file: UploadFile = File(...),
    scale: int = Form(2),
):
    raw = await file.read()
    jpg, score = restoration.super_resolution(raw, scale)
    return _resp(jpg, "image/jpeg", score)


@app.post("/restoration/deblur", tags=["restoration"])
async def deblur(
    file: UploadFile = File(...),
    snr: float = Form(25.0),
):
    raw = await file.read()
    jpg, score = restoration.deblur(raw, snr)
    return _resp(jpg, "image/jpeg", score)


@app.post("/restoration/dejpeg", tags=["restoration"])
async def dejpeg(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = restoration.dejpeg(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/restoration/inpaint", tags=["restoration"])
async def inpaint(
    file: UploadFile = File(...),
    radius: int = Form(8),
):
    raw = await file.read()
    jpg, score = restoration.inpaint(raw, radius)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEPTH & SPATIAL EFFECTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/depth/bokeh", tags=["depth"])
async def bokeh(
    file: UploadFile = File(...),
    blur_strength: int = Form(25),
):
    raw = await file.read()
    jpg, score = depth.bokeh(raw, blur_strength)
    return _resp(jpg, "image/jpeg", score)


@app.post("/depth/tilt-shift", tags=["depth"])
async def tilt_shift(
    file: UploadFile = File(...),
    focus_y: float = Form(0.5),
    focus_width: float = Form(0.25),
):
    raw = await file.read()
    jpg, score = depth.tilt_shift(raw, focus_y, focus_width)
    return _resp(jpg, "image/jpeg", score)


@app.post("/depth/perspective", tags=["depth"])
async def perspective(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = depth.perspective(raw)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DETECTION & SMART FEATURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/detection/face-blur", tags=["detection"])
async def face_blur(
    file: UploadFile = File(...),
    mode: str = Form("blur"),
):
    if mode not in ("blur", "pixelate"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "mode: 'blur'|'pixelate'")
    raw = await file.read()
    jpg, score = detection.face_blur(raw, mode)
    return _resp(jpg, "image/jpeg", score)


@app.post("/detection/portrait", tags=["detection"])
async def portrait(
    file: UploadFile = File(...),
    bg_style: str = Form("blur"),
):
    if bg_style not in ("blur", "white", "black", "gradient"):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "bg_style: 'blur'|'white'|'black'|'gradient'")
    raw = await file.read()
    jpg, score = detection.portrait(raw, bg_style)
    return _resp(jpg, "image/jpeg", score)


@app.post("/detection/remove-object", tags=["detection"])
async def remove_object(
    file: UploadFile = File(...),
    mask: UploadFile = File(...),
    radius: int = Form(12),
):
    raw      = await file.read()
    mask_raw = await mask.read()
    jpg, score = detection.remove_object(raw, mask_raw, radius)
    return _resp(jpg, "image/jpeg", score)


@app.post("/detection/remove-people", tags=["detection"])
async def remove_people(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = detection.remove_people(raw)
    return _resp(jpg, "image/jpeg", score)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANALYSIS & DIAGNOSTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/analysis/histogram", tags=["analysis"])
async def histogram(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = analysis.histogram(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/analysis/noise-map", tags=["analysis"])
async def noise_map(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = analysis.noise_map(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/analysis/sharpness-map", tags=["analysis"])
async def sharpness_map(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = analysis.sharpness_map(raw)
    return _resp(jpg, "image/jpeg", score)


@app.post("/analysis/exposure-map", tags=["analysis"])
async def exposure_map(file: UploadFile = File(...)):
    raw = await file.read()
    jpg, score = analysis.exposure_map(raw)
    return _resp(jpg, "image/jpeg", score)
