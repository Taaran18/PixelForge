"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Scissors, Sparkles, Pencil, Upload, Download, Loader2,
  AlertCircle, X, ImageIcon, Zap, Sun, Moon,
  Paintbrush, Droplets, Gauge, Grid2x2,
  Eye, Palette, Eraser, ScanLine, Focus, ScanSearch,
  UserX, User, BarChart3, Activity, Crosshair, Lightbulb,
  ChevronDown, ChevronRight, Film, Wand2,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────
type ParamType = "select" | "slider" | "slider-float";

interface Param {
  key: string;
  label: string;
  type: ParamType;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
  default: string | number;
}

interface Tool {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  endpoint: string;
  resultIsPng?: boolean;
  params?: Param[];
}

interface Category {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;        // tailwind text colour class for accent
  tools: Tool[];
}

// ── Tool Catalogue ─────────────────────────────────────────────────────────────
const CATEGORIES: Category[] = [
  {
    id: "core",
    label: "Core Tools",
    icon: <Sparkles className="w-4 h-4" />,
    color: "text-brand-purple",
    tools: [
      {
        id: "remove-background",
        label: "Background Remover",
        description: "Remove background with deep-learning segmentation.",
        icon: <Scissors className="w-5 h-5" />,
        endpoint: "/remove-background",
        resultIsPng: true,
      },
      {
        id: "enhance",
        label: "Image Enhancer",
        description: "Denoise, sharpen, and boost colour in one pass.",
        icon: <Sparkles className="w-5 h-5" />,
        endpoint: "/enhance",
      },
      {
        id: "sketch-cartoon",
        label: "Sketch / Cartoon",
        description: "Convert to pencil sketch or flat cartoon style.",
        icon: <Pencil className="w-5 h-5" />,
        endpoint: "/sketch-cartoon",
        params: [
          {
            key: "mode", label: "Mode", type: "select",
            options: [{ label: "Sketch", value: "sketch" }, { label: "Cartoon", value: "cartoon" }],
            default: "sketch",
          },
        ],
      },
    ],
  },
  {
    id: "filters",
    label: "Filters & Stylisation",
    icon: <Paintbrush className="w-4 h-4" />,
    color: "text-orange-400",
    tools: [
      {
        id: "filters/oil-painting",
        label: "Oil Painting",
        description: "Mode-filter neighbourhood gives thick painterly strokes.",
        icon: <Paintbrush className="w-5 h-5" />,
        endpoint: "/filters/oil-painting",
      },
      {
        id: "filters/watercolour",
        label: "Watercolour",
        description: "Soft washed edges with paper-grain texture.",
        icon: <Droplets className="w-5 h-5" />,
        endpoint: "/filters/watercolour",
      },
      {
        id: "filters/hdr",
        label: "HDR Tone Mapping",
        description: "Dramatic lighting via Drago / Reinhard / Mantiuk.",
        icon: <Wand2 className="w-5 h-5" />,
        endpoint: "/filters/hdr",
        params: [
          {
            key: "method", label: "Algorithm", type: "select",
            options: [
              { label: "Drago",    value: "drago" },
              { label: "Reinhard", value: "reinhard" },
              { label: "Mantiuk", value: "mantiuk" },
            ],
            default: "drago",
          },
        ],
      },
      {
        id: "filters/vintage",
        label: "Vintage / Film",
        description: "Faded shadows, warm S-curve, and luminance grain.",
        icon: <Film className="w-5 h-5" />,
        endpoint: "/filters/vintage",
      },
      {
        id: "filters/vignette",
        label: "Vignette",
        description: "Radial Gaussian darkening toward the edges.",
        icon: <Eye className="w-5 h-5" />,
        endpoint: "/filters/vignette",
        params: [
          {
            key: "strength", label: "Strength", type: "slider-float",
            min: 0.1, max: 1.0, step: 0.05, default: 0.7,
          },
        ],
      },
      {
        id: "filters/colour-grade",
        label: "Cinematic Grade",
        description: "Teal-Orange, Noir, or Warm LUT colour grading.",
        icon: <Palette className="w-5 h-5" />,
        endpoint: "/filters/colour-grade",
        params: [
          {
            key: "style", label: "Style", type: "select",
            options: [
              { label: "Teal-Orange", value: "teal-orange" },
              { label: "Noir",        value: "noir" },
              { label: "Warm",        value: "warm" },
            ],
            default: "teal-orange",
          },
        ],
      },
      {
        id: "filters/pixelate",
        label: "Pixelate",
        description: "Mosaic effect via nearest-neighbour downscale.",
        icon: <Grid2x2 className="w-5 h-5" />,
        endpoint: "/filters/pixelate",
        params: [
          {
            key: "block_size", label: "Block Size", type: "slider",
            min: 4, max: 64, step: 4, default: 16,
          },
        ],
      },
      {
        id: "filters/glitch",
        label: "Glitch / Chromatic",
        description: "RGB channel shifts and scan-line noise.",
        icon: <Zap className="w-5 h-5" />,
        endpoint: "/filters/glitch",
      },
    ],
  },
  {
    id: "colour",
    label: "Colour Operations",
    icon: <Palette className="w-4 h-4" />,
    color: "text-pink-400",
    tools: [
      {
        id: "colour/splash",
        label: "Colour Splash",
        description: "Keep one hue in colour; desaturate everything else.",
        icon: <Droplets className="w-5 h-5" />,
        endpoint: "/colour/splash",
        params: [
          {
            key: "hue", label: "Hue (0-360°)", type: "slider",
            min: 0, max: 359, step: 1, default: 120,
          },
          {
            key: "hue_range", label: "Range ±°", type: "slider",
            min: 5, max: 60, step: 5, default: 25,
          },
        ],
      },
      {
        id: "colour/replace",
        label: "Colour Replace",
        description: "Remap a source hue range to any target hue.",
        icon: <Eraser className="w-5 h-5" />,
        endpoint: "/colour/replace",
        params: [
          {
            key: "from_hue", label: "Source Hue", type: "slider",
            min: 0, max: 359, step: 1, default: 120,
          },
          {
            key: "to_hue", label: "Target Hue", type: "slider",
            min: 0, max: 359, step: 1, default: 0,
          },
          {
            key: "hue_range", label: "Range ±°", type: "slider",
            min: 5, max: 60, step: 5, default: 25,
          },
        ],
      },
      {
        id: "colour/sepia",
        label: "Sepia / Duotone",
        description: "Classic sepia or cool/purple duotone colour wash.",
        icon: <Film className="w-5 h-5" />,
        endpoint: "/colour/sepia",
        params: [
          {
            key: "style", label: "Style", type: "select",
            options: [
              { label: "Sepia",  value: "sepia" },
              { label: "Cool",   value: "cool" },
              { label: "Purple", value: "purple" },
            ],
            default: "sepia",
          },
        ],
      },
      {
        id: "colour/palette",
        label: "Colour Palette",
        description: "K-means dominant colours shown as swatches.",
        icon: <Palette className="w-5 h-5" />,
        endpoint: "/colour/palette",
        params: [
          {
            key: "n_colors", label: "Colours", type: "slider",
            min: 3, max: 12, step: 1, default: 6,
          },
        ],
      },
      {
        id: "colour/bw-mixer",
        label: "B&W Channel Mixer",
        description: "Cinematic greyscale with R/G/B channel weighting.",
        icon: <ScanLine className="w-5 h-5" />,
        endpoint: "/colour/bw-mixer",
        params: [
          {
            key: "r_weight", label: "Red", type: "slider-float",
            min: 0, max: 1, step: 0.05, default: 0.299,
          },
          {
            key: "g_weight", label: "Green", type: "slider-float",
            min: 0, max: 1, step: 0.05, default: 0.587,
          },
          {
            key: "b_weight", label: "Blue", type: "slider-float",
            min: 0, max: 1, step: 0.05, default: 0.114,
          },
        ],
      },
    ],
  },
  {
    id: "restoration",
    label: "Restoration & Repair",
    icon: <ScanSearch className="w-4 h-4" />,
    color: "text-green-400",
    tools: [
      {
        id: "restoration/super-resolution",
        label: "Super Resolution",
        description: "Upscale 2× or 4× via DNN (EDSR) or Lanczos4.",
        icon: <Crosshair className="w-5 h-5" />,
        endpoint: "/restoration/super-resolution",
        params: [
          {
            key: "scale", label: "Scale", type: "select",
            options: [{ label: "2×", value: "2" }, { label: "4×", value: "4" }],
            default: "2",
          },
        ],
      },
      {
        id: "restoration/deblur",
        label: "Deblur",
        description: "Wiener frequency-domain deconvolution.",
        icon: <Focus className="w-5 h-5" />,
        endpoint: "/restoration/deblur",
        params: [
          {
            key: "snr", label: "SNR", type: "slider",
            min: 5, max: 80, step: 5, default: 25,
          },
        ],
      },
      {
        id: "restoration/dejpeg",
        label: "JPEG Artefact Removal",
        description: "NL-Means tuned for block-noise and compression artefacts.",
        icon: <Grid2x2 className="w-5 h-5" />,
        endpoint: "/restoration/dejpeg",
      },
      {
        id: "restoration/inpaint",
        label: "Auto Inpaint",
        description: "Detect and fill scratches, dust, and dark/bright damage.",
        icon: <Eraser className="w-5 h-5" />,
        endpoint: "/restoration/inpaint",
        params: [
          {
            key: "radius", label: "Fill Radius", type: "slider",
            min: 3, max: 20, step: 1, default: 8,
          },
        ],
      },
    ],
  },
  {
    id: "depth",
    label: "Depth & Spatial",
    icon: <Focus className="w-4 h-4" />,
    color: "text-brand-cyan",
    tools: [
      {
        id: "depth/bokeh",
        label: "Bokeh / Background Blur",
        description: "U2-Net foreground mask → blurred background composite.",
        icon: <Eye className="w-5 h-5" />,
        endpoint: "/depth/bokeh",
        params: [
          {
            key: "blur_strength", label: "Blur Strength", type: "slider",
            min: 5, max: 50, step: 5, default: 25,
          },
        ],
      },
      {
        id: "depth/tilt-shift",
        label: "Tilt-Shift",
        description: "Horizontal focus band; miniature-world effect.",
        icon: <ScanLine className="w-5 h-5" />,
        endpoint: "/depth/tilt-shift",
        params: [
          {
            key: "focus_y", label: "Focus Position", type: "slider-float",
            min: 0.1, max: 0.9, step: 0.05, default: 0.5,
          },
          {
            key: "focus_width", label: "Focus Width", type: "slider-float",
            min: 0.05, max: 0.5, step: 0.05, default: 0.25,
          },
        ],
      },
      {
        id: "depth/perspective",
        label: "Perspective Correction",
        description: "Auto-straighten via Hough lines + homography warp.",
        icon: <Crosshair className="w-5 h-5" />,
        endpoint: "/depth/perspective",
      },
    ],
  },
  {
    id: "detection",
    label: "Detection & Smart",
    icon: <UserX className="w-4 h-4" />,
    color: "text-yellow-400",
    tools: [
      {
        id: "detection/face-blur",
        label: "Face Blur / Pixelate",
        description: "Haar cascade face detection → blur or pixelate each face.",
        icon: <UserX className="w-5 h-5" />,
        endpoint: "/detection/face-blur",
        params: [
          {
            key: "mode", label: "Effect", type: "select",
            options: [{ label: "Blur", value: "blur" }, { label: "Pixelate", value: "pixelate" }],
            default: "blur",
          },
        ],
      },
      {
        id: "detection/portrait",
        label: "Portrait Mode",
        description: "Subject on solid, blurred, or gradient background.",
        icon: <User className="w-5 h-5" />,
        endpoint: "/detection/portrait",
        params: [
          {
            key: "bg_style", label: "Background", type: "select",
            options: [
              { label: "Blur",     value: "blur" },
              { label: "White",    value: "white" },
              { label: "Black",    value: "black" },
              { label: "Gradient", value: "gradient" },
            ],
            default: "blur",
          },
        ],
      },
    ],
  },
  {
    id: "analysis",
    label: "Analysis & Diagnostics",
    icon: <BarChart3 className="w-4 h-4" />,
    color: "text-red-400",
    tools: [
      {
        id: "analysis/histogram",
        label: "Histogram Viewer",
        description: "R/G/B/Luminance channel histograms plotted below image.",
        icon: <BarChart3 className="w-5 h-5" />,
        endpoint: "/analysis/histogram",
      },
      {
        id: "analysis/noise-map",
        label: "Noise Level Map",
        description: "Local noise visualised as a JET heat-map overlay.",
        icon: <Activity className="w-5 h-5" />,
        endpoint: "/analysis/noise-map",
      },
      {
        id: "analysis/sharpness-map",
        label: "Sharpness Map",
        description: "Laplacian variance heat-map — blue=soft, red=sharp.",
        icon: <Crosshair className="w-5 h-5" />,
        endpoint: "/analysis/sharpness-map",
      },
      {
        id: "analysis/exposure-map",
        label: "Exposure Heatmap",
        description: "Highlights blown (>250) and crushed (<5) regions.",
        icon: <Lightbulb className="w-5 h-5" />,
        endpoint: "/analysis/exposure-map",
      },
    ],
  },
];

