"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import {
  Scissors, Sparkles, Pencil, Upload, Download, Loader2,
  AlertCircle, X, ImageIcon, Zap, Sun, Moon,
  Paintbrush, Droplets, Gauge, Grid2x2,
  Eye, Palette, Eraser, ScanLine, Focus, ScanSearch,
  UserX, User, BarChart3, Activity, Crosshair, Lightbulb,
  ChevronDown, ChevronRight, Film, Wand2, Users, Brush,
  Plus, CheckCircle2, Clock,
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
  maskTool?: boolean;   // requires canvas mask drawn by user
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
      {
        id: "detection/remove-object",
        label: "Object Remover",
        description: "Paint over any object to erase it. Uses inpainting to fill seamlessly.",
        icon: <Eraser className="w-5 h-5" />,
        endpoint: "/detection/remove-object",
        maskTool: true,
        params: [
          { key: "radius", label: "Radius", type: "slider", min: 4, max: 30, step: 1, default: 12 },
        ],
      },
      {
        id: "detection/remove-people",
        label: "Remove People",
        description: "Auto-detect and erase people from the image using HOG + inpainting.",
        icon: <Users className="w-5 h-5" />,
        endpoint: "/detection/remove-people",
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

// ── Custom themed dropdown ─────────────────────────────────────────────────────
function CustomSelect({ value, onChange, options }: {
  value: string;
  onChange: (v: string) => void;
  options: { label: string; value: string }[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = options.find(o => o.value === value);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(p => !p)}
        className="flex items-center gap-1.5 bg-transparent text-content-primary text-xs font-semibold outline-none cursor-pointer hover:text-brand-purple transition-colors"
      >
        {selected?.label ?? value}
        <ChevronDown className={`w-3 h-3 text-content-muted transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-2 min-w-[120px] rounded-xl border border-surface-border overflow-hidden z-[100] animate-fade-in"
          style={{background:"var(--bg-card)", boxShadow:"0 16px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04)"}}>
          {options.map(opt => (
            <button key={opt.value} type="button"
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm transition-colors ${
                opt.value === value
                  ? "bg-brand-purple/15 text-brand-purple font-semibold"
                  : "text-content-secondary hover:bg-surface-elevated hover:text-content-primary"
              }`}>
              {opt.value === value && <div className="w-1.5 h-1.5 rounded-full bg-brand-purple flex-shrink-0" />}
              {opt.value !== value && <div className="w-1.5 h-1.5 flex-shrink-0" />}
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── FileEntry type for multi-file support ──────────────────────────────────────
interface FileEntry {
  id: string;
  file: File;
  previewUrl: string;
  resultBlob: Blob | null;
  resultUrl: string | null;
  score: number | null;
  status: "idle" | "processing" | "done" | "error";
  error: string | null;
}

const FORMATS = [
  { label: "JPEG",  ext: "jpg",  mime: "image/jpeg" },
  { label: "PNG",   ext: "png",  mime: "image/png"  },
  { label: "WebP",  ext: "webp", mime: "image/webp" },
  { label: "AVIF",  ext: "avif", mime: "image/avif" },
];

// ── Main component ─────────────────────────────────────────────────────────────
export default function Home() {
  const [selectedId, setSelectedId]     = useState<string>("remove-background");
  const [files, setFiles]               = useState<FileEntry[]>([]);
  const [isDragOver, setIsDragOver]     = useState(false);
  const [isDark, setIsDark]             = useState(true);
  const [openCat, setOpenCat]           = useState<string>("core");
  const [toolSearch, setToolSearch]     = useState<string>("");
  const [params, setParams]             = useState<Record<string, string | number>>({});
  const [brushSize, setBrushSize]       = useState<number>(30);
  const [isDrawingMask, setIsDrawingMask] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<string>("jpg");
  const [isProcessingAll, setIsProcessingAll] = useState(false);
  const [globalError, setGlobalError]   = useState<string | null>(null);

  const fileInputRef  = useRef<HTMLInputElement>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement>(null);
  const imgPreviewRef = useRef<HTMLImageElement>(null);

  // Sync theme on mount
  useEffect(() => { setIsDark(document.documentElement.classList.contains("dark")); }, []);

  // Revoke all URLs on unmount
  useEffect(() => () => {
    files.forEach(e => { URL.revokeObjectURL(e.previewUrl); if (e.resultUrl) URL.revokeObjectURL(e.resultUrl); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset params when tool changes
  useEffect(() => {
    const tool = TOOL_MAP[selectedId];
    if (!tool?.params) { setParams({}); return; }
    const defaults: Record<string, string | number> = {};
    tool.params.forEach((p) => { defaults[p.key] = p.default; });
    setParams(defaults);
  }, [selectedId]);

  // Clear mask on tool change
  useEffect(() => {
    const c = maskCanvasRef.current;
    if (c) { const ctx = c.getContext("2d"); ctx?.clearRect(0, 0, c.width, c.height); }
  }, [selectedId]);

  // ── Canvas mask painting ─────────────────────────────────────────────────────
  const paintMask = useCallback((e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = maskCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    ctx.fillStyle = "rgba(255,80,80,0.85)";
    ctx.beginPath();
    ctx.arc((clientX - rect.left) * scaleX, (clientY - rect.top) * scaleY, brushSize * scaleX, 0, Math.PI * 2);
    ctx.fill();
  }, [brushSize]);

  const clearMask = useCallback(() => {
    const c = maskCanvasRef.current;
    if (c) { const ctx = c.getContext("2d"); ctx?.clearRect(0, 0, c.width, c.height); }
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    localStorage.setItem("pf-theme", next ? "dark" : "light");
    document.documentElement.classList.toggle("dark", next);
  };

  const toggleCat = (id: string) => setOpenCat((prev) => (prev === id ? "" : id));

  // ── File handling ─────────────────────────────────────────────────────────────
  const addFiles = useCallback((incoming: File[]) => {
    setGlobalError(null);
    const valid = incoming.filter(f => {
      if (!f.type.startsWith("image/")) return false;
      if (f.size > 20 * 1024 * 1024)    return false;
      return true;
    });
    if (valid.length < incoming.length) setGlobalError("Some files were skipped (not an image or >20 MB).");
    setFiles(prev => [
      ...prev,
      ...valid.map(f => ({
        id: crypto.randomUUID(),
        file: f,
        previewUrl: URL.createObjectURL(f),
        resultBlob: null,
        resultUrl:  null,
        score:      null,
        status:     "idle" as const,
        error:      null,
      })),
    ]);
  }, []);

  const removeEntry = useCallback((id: string) => {
    setFiles(prev => {
      const e = prev.find(x => x.id === id);
      if (e) { URL.revokeObjectURL(e.previewUrl); if (e.resultUrl) URL.revokeObjectURL(e.resultUrl); }
      return prev.filter(x => x.id !== id);
    });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(Array.from(e.target.files));
    e.target.value = "";
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragOver(false);
    if (e.dataTransfer.files) addFiles(Array.from(e.dataTransfer.files));
  };
  const handleDragOver  = (e: React.DragEvent) => { e.preventDefault(); setIsDragOver(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragOver(false); };

  // ── Process all files ─────────────────────────────────────────────────────────
  const getMaskBlob = async (): Promise<Blob | null> => {
    if (!maskCanvasRef.current) return null;
    return new Promise<Blob | null>(res => maskCanvasRef.current!.toBlob(res, "image/png"));
  };

  const processAll = async () => {
    const tool = TOOL_MAP[selectedId];
    const toProcess = files.filter(e => e.status === "idle" || e.status === "error");
    if (toProcess.length === 0) return;
    setIsProcessingAll(true);
    setGlobalError(null);

    const maskBlob = tool.maskTool ? await getMaskBlob() : null;

    for (const entry of toProcess) {
      setFiles(prev => prev.map(e => e.id === entry.id ? { ...e, status: "processing", error: null } : e));
      try {
        const form = new FormData();
        form.append("file", entry.file);
        Object.entries(params).forEach(([k, v]) => form.append(k, String(v)));
        if (maskBlob) form.append("mask", maskBlob, "mask.png");

        const res = await fetch(`${API_URL}${tool.endpoint}`, { method: "POST", body: form });
        if (!res.ok) {
          let msg = `Server error ${res.status}`;
          try { const j = await res.json(); msg = j.detail || msg; } catch { /* ignore */ }
          throw new Error(msg);
        }
        const score = res.headers.get("x-transform-score");
        const blob  = await res.blob();
        const url   = URL.createObjectURL(blob);
        setFiles(prev => prev.map(e => e.id === entry.id
          ? { ...e, status: "done", resultBlob: blob, resultUrl: url, score: score ? parseInt(score, 10) : null }
          : e));
      } catch (err) {
        const msg = err instanceof Error
          ? err.message.toLowerCase().includes("fetch")
            ? "Cannot reach backend (port 8000)."
            : err.message
          : "Unexpected error.";
        setFiles(prev => prev.map(e => e.id === entry.id ? { ...e, status: "error", error: msg } : e));
      }
    }
    setIsProcessingAll(false);
  };

  // ── Download helpers ──────────────────────────────────────────────────────────
  const convertBlob = async (blob: Blob, url: string, mime: string): Promise<Blob> => {
    if (blob.type === mime) return blob;
    const img = new Image();
    img.src = url;
    await new Promise<void>(r => { img.onload = () => r(); });
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    canvas.getContext("2d")!.drawImage(img, 0, 0);
    return new Promise<Blob>(r => canvas.toBlob(b => r(b!), mime, 0.92)!);
  };

  const downloadEntry = async (entry: FileEntry) => {
    if (!entry.resultBlob || !entry.resultUrl) return;
    const fmt  = FORMATS.find(f => f.ext === selectedFormat) ?? FORMATS[0];
    const blob = await convertBlob(entry.resultBlob, entry.resultUrl, fmt.mime);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${entry.file.name.replace(/\.[^.]+$/, "")}_pf.${fmt.ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const downloadAllZip = async () => {
    const done = files.filter(e => e.status === "done" && e.resultBlob);
    if (done.length === 0) return;
    const fmt = FORMATS.find(f => f.ext === selectedFormat) ?? FORMATS[0];
    const JSZip = (await import("jszip")).default;
    const zip   = new JSZip();
    for (const entry of done) {
      const blob = await convertBlob(entry.resultBlob!, entry.resultUrl!, fmt.mime);
      zip.file(`${entry.file.name.replace(/\.[^.]+$/, "")}_pf.${fmt.ext}`, blob);
    }
    const zipBlob = await zip.generateAsync({ type: "blob" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(zipBlob);
    a.download = "pixelforge-results.zip";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const currentTool = TOOL_MAP[selectedId];
  const currentCat  = CATEGORIES.find((c) => c.id === currentTool?.categoryId);
  const doneCount   = files.filter(e => e.status === "done").length;
  const firstFile   = files[0] ?? null;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-base)]">
      {/* Ambient glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-60 -left-60 w-[800px] h-[800px] rounded-full bg-brand-purple/8 blur-[140px]" />
        <div className="absolute top-1/3 -right-60 w-[600px] h-[600px] rounded-full bg-brand-cyan/8 blur-[140px]" />
      </div>

      {/* ══ Sticky Header ══ */}
      <header className="sticky top-0 z-50 border-b border-surface-border bg-surface-card/90 backdrop-blur-xl">
        <div className="w-full px-4 sm:px-6 lg:px-10 h-14 flex items-center gap-3">
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-purple to-brand-cyan flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-extrabold tracking-tight"><span className="gradient-text">PixelForge</span></h1>
          </div>
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-surface-border text-xs text-content-muted">
            Free · Instant · Private
          </div>
          <div className="flex-1" />
          {/* Search */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-surface-border bg-surface-elevated w-40 sm:w-56 md:w-72 transition-all focus-within:border-brand-purple/50 focus-within:bg-surface-card">
            <ScanSearch className="w-3.5 h-3.5 text-content-muted flex-shrink-0" />
            <input type="text" placeholder="Search 34 tools…" value={toolSearch}
              onChange={e => setToolSearch(e.target.value)}
              className="flex-1 bg-transparent text-sm text-content-primary placeholder:text-content-subtle outline-none min-w-0" />
            {toolSearch && <button onClick={() => setToolSearch("")} className="text-content-subtle hover:text-content-primary transition-colors"><X className="w-3.5 h-3.5" /></button>}
          </div>
          <button onClick={toggleTheme} className="btn-icon w-9 h-9 flex-shrink-0" aria-label="Toggle theme">
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* ══ Sticky Tool Navigator ══ */}
      <div className="sticky top-14 z-40 border-b border-surface-border bg-surface-card/80 backdrop-blur-xl">
        <div className="w-full px-4 sm:px-6 lg:px-10 h-11 flex items-center gap-1">
          {openCat && !toolSearch && <div className="fixed inset-0 z-10" onClick={() => setOpenCat("")} />}

          {!toolSearch && CATEGORIES.map(cat => {
            const isActive = openCat === cat.id;
            const hasTool  = cat.tools.some(t => t.id === selectedId);
            return (
              <div key={cat.id} className="relative z-20 flex-shrink-0">
                <button onClick={() => toggleCat(cat.id)}
                  className={`flex items-center gap-1.5 px-2.5 h-8 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                    isActive ? "bg-brand-purple/15 text-content-primary ring-1 ring-brand-purple/30"
                    : hasTool ? "bg-surface-elevated text-content-primary"
                    : "text-content-muted hover:bg-surface-elevated hover:text-content-secondary"}`}>
                  <span className={isActive || hasTool ? cat.color : "opacity-60"}>{cat.icon}</span>
                  <span className="hidden md:inline">{cat.label}</span>
                  <ChevronDown className={`w-3 h-3 opacity-60 transition-transform duration-200 ${isActive ? "rotate-180" : ""}`} />
                </button>
                {isActive && (
                  <div className="absolute top-full left-0 mt-2 w-56 rounded-2xl border border-surface-border overflow-hidden animate-fade-in"
                    style={{background:"var(--bg-card)", boxShadow:"0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)"}}>
                    <div className="px-4 py-3 border-b border-surface-border bg-surface-elevated/50">
                      <p className={`text-xs font-bold uppercase tracking-widest ${cat.color}`}>{cat.label}</p>
                    </div>
                    <div className="py-1">
                      {cat.tools.map(tool => {
                        const active = selectedId === tool.id;
                        return (
                          <button key={tool.id}
                            onClick={() => { setSelectedId(tool.id); setOpenCat(""); setFiles(prev => prev.map(e => ({...e, resultUrl: null, resultBlob: null, status: "idle"}))); }}
                            className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${active ? "bg-brand-purple/12 text-brand-purple" : "text-content-secondary hover:bg-surface-elevated/70 hover:text-content-primary"}`}>
                            <span className={`flex-shrink-0 ${active ? "text-brand-purple" : "text-content-muted"}`}>{tool.icon}</span>
                            <span className="text-sm font-medium flex-1">{tool.label}</span>
                            {active && <CheckCircle2 className="w-3.5 h-3.5 text-brand-purple flex-shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {toolSearch && (() => {
            const q = toolSearch.toLowerCase();
            const matches = CATEGORIES.flatMap(cat => cat.tools
              .filter(t => t.label.toLowerCase().includes(q) || t.description.toLowerCase().includes(q))
              .map(t => ({ tool: t, cat })));
            return matches.length === 0
              ? <p className="text-xs text-content-subtle px-2">No tools match &ldquo;{toolSearch}&rdquo;</p>
              : <div className="flex gap-1.5 overflow-x-auto scrollbar-hide flex-1 py-1">
                  {matches.map(({ tool, cat }) => (
                    <button key={tool.id} onClick={() => { setSelectedId(tool.id); setToolSearch(""); }}
                      className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                        selectedId === tool.id ? "bg-brand-purple/20 border-brand-purple/40 text-brand-purple"
                        : "bg-surface-card border-surface-border text-content-muted hover:bg-surface-elevated"}`}>
                      {tool.icon}<span>{tool.label}</span>
                      <span className="text-content-subtle/50 hidden sm:inline">· {cat.label}</span>
                    </button>
                  ))}
                </div>;
          })()}
        </div>
      </div>

      {/* ══ Main scrollable content ══ */}
      <main className="relative z-10 flex-1 w-full px-4 sm:px-6 lg:px-10 py-6 space-y-6">

        {/* ── Tool action bar ── */}
        {currentTool && (
          <div className="glass-card px-4 sm:px-6 py-4 flex flex-wrap items-center gap-3 md:gap-4">
            {/* Tool identity */}
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${currentCat?.color ?? "text-brand-purple"}`}
              style={{background:"var(--bg-elevated)"}}>
              {currentTool.icon}
            </div>
            <div className="min-w-0 flex-shrink-0">
              <p className="text-sm font-bold text-content-primary">{currentTool.label}</p>
              <p className="text-xs text-content-muted mt-0.5 max-w-[220px] sm:max-w-xs truncate">{currentTool.description}</p>
            </div>

            {/* Params */}
            {currentTool.params?.map(p => (
              <div key={p.key} className="flex items-center gap-2 flex-shrink-0 bg-surface-elevated border border-surface-border rounded-lg px-3 py-1.5">
                <span className="text-xs text-content-subtle font-medium">{p.label}</span>
                {p.type === "select" && (
                  <CustomSelect
                    value={String(params[p.key] ?? p.default)}
                    onChange={v => setParams(prev => ({...prev, [p.key]: v}))}
                    options={p.options!}
                  />
                )}
                {(p.type === "slider" || p.type === "slider-float") && (
                  <div className="flex items-center gap-2">
                    <input type="range" min={p.min} max={p.max} step={p.step}
                      value={Number(params[p.key] ?? p.default)}
                      onChange={e => setParams(prev => ({...prev, [p.key]: p.type === "slider-float" ? parseFloat(e.target.value) : parseInt(e.target.value, 10)}))}
                      className="accent-brand-purple w-24" />
                    <span className="text-xs font-mono text-brand-cyan w-8 text-right tabular-nums">{params[p.key] ?? p.default}</span>
                  </div>
                )}
              </div>
            ))}

            <div className="flex-1" />

            {globalError && (
              <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-1.5">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="max-w-[180px] truncate">{globalError}</span>
                <button onClick={() => setGlobalError(null)} className="ml-1 hover:opacity-70"><X className="w-3.5 h-3.5" /></button>
              </div>
            )}

            {/* Format */}
            <div className="flex items-center gap-2 bg-surface-elevated border border-surface-border rounded-lg px-3 py-1.5">
              <span className="text-xs text-content-subtle">Format</span>
              <CustomSelect
                value={selectedFormat}
                onChange={setSelectedFormat}
                options={FORMATS.map(f => ({ label: f.label, value: f.ext }))}
              />
            </div>

            {doneCount > 1 && (
              <button onClick={downloadAllZip}
                className="flex items-center gap-2 bg-surface-elevated hover:bg-surface-card border border-surface-border rounded-xl px-4 py-2 text-sm font-medium text-content-secondary hover:text-content-primary transition-all">
                <Download className="w-4 h-4" /> ZIP ({doneCount})
              </button>
            )}

            <button onClick={processAll}
              disabled={files.length === 0 || isProcessingAll || files.every(e => e.status === "done")}
              className="btn-primary px-6 py-2.5 text-sm font-semibold rounded-xl disabled:opacity-40 disabled:cursor-not-allowed">
              {isProcessingAll
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</>
                : <><span className="mr-1">{currentTool.icon}</span>Run{files.length > 1 ? ` All (${files.length})` : ""}</>}
            </button>
          </div>
        )}

        {/* ── Upload section ── */}
        <section className="space-y-4">
          {/* Drop zone */}
          <div onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`relative rounded-2xl border-2 border-dashed p-8 sm:p-12 flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-300 group ${
              isDragOver
                ? "border-brand-purple bg-brand-purple/10 scale-[1.01]"
                : "border-surface-border hover:border-brand-purple/50 hover:bg-brand-purple/5"}`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${isDragOver ? "bg-brand-purple/20 scale-110" : "bg-surface-elevated group-hover:bg-surface-card"}`}>
              <Upload className={`w-7 h-7 transition-colors ${isDragOver ? "text-brand-purple" : "text-content-muted group-hover:text-content-secondary"}`} />
            </div>
            <div className="text-center">
              <p className="text-base font-semibold text-content-secondary group-hover:text-content-primary transition-colors">
                Drop images here, or <span className="text-brand-purple">click to browse</span>
              </p>
              <p className="text-sm text-content-muted mt-1">Multiple files supported · JPEG, PNG, WebP, AVIF · Max 20 MB each</p>
            </div>
            {files.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-content-muted bg-surface-elevated px-3 py-1.5 rounded-full border border-surface-border">
                <Plus className="w-3 h-3" /> Add more images
              </div>
            )}
            <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileChange} />
          </div>

          {/* Mask brush controls */}
          {currentTool?.maskTool && files.length > 0 && (
            <div className="glass-card px-4 py-3 flex flex-wrap items-center gap-3">
              <Brush className="w-4 h-4 text-brand-purple flex-shrink-0" />
              <span className="text-sm font-medium text-content-primary">Paint to select</span>
              <div className="flex items-center gap-2 bg-surface-elevated border border-surface-border rounded-lg px-3 py-1.5">
                <span className="text-xs text-content-subtle">Brush size</span>
                <input type="range" min={8} max={80} value={brushSize} onChange={e => setBrushSize(+e.target.value)} className="accent-brand-purple w-24" />
                <span className="text-xs font-mono text-brand-cyan w-6 tabular-nums">{brushSize}</span>
              </div>
              <button onClick={clearMask} className="flex items-center gap-1.5 text-xs text-content-muted hover:text-content-primary border border-surface-border bg-surface-elevated hover:bg-surface-card px-3 py-1.5 rounded-lg transition-all">
                <Eraser className="w-3.5 h-3.5" /> Clear mask
              </button>
              <p className="text-xs text-content-muted ml-auto hidden sm:block">Paint red over the object, then click Run.</p>
            </div>
          )}

          {/* File grid */}
          {files.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-8 gap-3">
              {files.map((entry, idx) => (
                <div key={entry.id} className={`relative rounded-xl overflow-hidden border transition-all ${
                  entry.status === "done" ? "border-green-500/40" : entry.status === "error" ? "border-red-500/40" : entry.status === "processing" ? "border-brand-purple/60 ring-2 ring-brand-purple/20" : "border-surface-border"
                } bg-surface-elevated group`}>
                  <div className="aspect-square relative">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img ref={idx === 0 ? imgPreviewRef : undefined}
                      src={entry.previewUrl} alt={entry.file.name}
                      className="w-full h-full object-cover"
                      onLoad={e => { if (idx === 0 && maskCanvasRef.current) { maskCanvasRef.current.width = e.currentTarget.naturalWidth; maskCanvasRef.current.height = e.currentTarget.naturalHeight; }}} />
                    {/* Mask canvas for first file */}
                    {currentTool?.maskTool && idx === 0 && (
                      <canvas ref={maskCanvasRef} className="absolute inset-0 w-full h-full" style={{cursor:"crosshair"}}
                        onMouseDown={e => { setIsDrawingMask(true); paintMask(e); }}
                        onMouseMove={e => { if (isDrawingMask) paintMask(e); }}
                        onMouseUp={() => setIsDrawingMask(false)} onMouseLeave={() => setIsDrawingMask(false)}
                        onTouchStart={e => { e.preventDefault(); setIsDrawingMask(true); paintMask(e); }}
                        onTouchMove={e => { e.preventDefault(); if (isDrawingMask) paintMask(e); }}
                        onTouchEnd={() => setIsDrawingMask(false)} />
                    )}
                    {/* Status overlay */}
                    {entry.status === "processing" && (
                      <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-brand-purple animate-spin" />
                      </div>
                    )}
                    {entry.status === "done" && (
                      <div className="absolute top-1.5 left-1.5">
                        <CheckCircle2 className="w-4 h-4 text-green-400 drop-shadow" />
                      </div>
                    )}
                    {entry.status === "error" && (
                      <div className="absolute inset-0 bg-red-900/40 flex items-center justify-center">
                        <AlertCircle className="w-5 h-5 text-red-400" />
                      </div>
                    )}
                    {/* Remove button */}
                    <button onClick={() => removeEntry(entry.id)}
                      className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500">
                      <X className="w-3 h-3" />
                    </button>
                    {/* Download on hover for done */}
                    {entry.status === "done" && (
                      <button onClick={() => downloadEntry(entry)}
                        className="absolute bottom-1.5 right-1.5 w-6 h-6 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-brand-purple">
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="px-2 py-1.5">
                    <p className="text-xs text-content-secondary truncate font-medium">{entry.file.name}</p>
                    <div className="flex items-center justify-between mt-0.5">
                      <p className="text-xs text-content-subtle">{formatBytes(entry.file.size)}</p>
                      {entry.score !== null && (
                        <span className="text-xs font-bold tabular-nums"
                          style={{color: entry.score >= 80 ? "#22c55e" : entry.score >= 65 ? "#f97316" : "#ef4444"}}>
                          {entry.score}
                        </span>
                      )}
                      {entry.status === "idle" && <Clock className="w-3 h-3 text-content-subtle" />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Results section ── */}
        {files.some(e => e.status === "done" && e.resultUrl) && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-content-primary">Results</h2>
              <span className="text-sm text-content-muted">{doneCount} processed</span>
              <div className="flex-1 h-px bg-surface-border" />
            </div>

            <div className="space-y-6">
              {files.filter(e => e.status === "done" && e.resultUrl).map(entry => {
                const scoreColor = entry.score !== null
                  ? entry.score >= 80 ? "#22c55e" : entry.score >= 65 ? "#f97316" : "#ef4444"
                  : null;
                return (
                  <div key={entry.id} className="glass-card overflow-hidden animate-slide-up">
                    {/* Card header */}
                    <div className="flex items-center gap-3 px-5 py-3.5 border-b border-surface-border">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${currentCat?.color ?? "text-brand-purple"}`}
                        style={{background:"var(--bg-elevated)"}}>
                        {currentTool?.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-content-primary truncate">{entry.file.name}</p>
                        <p className="text-xs text-content-muted">{formatBytes(entry.file.size)} · {currentTool?.label}</p>
                      </div>
                      {entry.score !== null && scoreColor && (
                        <div className="flex items-center gap-2.5 flex-shrink-0">
                          <div className="w-28 h-2 rounded-full bg-surface-elevated overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{width:`${entry.score}%`, background: scoreColor}} />
                          </div>
                          <span className="text-sm font-bold tabular-nums w-10" style={{color: scoreColor}}>
                            {entry.score}<span className="text-xs font-medium opacity-50">/99</span>
                          </span>
                        </div>
                      )}
                      <button onClick={() => downloadEntry(entry)}
                        className="flex items-center gap-2 btn-primary text-sm px-4 py-2 flex-shrink-0">
                        <Download className="w-4 h-4" /> {selectedFormat.toUpperCase()}
                      </button>
                    </div>

                    {/* Before / After 50-50 */}
                    <div className="grid grid-cols-2 divide-x divide-surface-border">
                      <div className="relative bg-surface-elevated checkerboard">
                        <p className="absolute top-3 left-3 z-10 text-xs font-semibold text-white bg-black/50 backdrop-blur-sm px-2.5 py-1 rounded-full">Before</p>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={entry.previewUrl} alt="Before" className="w-full object-contain block" style={{maxHeight:"60vh"}} />
                      </div>
                      <div className="relative bg-surface-elevated checkerboard">
                        <p className="absolute top-3 right-3 z-10 text-xs font-semibold text-white bg-black/50 backdrop-blur-sm px-2.5 py-1 rounded-full">After</p>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={entry.resultUrl!} alt="After" className="w-full object-contain block" style={{maxHeight:"60vh"}} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Empty state ── */}
        {files.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-content-muted">
            <div className="w-20 h-20 rounded-3xl bg-surface-elevated border border-surface-border flex items-center justify-center">
              <ImageIcon className="w-9 h-9 opacity-40" />
            </div>
            <p className="text-base font-medium text-content-secondary">Upload images to get started</p>
            <p className="text-sm text-content-muted">Choose a tool above, drop your photos, and hit Run</p>
          </div>
        )}

        <div className="h-8" />
      </main>
    </div>
  );
}
