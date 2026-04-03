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
DENOISE_H            = 5        # was 3 — more meaningful noise removal
DENOISE_H_COLOR      = 5        # was 3
DENOISE_TEMPLATE_WIN = 7
DENOISE_SEARCH_WIN   = 21
CLAHE_CLIP_LIMIT     = 2.5      # was 1.8 — stronger local contrast
CLAHE_TILE_GRID      = (8, 8)
CLAHE_CLIP_LOW       = 1.2      # used by adaptive CLAHE for already-contrasty images
CLAHE_CLIP_HIGH      = 3.5      # used by adaptive CLAHE for flat/washed-out images
UNSHARP_SHARP_W      = 1.5      # was 1.3 — crisper edges
UNSHARP_BLUR_W       = -0.5     # was -0.3
UNSHARP_SIGMA        = 2.0      # was 1.5 — wider sharpening kernel
UNSHARP_FLAT_THRESH  = 8
ENHANCE_VIBRANCE_STRENGTH = 0.35  # selective vibrance: replaces flat SAT_BOOST

# ── Sketch ────────────────────────────────────────────────────────────────────
SKETCH_BILATERAL_D      = 9
SKETCH_BILATERAL_SIGMA  = 75
SKETCH_DODGE_SIGMA      = 15      # was 22 — tighter blur → crisper line separation
SKETCH_GAMMA            = 0.80    # was 0.60 — paper-white without lifting darks
SKETCH_DARKNESS_W       = 0.55    # was 0.45 — stronger shadow preservation
SKETCH_EDGE_BLEND       = 0.35

# ── Cartoon ───────────────────────────────────────────────────────────────────
CARTOON_BILATERAL_PASSES = 3
CARTOON_BILATERAL_D      = 9
CARTOON_BILATERAL_SIGMA  = 60      # was 80 — preserve face boundary pre-kmeans
CARTOON_MEDIAN_K         = 7
CARTOON_KMEANS_K         = 10      # was 14 — fewer but stable clusters
CARTOON_KMEANS_ATTEMPTS  = 8       # was 5 — better convergence
CARTOON_CANNY_LOW        = 30      # was 50 — catch finer facial outlines
CARTOON_CANNY_HIGH       = 100     # was 130
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