// Flat lookup: id → Tool
const TOOL_MAP: Record<string, Tool & { categoryId: string }> = {};
CATEGORIES.forEach((cat) => {
  cat.tools.forEach((t) => {
    TOOL_MAP[t.id] = { ...t, categoryId: cat.id };
  });
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Home() {
  const [selectedId, setSelectedId]         = useState<string>("remove-background");
  const [uploadedFile, setUploadedFile]     = useState<File | null>(null);
  const [previewUrl, setPreviewUrl]         = useState<string | null>(null);
  const [resultUrl, setResultUrl]           = useState<string | null>(null);
  const [isProcessing, setIsProcessing]     = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [isDragOver, setIsDragOver]         = useState(false);
  const [isDark, setIsDark]                 = useState(true);
  const [transformScore, setTransformScore] = useState<number | null>(null);
  const [openCats, setOpenCats]             = useState<Set<string>>(new Set(["core"]));
  // param state: paramKey → value
  const [params, setParams]                 = useState<Record<string, string | number>>({});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const resultRef    = useRef<HTMLDivElement>(null);

  // Sync theme on mount
  useEffect(() => { setIsDark(document.documentElement.classList.contains("dark")); }, []);
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  useEffect(() => () => { if (resultUrl)  URL.revokeObjectURL(resultUrl);  }, [resultUrl]);

  // Reset params to defaults when tool changes
  useEffect(() => {
    const tool = TOOL_MAP[selectedId];
    if (!tool?.params) { setParams({}); return; }
    const defaults: Record<string, string | number> = {};
    tool.params.forEach((p) => { defaults[p.key] = p.default; });
    setParams(defaults);
  }, [selectedId]);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem("pf-theme", next ? "dark" : "light");
    document.documentElement.classList.toggle("dark", next);
  };

  const toggleCat = (id: string) => {
    setOpenCats((prev) => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  // ── File handling ────────────────────────────────────────────────────────────
  const acceptFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) { setError("Please upload an image file."); return; }
    if (file.size > 20 * 1024 * 1024)   { setError("File must be under 20 MB."); return; }
    setError(null); setResultUrl(null);
    setUploadedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (f) acceptFile(f); e.target.value = "";
  };
  const handleDrop      = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragOver(false);
    const f = e.dataTransfer.files?.[0]; if (f) acceptFile(f);
  };
  const handleDragOver  = (e: React.DragEvent) => { e.preventDefault(); setIsDragOver(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragOver(false); };

  // ── Process ──────────────────────────────────────────────────────────────────
  const handleProcess = async () => {
    if (!uploadedFile) return;
    const tool = TOOL_MAP[selectedId];
    const form = new FormData();
    form.append("file", uploadedFile);
    Object.entries(params).forEach(([k, v]) => form.append(k, String(v)));

    setIsProcessing(true); setError(null); setResultUrl(null); setTransformScore(null);

    try {
      const res = await fetch(`${API_URL}${tool.endpoint}`, { method: "POST", body: form });
      if (!res.ok) {
        let msg = `Server error: ${res.status}`;
        try { const j = await res.json(); msg = j.detail || msg; } catch { /* ignore */ }
        throw new Error(msg);
      }
      const scoreHdr = res.headers.get("x-transform-score");
      setTransformScore(scoreHdr ? parseInt(scoreHdr, 10) : null);
      setResultUrl(URL.createObjectURL(await res.blob()));
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message.toLowerCase().includes("fetch")
            ? "Cannot reach the backend. Make sure FastAPI is running on port 8000."
            : err.message
          : "Unexpected error."
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!resultUrl) return;
    const tool = TOOL_MAP[selectedId];
    const a = document.createElement("a");
    a.href = resultUrl;
    a.download = `pixelforge-${selectedId.replace("/", "-")}.${tool.resultIsPng ? "png" : "jpg"}`;
    a.click();
  };

  const currentTool = TOOL_MAP[selectedId];
  const currentCat  = CATEGORIES.find((c) => c.id === currentTool?.categoryId);

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col">

      {/* Ambient glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-brand-purple/10 blur-[120px] opacity-40 dark:opacity-100" />
        <div className="absolute -top-20 -right-40 w-[500px] h-[500px] rounded-full bg-brand-cyan/10 blur-[120px] opacity-30 dark:opacity-100" />
      </div>

      {/* Theme toggle */}
      <button onClick={toggleTheme} className="btn-icon fixed top-4 right-4 z-50 w-10 h-10" aria-label="Toggle theme">
        {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>

      <main className="relative flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col gap-12">

        {/* ── Hero ── */}
        <section className="text-center flex flex-col items-center gap-4 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-surface-border bg-surface-card text-xs font-medium text-content-muted uppercase tracking-widest">
            <Zap className="w-3.5 h-3.5 text-brand-cyan" />
            Free · Instant · Private
          </div>
          <h1 className="text-6xl sm:text-7xl font-extrabold tracking-tight">
            <span className="gradient-text">PixelForge</span>
          </h1>
          <p className="max-w-xl text-content-muted text-lg leading-relaxed">
            Upload a photo, pick a tool, download your result.{" "}
            <span className="text-content-secondary font-medium">No account, no cloud uploads.</span>
          </p>
        </section>

        {/* ── Layout: Sidebar + Main ── */}
        <div className="flex flex-col lg:flex-row gap-8">

          {/* ── Sidebar: Category + Tool selector ── */}
          <aside className="lg:w-72 xl:w-80 flex-shrink-0 flex flex-col gap-2">
            {CATEGORIES.map((cat) => {
              const isOpen = openCats.has(cat.id);
              return (
                <div key={cat.id} className="glass-card overflow-hidden">
                  {/* Category header */}
                  <button
                    onClick={() => toggleCat(cat.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-elevated transition-colors"
                  >
                    <span className={cat.color}>{cat.icon}</span>
                    <span className="flex-1 text-sm font-semibold text-content-secondary">{cat.label}</span>
                    <span className="text-content-subtle">
                      {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </span>
                  </button>

                  {/* Tool list */}
                  {isOpen && (
                    <div className="border-t border-surface-border">
                      {cat.tools.map((tool) => {
                        const active = selectedId === tool.id;
                        return (
                          <button
                            key={tool.id}
                            onClick={() => {
                              setSelectedId(tool.id);
                              setResultUrl(null);
                              setError(null);
                            }}
                            className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all duration-150 ${
                              active
                                ? "bg-brand-purple/10 border-l-2 border-brand-purple"
                                : "border-l-2 border-transparent hover:bg-surface-elevated"
                            }`}
                          >
                            <span className={active ? "text-brand-purple" : "text-content-muted"}>
                              {tool.icon}
                            </span>
                            <div className="min-w-0">
                              <p className={`text-sm font-medium truncate ${active ? "text-content-primary" : "text-content-secondary"}`}>
                                {tool.label}
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </aside>

          {/* ── Main panel ── */}
          <div className="flex-1 flex flex-col gap-8">

            {/* Tool header + description */}
            {currentTool && (
              <div className="flex flex-col items-center text-center gap-3 animate-fade-in">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-surface-elevated ${currentCat?.color ?? "text-brand-purple"}`}>
                  {currentTool.icon}
                </div>
                <div>
                  <div className="flex items-center justify-center gap-2">
                    <h2 className="text-lg font-bold text-content-primary">{currentTool.label}</h2>
                    {currentCat && (
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full bg-surface-elevated ${currentCat.color}`}>
                        {currentCat.label}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-content-muted mt-0.5">{currentTool.description}</p>
                </div>
              </div>
            )}

            {/* ── Tool Params ── */}
            {currentTool?.params && currentTool.params.length > 0 && (
              <div className="glass-card p-5 flex flex-wrap gap-6 animate-fade-in">
                {currentTool.params.map((p) => (
                  <div key={p.key} className="flex flex-col gap-1.5 min-w-[160px]">
                    <label className="text-xs font-semibold text-content-subtle uppercase tracking-wide">
                      {p.label}
                      {(p.type === "slider" || p.type === "slider-float") && (
                        <span className="ml-2 text-brand-cyan normal-case font-mono">
                          {params[p.key] ?? p.default}
                        </span>
                      )}
                    </label>
                    {p.type === "select" && (
                      <select
                        value={String(params[p.key] ?? p.default)}
                        onChange={(e) => setParams((prev) => ({ ...prev, [p.key]: e.target.value }))}
                        className="bg-surface-elevated border border-surface-border text-content-primary text-sm rounded-lg px-3 py-2 outline-none focus:border-brand-purple transition-colors"
                      >
                        {p.options!.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    )}
                    {(p.type === "slider" || p.type === "slider-float") && (
                      <input
                        type="range"
                        min={p.min} max={p.max} step={p.step}
                        value={Number(params[p.key] ?? p.default)}
                        onChange={(e) =>
                          setParams((prev) => ({
                            ...prev,
                            [p.key]: p.type === "slider-float"
                              ? parseFloat(e.target.value)
                              : parseInt(e.target.value, 10),
                          }))
                        }
                        className="accent-brand-purple w-full"
                      />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* ── Upload ── */}
            {!uploadedFile ? (
              <div
                onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={`glass-card border-2 border-dashed border-surface-border rounded-2xl p-12 flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-200 min-h-[200px] ${
                  isDragOver ? "drop-zone-active" : "hover:border-brand-purple/40 hover:bg-brand-purple/5"
                }`}
              >
                <div className="w-14 h-14 rounded-2xl bg-surface-elevated flex items-center justify-center">
                  <Upload className="w-6 h-6 text-content-muted" />
                </div>
                <div className="text-center">
                  <p className="text-content-secondary font-medium mb-1">
                    Drop an image here, or{" "}
                    <span className="text-brand-purple">click to browse</span>
                  </p>
                  <p className="text-sm text-content-subtle">JPEG, PNG, WebP · Max 20 MB</p>
                </div>
                <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
              </div>
            ) : (
              <div className="glass-card p-4 flex gap-4 items-center animate-fade-in">
                <div className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 bg-surface-elevated checkerboard">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={previewUrl!} alt="Preview" className="w-full h-full object-cover" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-content-primary font-medium truncate">{uploadedFile.name}</p>
                  <p className="text-sm text-content-muted mt-0.5">{formatBytes(uploadedFile.size)}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => fileInputRef.current?.click()} className="btn-secondary text-xs">
                    <ImageIcon className="w-3.5 h-3.5" /> Change
                  </button>
                  <button onClick={() => { setUploadedFile(null); setPreviewUrl(null); setResultUrl(null); setError(null); }} className="btn-secondary text-xs">
                    <X className="w-3.5 h-3.5" /> Remove
                  </button>
                </div>
                <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
              </div>
            )}

            {/* ── Error ── */}
            {error && (
              <div className="flex items-start gap-3 p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-500 dark:text-red-400 text-sm animate-fade-in">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span className="flex-1">{error}</span>
                <button onClick={() => setError(null)} className="opacity-60 hover:opacity-100"><X className="w-4 h-4" /></button>
              </div>
            )}

            {/* ── Process Button ── */}
            <div className="flex justify-center">
              <button onClick={handleProcess} disabled={!uploadedFile || isProcessing} className="btn-primary text-base px-10 py-4">
                {isProcessing
                  ? <><Loader2 className="w-5 h-5 animate-spin" /> Processing…</>
                  : <>{currentTool?.icon} Run {currentTool?.label}</>
                }
              </button>
            </div>

            {/* ── Result ── */}
            {resultUrl && (
              <section ref={resultRef} className="flex flex-col gap-6 animate-slide-up">
                <div className="flex items-center gap-4">
                  <h2 className="text-xs font-semibold uppercase tracking-widest text-content-subtle shrink-0">Result</h2>

                  {transformScore !== null && (
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="flex-1 h-2 rounded-full bg-surface-elevated overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${transformScore}%`,
                            background: transformScore >= 80 ? "#22c55e" : transformScore >= 65 ? "#f97316" : "#ef4444",
                          }}
                        />
                      </div>
                      <span className="text-sm font-bold tabular-nums shrink-0"
                        style={{ color: transformScore >= 80 ? "#22c55e" : transformScore >= 65 ? "#f97316" : "#ef4444" }}>
                        {transformScore}<span className="text-xs font-medium opacity-70">/99</span>
                      </span>
                    </div>
                  )}

                  <button onClick={handleDownload} className="btn-secondary shrink-0">
                    <Download className="w-4 h-4" /> Download
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="glass-card p-4 flex flex-col gap-3">
                    <p className="text-xs font-semibold uppercase tracking-widest text-content-subtle">Original</p>
                    <div className="rounded-xl overflow-hidden bg-surface-elevated checkerboard">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={previewUrl!} alt="Original" className="w-full h-auto object-contain max-h-[420px]" />
                    </div>
                  </div>
                  <div className="glass-card p-4 flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold uppercase tracking-widest text-content-subtle">Processed</p>
                      <span className={`text-xs font-medium ${currentCat?.color ?? "text-brand-cyan"}`}>{currentTool?.label}</span>
                    </div>
                    <div className="rounded-xl overflow-hidden bg-surface-elevated checkerboard">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={resultUrl} alt="Result" className="w-full h-auto object-contain max-h-[420px]" />
                    </div>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </main>

      <footer className="relative border-t border-surface-border mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between text-sm text-content-subtle">
          <span>No data stored · No cloud processing · 100% on-device</span>
          <span className="gradient-text font-semibold">PixelForge</span>
        </div>
      </footer>
    </div>
  );
}
