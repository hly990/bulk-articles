from __future__ import annotations

"""Lightweight wrapper around the ``yt_dlp`` Python API / CLI.

This helper fulfils *task 2.1 (Set up **yt‑dlp** library integration)*:

1. Checks that the library is importable at runtime.
2. Provides convenience methods to:
   • validate installation
   • fetch basic video metadata (without download)
   • execute arbitrary yt‑dlp CLI commands (fallback / advanced)
3. Surfaces clear, typed exceptions for UI‑layer handling.
"""

from pathlib import Path
import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

try:
    import yt_dlp  # noqa: F401
except ImportError as exc:  # pragma: no cover – wrapped in function-level check
    # Lazy‑raise when actually used so that unit tests can monkey‑patch
    yt_dlp = None  # type: ignore  # pylint: disable=invalid-name
    _import_error: Optional[ImportError] = exc  # Store for later message
else:
    _import_error = None

__all__ = [
    "YtDlpError",
    "YtDlpWrapper",
]


class YtDlpError(RuntimeError):
    """Common base error for all wrapper‑raised issues."""


class YtDlpWrapper:
    """Simple façade over *yt‑dlp* for unified error handling.

    Parameters
    ----------
    ydl_opts : dict | None
        Extra options forwarded to :class:`yt_dlp.YoutubeDL`.  The wrapper adds
        a few sensible defaults (quiet extraction, no download) which can be
        overridden here.
    logger : logging.Logger | None
        Logger to use.  If *None*, the module‑level logger is employed.
    """

    # Minimal default YDL options – callers may override as needed
    _BASE_OPTS: Dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        # Ensure predictable JSON output for CLI fallback
        "dumpjson": True,
    }

    def __init__(
        self,
        ydl_opts: Optional[Dict[str, Any]] = None,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.ydl_opts: Dict[str, Any] = {**self._BASE_OPTS, **(ydl_opts or {})}
        self.logger.debug("YtDlpWrapper initialised with opts: %s", self.ydl_opts)

        # Validate environment early so UI 能够在启动阶段给出提示
        self._ensure_library_available()

    # ---------------------------------------------------------------------
    # Installation helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _ensure_library_available() -> None:
        """Raise :class:`YtDlpError` if *yt‑dlp* is not importable."""

        if yt_dlp is None:  # type: ignore[comparison‑overlap]
            raise YtDlpError(
                "yt-dlp library is not installed. Run 'pip install yt-dlp' or add it to requirements.txt"  # noqa: E501
            ) from _import_error  # type: ignore[arg‑type]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def is_installed(cls) -> bool:
        """Return **True** when *yt‑dlp* is importable (Python package level)."""
        return yt_dlp is not None  # type: ignore[comparison‑overlap]

    @staticmethod
    def executable_exists() -> bool:
        """Check if the *yt-dlp* CLI executable is in *PATH*."""
        return shutil.which("yt-dlp") is not None

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Return full metadata for *url* without downloading the video.

        Internally uses :class:`yt_dlp.YoutubeDL.extract_info`.
        """
        self.logger.debug("Fetching video info for URL: %s", url)
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:  # type: ignore[attr-defined]
                info_dict: Dict[str, Any] = ydl.extract_info(url, download=False)
                self.logger.debug("Extraction successful: id=%s title=%s", info_dict.get("id"), info_dict.get("title"))
                return info_dict
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.error("yt-dlp failed to extract info: %s", exc, exc_info=False)
            raise YtDlpError(str(exc)) from exc

    # ------------------------------------------------------------------
    # CLI fallback – occasionally needed for features not exposed in API
    # ------------------------------------------------------------------
    def run_cli(self, args: List[str]) -> str:
        """Execute *yt-dlp* via subprocess and return *stdout* text.

        Parameters
        ----------
        args
            List of arguments *excluding* the program name, e.g. ``["--version"]``.
        """
        if not self.executable_exists():
            raise YtDlpError("yt-dlp executable not found in PATH; cannot run CLI command.")

        cmd = ["yt-dlp", *args]
        self.logger.debug("Running yt-dlp CLI: %s", cmd)
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            self.logger.error("yt-dlp CLI failed: %s", exc.stdout)
            raise YtDlpError(exc.stdout) from exc

        self.logger.debug("yt-dlp CLI output: %s", proc.stdout[:4000])
        return proc.stdout

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    @staticmethod
    def save_json(data: Dict[str, Any], output_path: str | Path) -> None:
        """Utility helper: dump *data* to *output_path* in UTF‑8 JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf‑8") 