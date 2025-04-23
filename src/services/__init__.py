"""Services package initialization."""

from importlib import metadata

try:
    # Expose wrapper at package level for convenience
    from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError  # noqa: F401
except ModuleNotFoundError:
    # Wrapper may not be available yet during initial installation
    YtDlpWrapper = None  # type: ignore
    YtDlpError = RuntimeError  # type: ignore

# Import caption models
try:
    from .caption_model import Caption, CaptionLine, CaptionMetadata, CaptionError
except ModuleNotFoundError:
    Caption = None  # type: ignore
    CaptionLine = None  # type: ignore
    CaptionMetadata = None  # type: ignore
    CaptionError = RuntimeError  # type: ignore

# Import subtitle parser
try:
    from .subtitle_parser import ParserFactory, ParserError, SrtParser, VttParser
except ModuleNotFoundError:
    ParserFactory = None  # type: ignore
    ParserError = RuntimeError  # type: ignore
    SrtParser = None  # type: ignore
    VttParser = None  # type: ignore

# Import caption service
try:
    from .caption_service import CaptionService
except ModuleNotFoundError:
    CaptionService = None  # type: ignore

__all__ = [
    "YtDlpWrapper",
    "YtDlpError",
    "Caption",
    "CaptionLine",
    "CaptionMetadata",
    "CaptionError",
    "ParserFactory",
    "ParserError",
    "SrtParser",
    "VttParser",
    "CaptionService",
]

try:
    __version__ = metadata.version("yt-dlp")
except metadata.PackageNotFoundError:  # type: ignore[attr-defined]
    __version__ = "not-installed" 
# Import subtitle parser
try:
    from .subtitle_parser import ParserFactory, ParserError, SrtParser, VttParser
except ModuleNotFoundError:
    ParserFactory = None  # type: ignore
    ParserError = RuntimeError  # type: ignore
    SrtParser = None  # type: ignore
    VttParser = None  # type: ignore

# Import caption service
try:
    from .caption_service import CaptionService
except ModuleNotFoundError:
    CaptionService = None  # type: ignore

__all__ = [
    "YtDlpWrapper",
    "YtDlpError",
    "Caption",
    "CaptionLine",
    "CaptionMetadata",
    "CaptionError",
    "ParserFactory",
    "ParserError",
    "SrtParser",
    "VttParser",
    "CaptionService",
]

try:
    __version__ = metadata.version("yt-dlp")
except metadata.PackageNotFoundError:  # type: ignore[attr-defined]
    __version__ = "not-installed" 