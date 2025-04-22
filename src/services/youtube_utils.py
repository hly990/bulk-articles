from __future__ import annotations

"""Utilities for YouTube URL handling & metadata extraction.

Completes *task 2.3* (URL validation & metadata extraction) by providing:

* ``YouTubeValidator`` – Regex‑based URL validation & video‑ID parsing
* ``MetadataExtractor`` – Wrapper around :class:`YtDlpWrapper` with
  transparent disk‑cache via :class:`MediaStorage`
"""

from dataclasses import dataclass
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError
from .media_storage import MediaStorage

__all__ = [
    "YouTubeValidator",
    "VideoMetadata",
    "MetadataExtractor",
]


class YouTubeValidator:
    """Utility class for recognising and parsing YouTube URLs."""

    # Patterns cover: regular watch URL, youtu.be short, embed, shorts
    _VIDEO_ID_RE = r"([A-Za-z0-9_-]{11})"  # 11‑char video id

    _WATCH_PATTERN = re.compile(rf"https?://(?:www\.)?youtube\.com/watch\?v={_VIDEO_ID_RE}")
    _SHORT_PATTERN = re.compile(rf"https?://youtu\.be/{_VIDEO_ID_RE}")
    _EMBED_PATTERN = re.compile(rf"https?://(?:www\.)?youtube\.com/embed/{_VIDEO_ID_RE}")
    _SHORTS_PATTERN = re.compile(rf"https?://(?:www\.)?youtube\.com/shorts/{_VIDEO_ID_RE}")

    @classmethod
    def is_valid(cls, url: str) -> bool:
        """Return **True** if *url* looks like a valid YouTube *video* URL."""
        return any(p.match(url) for p in cls._patterns())

    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """Return the 11‑character video ID from *url* or **None** if not found."""
        for pattern in cls._patterns():
            m = pattern.match(url)
            if m:
                return m.group(1)
        # Fallback: parse query param 'v'
        if "v=" in url:
            # naive parse to keep deps light
            from urllib.parse import urlparse, parse_qs

            qs = parse_qs(urlparse(url).query)
            vid = qs.get("v", [None])[0]
            if vid and len(vid) == 11:
                return vid
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @classmethod
    def _patterns(cls):
        return (
            cls._WATCH_PATTERN,
            cls._SHORT_PATTERN,
            cls._EMBED_PATTERN,
            cls._SHORTS_PATTERN,
        )


@dataclass
class VideoMetadata:  # pylint: disable=too-many-instance-attributes
    """Slim‑structured subset of yt‑dlp info dict used by app."""

    video_id: str
    title: str
    duration: int  # seconds
    thumbnail: str
    formats: list[dict[str, Any]]

    @classmethod
    def from_info_dict(cls, info: Dict[str, Any]) -> "VideoMetadata":
        return cls(
            video_id=info.get("id", ""),
            title=info.get("title", ""),
            duration=int(info.get("duration") or 0),
            thumbnail=info.get("thumbnail", ""),
            formats=info.get("formats", []),
        )

    # For JSON serialisation
    def to_json(self) -> Dict[str, Any]:  # noqa: D401 – not using property
        return {
            "video_id": self.video_id,
            "title": self.title,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "formats": self.formats,
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "VideoMetadata":
        return cls(**data)  # type: ignore[arg-type]


@dataclass
class VideoFormat:
    """Representation of a single yt‑dlp format entry, simplified for UI."""

    format_id: str
    ext: str
    resolution: str  # e.g. "1920x1080" or "audio only"
    filesize: Optional[int]  # bytes, may be None
    tbr: Optional[float]  # total bitrate (kbits/s)
    vcodec: str
    acodec: str

    @classmethod
    def from_raw(cls, fmt: Dict[str, Any]) -> "VideoFormat":
        return cls(
            format_id=fmt.get("format_id", ""),
            ext=fmt.get("ext", ""),
            resolution=fmt.get("resolution") or fmt.get("format_note") or "audio only",
            filesize=fmt.get("filesize") or fmt.get("filesize_approx"),
            tbr=fmt.get("tbr"),
            vcodec=fmt.get("vcodec", ""),
            acodec=fmt.get("acodec", ""),
        )

    def human_size(self) -> str:
        if not self.filesize:
            return "?"
        units = ["B", "KB", "MB", "GB"]
        size = float(self.filesize)
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    def __str__(self) -> str:  # pragma: no cover
        size = self.human_size()
        return f"{self.format_id} {self.ext} {self.resolution} {size}bps={self.tbr or '?'}k"


class MetadataExtractor:
    """Fetch & cache video metadata using :class:`YtDlpWrapper`."""

    def __init__(
        self,
        storage: Optional[MediaStorage] = None,
        wrapper: Optional[YtDlpWrapper] = None,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.wrapper = wrapper or YtDlpWrapper()
        self.storage = storage or MediaStorage()
        self.logger = logger or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_metadata(self, url: str, *, use_cache: bool = True) -> VideoMetadata:
        """Return :class:`VideoMetadata` for *url*, optionally using disk cache."""
        if not YouTubeValidator.is_valid(url):
            raise ValueError("Invalid YouTube URL")

        video_id = YouTubeValidator.extract_video_id(url)
        if not video_id:
            raise ValueError("Unable to extract video_id from URL")

        cache_path = self.storage.get_metadata_path(video_id)

        if use_cache and cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                self.logger.debug("Loaded metadata from cache: %s", cache_path)
                return VideoMetadata.from_json(data)
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Failed to read cached metadata – will re‑fetch. %s", exc)

        # Fetch via yt‑dlp
        try:
            info = self.wrapper.get_video_info(url)
        except YtDlpError:
            raise  # re‑raise for caller
        except Exception as exc:  # pragma: no cover
            raise YtDlpError(str(exc)) from exc

        # Some playlist URLs return list – take first entry
        if "entries" in info:
            info = info["entries"][0]

        meta = VideoMetadata.from_info_dict(info)

        # Save to cache
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(meta.to_json(), ensure_ascii=False), encoding="utf-8")
            self.logger.debug("Saved metadata cache to %s", cache_path)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Failed to save metadata cache: %s", exc)

        return meta

    # ------------------------------------------------------------------
    # Formats API
    # ------------------------------------------------------------------

    def list_formats(self, url: str, *, use_cache: bool = True) -> list[VideoFormat]:
        """Return a list of available :class:`VideoFormat` objects for *url*."""
        meta = self.get_metadata(url, use_cache=use_cache)
        raw_formats = meta.formats or []
        parsed = [VideoFormat.from_raw(f) for f in raw_formats if f.get("vcodec") != "none" or f.get("acodec") != "none"]
        # sort by resolution or bitrate descending
        parsed.sort(key=lambda f: (f.tbr or 0), reverse=True)
        return parsed 