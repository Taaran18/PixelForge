# PixelForge

A web-based image processing tool — upload a photo, pick a tool, download the result.
No account required. No data leaves your machine.

---

## Features

PixelForge organises its tools into seven categories.

### Core Tools

| Tool | Description |
|------|-------------|
| Background Remover | U2-Net deep-learning segmentation → transparent PNG |
| Image Enhancer | NL-Means denoise → CLAHE → unsharp mask → saturation boost |
| Sketch / Cartoon | Bilateral + dodge-burn pencil sketch; K-means + Canny cartoon |

### Filters & Stylisation

| Tool | Description |
|------|-------------|
| Oil Painting | Mode-filter neighbourhood via `xphoto.oilPainting` |
| Watercolour | Colour pencilSketch + paper-grain texture overlay |
| HDR Tone Mapping | Drago / Reinhard / Mantiuk tone-mapping operators |
| Vintage / Film | Shadow-lift fade, warm S-curve, luminance grain |
| Vignette | Radial Gaussian darkening toward frame edges |
| Cinematic Grade | Teal-Orange, Noir, or Warm colour LUT |
| Pixelate | Mosaic via nearest-neighbour downscale |
| Glitch | Per-channel RGB shift + scan-line noise |

### Colour Operations

| Tool | Description |
|------|-------------|
| Colour Splash | Keep one hue range in colour; desaturate the rest |
| Colour Replace | Remap a source hue range to any target hue |
| Sepia / Duotone | Classic sepia, cool blue, or purple duotone |
| Colour Palette | K-means dominant-colour swatches rendered below the image |
| B&W Channel Mixer | Weighted RGB → greyscale with per-channel sliders |

### Restoration & Repair

| Tool | Description |
|------|-------------|
| Super Resolution | 2× / 4× upscale via DNN (EDSR) or Lanczos4 fallback |
| Deblur | Wiener frequency-domain deconvolution |
| JPEG Artefact Removal | NL-Means tuned for block-noise and compression artefacts |
| Auto Inpaint | Detect scratches/dust → fill with `cv2.INPAINT_TELEA` |

### Depth & Spatial Effects

| Tool | Description |
|------|-------------|
| Bokeh / Background Blur | U2-Net mask → blur background → composite |
| Tilt-Shift | Horizontal focus band with smooth gradient blur |
| Perspective Correction | Hough lines → homography warp to straighten images |

### Detection & Smart Features

| Tool | Description |
|------|-------------|
| Face Blur / Pixelate | Haar cascade detection → blur or pixelate each face |
| Portrait Mode | Subject on blurred, white, black, or gradient background |

### Analysis & Diagnostics

| Tool | Description |
|------|-------------|
| Histogram Viewer | R/G/B/Luminance channel histograms plotted below image |
| Noise Level Map | Local noise visualised as JET heat-map overlay |
| Sharpness Map | Laplacian-variance TURBO heat-map |
| Exposure Heatmap | Blown (>250) and crushed (<5) pixel region highlights |

Every tool returns a **transform score (0–99)** measuring how effectively the image was processed.

---

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, App Router |
| Backend | FastAPI, Python 3.11 |
| Computer Vision | OpenCV contrib (`opencv-contrib-python-headless`) |
| DL Segmentation | U2-Net via `rembg` + ONNX Runtime (CPU) |
| Deployment | Vercel (frontend) · Render (backend) |

---

## Project Structure

```
PixelForge/
├── frontend/                   # Next.js app
│   └── src/app/
│       ├── layout.tsx
│       ├── page.tsx            # Single interactive page
│       └── globals.css
└── backend/                    # FastAPI app
    ├── main.py                 # Routes only
    ├── config.py               # All tuning constants
    ├── image_io.py             # Decode / encode helpers
    └── processors/
        ├── background.py       # Core: Background Removal
        ├── enhancer.py         # Core: Enhancement
        ├── sketch_cartoon.py   # Core: Sketch / Cartoon
        ├── filters.py          # Filters & Stylisation (8 tools)
        ├── colour.py           # Colour Operations (5 tools)
        ├── restoration.py      # Restoration & Repair (4 tools)
        ├── depth.py            # Depth & Spatial (3 tools)
        ├── detection.py        # Detection & Smart (2 tools)
        └── analysis.py         # Analysis & Diagnostics (4 tools)
```

---

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend

# If you have any existing opencv build, remove it first
pip uninstall -y opencv-python opencv-python-headless

pip install -r requirements.txt

# Start the server (U2-Net model downloads ~170 MB on first run)
uvicorn main:app --reload
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: `http://localhost:3000`

### Environment Variables

Create `frontend/.env.local` to point at a deployed backend:

```env
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

---

## Docker (backend)

```bash
cd backend
docker build -t pixelforge-backend .
docker run -p 8000:8000 pixelforge-backend
```

The Dockerfile pre-downloads the U2-Net model at build time so the first request is instant.

---

## API Reference

All `POST` endpoints accept `multipart/form-data` with a `file` field.
Every response includes an `X-Transform-Score` header (integer 0–99).

### Core

| Method | Path | Form params |
|--------|------|-------------|
| `GET` | `/health` | — |
| `POST` | `/remove-background` | `file` |
| `POST` | `/enhance` | `file` |
| `POST` | `/sketch-cartoon` | `file`, `mode` (sketch\|cartoon) |

### Filters

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/filters/oil-painting` | `file` |
| `POST` | `/filters/watercolour` | `file` |
| `POST` | `/filters/hdr` | `file`, `method` (drago\|reinhard\|mantiuk) |
| `POST` | `/filters/vintage` | `file` |
| `POST` | `/filters/vignette` | `file`, `strength` (0.1–1.0) |
| `POST` | `/filters/colour-grade` | `file`, `style` (teal-orange\|noir\|warm) |
| `POST` | `/filters/pixelate` | `file`, `block_size` (4–64) |
| `POST` | `/filters/glitch` | `file` |

### Colour

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/colour/splash` | `file`, `hue` (0–359), `hue_range` |
| `POST` | `/colour/replace` | `file`, `from_hue`, `to_hue`, `hue_range` |
| `POST` | `/colour/sepia` | `file`, `style` (sepia\|cool\|purple) |
| `POST` | `/colour/palette` | `file`, `n_colors` (3–12) |
| `POST` | `/colour/bw-mixer` | `file`, `r_weight`, `g_weight`, `b_weight` |

### Restoration

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/restoration/super-resolution` | `file`, `scale` (2\|4) |
| `POST` | `/restoration/deblur` | `file`, `snr` (5–80) |
| `POST` | `/restoration/dejpeg` | `file` |
| `POST` | `/restoration/inpaint` | `file`, `radius` (3–20) |

### Depth

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/depth/bokeh` | `file`, `blur_strength` (5–50) |
| `POST` | `/depth/tilt-shift` | `file`, `focus_y` (0–1), `focus_width` (0.05–0.5) |
| `POST` | `/depth/perspective` | `file` |

### Detection

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/detection/face-blur` | `file`, `mode` (blur\|pixelate) |
| `POST` | `/detection/portrait` | `file`, `bg_style` (blur\|white\|black\|gradient) |

### Analysis

| Method | Path | Form params |
|--------|------|-------------|
| `POST` | `/analysis/histogram` | `file` |
| `POST` | `/analysis/noise-map` | `file` |
| `POST` | `/analysis/sharpness-map` | `file` |
| `POST` | `/analysis/exposure-map` | `file` |
