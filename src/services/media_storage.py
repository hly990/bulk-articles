from __future__ import annotations

"""Media cache directory management.

Implements *task 2.2 (Create local media cache directory structure)*.

Responsibilities
----------------
• Determine a root cache directory (default: ``~/.yt_article_cache``).
• Provide helpers to create/retrieve paths for downloaded videos & metadata.
• Offer utilities to check free disk space & clean cache.
"""

from pathlib import Path
import logging
import os
import shutil
import stat
import time
from typing import Optional

__all__ = [
    "MediaStorage",
]


class MediaStorageError(RuntimeError):
    """Raised when cache directory operations fail."""


class MediaStorage:  # pylint: disable=too-few-public-methods
    """Manage file‑system paths for video & metadata cache.

    Parameters
    ----------
    base_dir : str | Path | None, default *None*
        Root directory for cache.  *None* falls back to
        ``~/.yt_article_cache``.
    auto_create : bool, default *True*
        Automatically create the directory (and required sub‑dirs) on init.
    logger : logging.Logger | None
        Logger instance – defaults to module‑level logger.
    """

    DEFAULT_DIRNAME = ".yt_article_cache"
    METADATA_SUFFIX = ".json"

    def __init__(
        self,
        base_dir: str | Path | None = None,
        *,
        auto_create: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.base_path = Path(base_dir).expanduser() if base_dir else Path.home() / self.DEFAULT_DIRNAME

        if auto_create:
            self.ensure_directories()
            self.logger.debug("Cache base directory initialised at %s", self.base_path)

    # ------------------------------------------------------------------
    # Directory helpers
    # ------------------------------------------------------------------
    def ensure_directories(self) -> None:
        """Create *base_path* and sub‑directories if they don't exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as exc:  # pragma: no cover
            raise MediaStorageError(f"Cannot create cache directory: {self.base_path}") from exc

    # ------------------------------------------------------------------
    # Path retrieval
    # ------------------------------------------------------------------
    def get_video_path(self, video_id: str, *, fmt: str = "mp4") -> Path:
        """Return absolute path where *video_id* file (format *fmt*) should be stored."""
        self._validate_video_id(video_id)
        filename = f"{video_id}.{fmt}"
        return self.base_path / "videos" / filename

    def get_metadata_path(self, video_id: str) -> Path:
        """Return absolute path to metadata JSON for *video_id*."""
        self._validate_video_id(video_id)
        filename = f"{video_id}{self.METADATA_SUFFIX}"
        return self.base_path / "metadata" / filename

    # ------------------------------------------------------------------
    # File‑system utility
    # ------------------------------------------------------------------
    def disk_free_bytes(self) -> int:
        """Return free disk bytes on the partition containing *base_path*."""
        statv = os.statvfs(str(self.base_path))
        return statv.f_bavail * statv.f_frsize

    def clean_cache(self, *, max_age_days: int = 30) -> None:
        """Remove files older than *max_age_days* in cache directories."""
        cutoff_ts = time.time() - max_age_days * 86_400
        removed = 0
        for path in self.base_path.rglob("*"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff_ts:
                    path.unlink()
                    removed += 1
            except (OSError, PermissionError):  # pragma: no cover
                self.logger.warning("Failed to delete cache file: %s", path)
        if removed:
            self.logger.info("Cleaned %d old cache files (>%d days)", removed, max_age_days)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_video_id(video_id: str) -> None:  # pragma: no cover
        if not video_id or any(c in video_id for c in " /\\:\"\'\n\t"):
            raise ValueError("Invalid video_id for cache file naming")

    # ------------------------------------------------------------------
    # Human‑friendly info
    # ------------------------------------------------------------------
    def describe(self) -> str:
        """Return a human‑readable summary of cache location & usage."""
        total, used, free = shutil.disk_usage(self.base_path)
        return (
            f"Media cache directory: {self.base_path}\n"
            f"Free space: {free / (1024 ** 3):.1f} GiB / {total / (1024 ** 3):.1f} GiB"
        ) 