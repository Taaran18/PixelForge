"""
PixelForge · config.py
Global constants and tuning parameters for all processors.
"""

# ── Background Removal ────────────────────────────────────────────────────────
REMBG_MODEL        = "u2net"
GRABCUT_ITERATIONS = 10
GRABCUT_FG_INSET   = 0.12
GRABCUT_BG_BORDER  = 0.04
GRABCUT_MORPH_K    = 7
GRABCUT_EDGE_BLUR  = 5

# ── Enhancement ───────────────────────────────────────────────────────────────
DENOISE_H            = 3
DENOISE_H_COLOR      = 3
DENOISE_TEMPLATE_WIN = 7
DENOISE_SEARCH_WIN   = 21
CLAHE_CLIP_LIMIT     = 1.8
CLAHE_TILE_GRID      = (8, 8)
UNSHARP_SHARP_W      = 1.3
UNSHARP_BLUR_W       = -0.3
UNSHARP_SIGMA        = 1.5
UNSHARP_FLAT_THRESH  = 8
ENHANCE_SAT_BOOST    = 1.12

# ── Sketch ────────────────────────────────────────────────────────────────────
SKETCH_BILATERAL_D      = 9
SKETCH_BILATERAL_SIGMA  = 75
SKETCH_DODGE_SIGMA      = 22
SKETCH_GAMMA            = 0.60
SKETCH_DARKNESS_W       = 0.45
SKETCH_EDGE_BLEND       = 0.35

# ── Cartoon ───────────────────────────────────────────────────────────────────
CARTOON_BILATERAL_PASSES = 3
CARTOON_BILATERAL_D      = 9
CARTOON_BILATERAL_SIGMA  = 80
CARTOON_MEDIAN_K         = 7
CARTOON_KMEANS_K         = 14
CARTOON_KMEANS_ATTEMPTS  = 5
CARTOON_CANNY_LOW        = 50
CARTOON_CANNY_HIGH       = 130
CARTOON_EDGE_DILATE      = 1

# ── Filters: Oil Painting ─────────────────────────────────────────────────────
OIL_RADIUS          = 4            # neighbourhood radius for mode filter
OIL_DYNAMIC_RATIO   = 1            # dynamic ratio for xphoto.oilPainting

# ── Filters: Watercolour ──────────────────────────────────────────────────────
WATERCOLOUR_SIGMA_S  = 60
WATERCOLOUR_SIGMA_R  = 0.6
WATERCOLOUR_SHADE    = 0.025
WATERCOLOUR_TEXTURE  = 0.12        # strength of paper-grain overlay

# ── Filters: HDR ─────────────────────────────────────────────────────────────
HDR_GAMMA           = 1.0
HDR_SATURATION      = 1.2

# ── Filters: Vintage ─────────────────────────────────────────────────────────
VINTAGE_FADE        = 0.25         # how much to lift shadows
VINTAGE_GRAIN_STD   = 18           # luminance grain strength

# ── Filters: Vignette ────────────────────────────────────────────────────────
VIGNETTE_SIGMA      = 0.5          # falloff shape (relative to image radius)

# ── Filters: Pixelate ────────────────────────────────────────────────────────
PIXELATE_BLOCK      = 16           # default block size in pixels

# ── Colour: Splash ────────────────────────────────────────────────────────────
SPLASH_HUE_RANGE    = 25           # ± hue degrees around target hue

# ── Colour: Super-Resolution ──────────────────────────────────────────────────
SR_MODEL_DIR        = "models"     # folder containing .pb model files
SR_DEFAULT_SCALE    = 2            # upscale factor (2 or 4)
SR_MODEL_NAME       = "EDSR"       # EDSR, ESPCN, FSRCNN, or LAPSRN

# ── Depth: Bokeh ─────────────────────────────────────────────────────────────
BOKEH_BLUR_K        = 51           # Gaussian kernel size for background blur

# ── Depth: Tilt-Shift ────────────────────────────────────────────────────────
TILT_BLUR_K         = 41

# ── Detection: Face ───────────────────────────────────────────────────────────
FACE_CASCADE        = "haarcascade_frontalface_default.xml"
FACE_SCALE          = 1.1
FACE_NEIGHBORS      = 5
FACE_MIN_SIZE       = (40, 40)

# ── Output ────────────────────────────────────────────────────────────────────
JPEG_QUALITY        = 92
