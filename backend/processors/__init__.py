from .analysis       import AnalysisProcessor
from .background     import BackgroundRemover
from .colour         import ColourProcessor
from .depth          import DepthProcessor
from .detection      import DetectionProcessor
from .enhancer       import Enhancer
from .filters        import FiltersProcessor
from .restoration    import RestorationProcessor
from .sketch_cartoon import SketchCartoon

__all__ = [
    "AnalysisProcessor",
    "BackgroundRemover",
    "ColourProcessor",
    "DepthProcessor",
    "DetectionProcessor",
    "Enhancer",
    "FiltersProcessor",
    "RestorationProcessor",
    "SketchCartoon",
]
