"""Services package initialization."""

from importlib import metadata

try:
    # Expose wrapper at package level for convenience
    from .yt_dlp_wrapper import YtDlpWrapper  # noqa: F401
except ModuleNotFoundError:
    # Wrapper may not be available yet during initial installation
    YtDlpWrapper = None  # type: ignore

__all__ = [
    "YtDlpWrapper",
]

try:
    __version__ = metadata.version("yt-dlp")
except metadata.PackageNotFoundError:  # type: ignore[attr-defined]
    __version__ = "not-installed" 