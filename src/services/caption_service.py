from __future__ import annotations

"""Caption extraction service for YouTube videos.

Implements *task 3.1 (Setup yt-dlp integration for caption extraction)* by providing:

* `CaptionService` - Main service for retrieving and managing captions from YouTube videos
* `Caption` - Data structure for caption content and metadata

This service uses the enhanced `YtDlpWrapper` to fetch subtitle tracks from videos
and provides additional parsing, formatting, and caching capabilities.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError
from .media_storage import MediaStorage
from .youtube_utils import YouTubeValidator

__all__ = [
    "CaptionService",
    "Caption",
    "CaptionLine",
    "CaptionMetadata",
    "CaptionError",
]


class CaptionError(RuntimeError):
    """Base exception for caption-related errors."""


@dataclass
class CaptionLine:
    """Represents a single line of caption with start/end times and text."""
    
    index: int
    start_time: float  # seconds
    end_time: float  # seconds
    text: str
    
    def format_time(self, time_in_seconds: float) -> str:
        """Convert time in seconds to SRT format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=time_in_seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int(td.microseconds / 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def to_srt(self) -> str:
        """Convert caption line to SRT format."""
        return (
            f"{self.index}\n"
            f"{self.format_time(self.start_time)} --> {self.format_time(self.end_time)}\n"
            f"{self.text}\n"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "start": self.start_time,
            "end": self.end_time,
            "text": self.text
        }


@dataclass
class CaptionMetadata:
    """Metadata for a caption track."""
    
    language_code: str
    language_name: str
    is_auto_generated: bool
    format: str
    source_url: str
    video_id: str


@dataclass
class Caption:
    """Represents a full caption track with metadata and content."""
    
    metadata: CaptionMetadata
    lines: List[CaptionLine] = field(default_factory=list)
    
    def to_srt(self) -> str:
        """Convert all caption lines to SRT format."""
        return "\n".join(line.to_srt() for line in self.lines)
    
    def to_plain_text(self) -> str:
        """Extract only text content from captions, joined with newlines."""
        return "\n".join(line.text for line in self.lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metadata": {
                "language_code": self.metadata.language_code,
                "language_name": self.metadata.language_name,
                "is_auto_generated": self.metadata.is_auto_generated,
                "format": self.metadata.format,
                "source_url": self.metadata.source_url,
                "video_id": self.metadata.video_id,
            },
            "lines": [line.to_dict() for line in self.lines]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Caption":
        """Create Caption instance from dictionary."""
        metadata = CaptionMetadata(
            language_code=data["metadata"]["language_code"],
            language_name=data["metadata"]["language_name"],
            is_auto_generated=data["metadata"]["is_auto_generated"],
            format=data["metadata"]["format"],
            source_url=data["metadata"]["source_url"],
            video_id=data["metadata"]["video_id"],
        )
        
        lines = [
            CaptionLine(
                index=line["index"],
                start_time=line["start"],
                end_time=line["end"],
                text=line["text"]
            )
            for line in data["lines"]
        ]
        
        return cls(metadata=metadata, lines=lines)


class CaptionService:
    """Service for retrieving and managing captions from YouTube videos."""
    
    def __init__(
        self,
        yt_wrapper: Optional[YtDlpWrapper] = None,
        storage: Optional[MediaStorage] = None,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.wrapper = yt_wrapper or YtDlpWrapper()
        self.storage = storage or MediaStorage()
        
        # Ensure captions directory exists
        self.captions_dir = self.storage.base_path / "captions"
        self.captions_dir.mkdir(parents=True, exist_ok=True)
    
    def get_available_captions(self, url: str) -> Dict[str, Dict[str, Any]]:
        """Return a dictionary of available captions for a YouTube video.
        
        Parameters
        ----------
        url : str
            URL of the YouTube video
            
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary mapping language codes to caption information
            
        Raises
        ------
        CaptionError
            If the URL is invalid or captions cannot be retrieved
        """
        if not YouTubeValidator.is_valid(url):
            raise CaptionError(f"Invalid YouTube URL: {url}")
        
        try:
            return self.wrapper.list_available_subtitles(url)
        except YtDlpError as exc:
            raise CaptionError(f"Failed to get available captions: {exc}") from exc
    
    def get_caption(
        self, 
        url: str, 
        lang_code: str = "en", 
        *,
        allow_auto: bool = True,
        use_cache: bool = True,
        subtitle_format: str = "srt"
    ) -> Caption:
        """Retrieve and parse caption for a YouTube video.
        
        Parameters
        ----------
        url : str
            URL of the YouTube video
        lang_code : str, default 'en'
            Language code of the caption to retrieve
        allow_auto : bool, default True
            Whether to allow auto-generated captions if manual ones aren't available
        use_cache : bool, default True
            Whether to use cached captions if available
        subtitle_format : str, default 'srt'
            Format of the subtitle file to retrieve ('srt', 'vtt', 'json')
            
        Returns
        -------
        Caption
            Parsed caption with metadata and content
            
        Raises
        ------
        CaptionError
            If captions cannot be retrieved or parsed
        """
        video_id = YouTubeValidator.extract_video_id(url)
        if not video_id:
            raise CaptionError(f"Could not extract video ID from URL: {url}")
        
        # Check if cached version exists
        if use_cache:
            cached_caption = self._get_cached_caption(video_id, lang_code, allow_auto)
            if cached_caption:
                self.logger.debug("Retrieved caption from cache for video %s, language %s", 
                                  video_id, lang_code)
                return cached_caption
        
        # Get available captions
        available_captions = self.get_available_captions(url)
        
        # Check if requested language is available
        if lang_code not in available_captions:
            available_langs = ", ".join(available_captions.keys())
            raise CaptionError(
                f"Caption in language '{lang_code}' not available for video. "
                f"Available languages: {available_langs}"
            )
        
        caption_info = available_captions[lang_code]
        
        # Check if caption is auto-generated and allow_auto is False
        if caption_info.get("is_auto", False) and not allow_auto:
            raise CaptionError(
                f"Only auto-generated captions available for language '{lang_code}', "
                f"but allow_auto=False"
            )
        
        # Download the caption
        try:
            # Create a file path for the downloaded caption
            output_path = self.captions_dir / f"{video_id}_{lang_code}.{subtitle_format}"
            
            # Download the caption
            subtitle_path = self.wrapper.download_subtitle(
                url=url,
                lang_code=lang_code,
                output_path=output_path,
                auto_generated=caption_info.get("is_auto", False),
                format=subtitle_format
            )
            
            # Parse the caption
            caption = self._parse_subtitle_file(
                subtitle_path, 
                video_id=video_id,
                url=url,
                lang_code=lang_code,
                is_auto=caption_info.get("is_auto", False),
                format=subtitle_format
            )
            
            # Cache the caption
            self._cache_caption(caption)
            
            return caption
        
        except (YtDlpError, IOError) as exc:
            raise CaptionError(f"Failed to download or parse caption: {exc}") from exc
    
    def _parse_subtitle_file(
        self, 
        file_path: Path, 
        *,
        video_id: str,
        url: str,
        lang_code: str,
        is_auto: bool,
        format: str
    ) -> Caption:
        """Parse a subtitle file into a Caption object."""
        if format.lower() == "srt":
            return self._parse_srt_file(
                file_path, 
                video_id=video_id,
                url=url,
                lang_code=lang_code,
                is_auto=is_auto
            )
        elif format.lower() == "vtt":
            return self._parse_vtt_file(
                file_path, 
                video_id=video_id,
                url=url,
                lang_code=lang_code,
                is_auto=is_auto
            )
        else:
            raise CaptionError(f"Unsupported subtitle format: {format}")
    
    def _parse_srt_file(
        self, 
        file_path: Path, 
        *,
        video_id: str,
        url: str,
        lang_code: str,
        is_auto: bool
    ) -> Caption:
        """Parse an SRT file into a Caption object."""
        # Create metadata
        metadata = CaptionMetadata(
            language_code=lang_code,
            language_name=self.wrapper._get_language_name(lang_code),
            is_auto_generated=is_auto,
            format="srt",
            source_url=url,
            video_id=video_id
        )
        
        # Create caption
        caption = Caption(metadata=metadata)
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Split into caption blocks (separated by blank lines)
            blocks = re.split(r"\n\s*\n", content.strip())
            
            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) < 3:
                    continue  # Skip invalid blocks
                
                try:
                    # Parse index
                    index = int(lines[0])
                    
                    # Parse time codes
                    time_line = lines[1]
                    time_parts = time_line.split(" --> ")
                    if len(time_parts) != 2:
                        continue  # Skip invalid time format
                    
                    start_time = self._parse_srt_time(time_parts[0])
                    end_time = self._parse_srt_time(time_parts[1])
                    
                    # Join the remaining lines as the text
                    text = "\n".join(lines[2:])
                    
                    # Create caption line
                    caption_line = CaptionLine(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text
                    )
                    
                    caption.lines.append(caption_line)
                    
                except (ValueError, IndexError) as exc:
                    self.logger.warning("Failed to parse caption block: %s - %s", block, exc)
                    continue
            
            return caption
            
        except Exception as exc:
            raise CaptionError(f"Failed to parse SRT file: {exc}") from exc
    
    def _parse_vtt_file(
        self, 
        file_path: Path, 
        *,
        video_id: str,
        url: str,
        lang_code: str,
        is_auto: bool
    ) -> Caption:
        """Parse a VTT file into a Caption object."""
        # Create metadata
        metadata = CaptionMetadata(
            language_code=lang_code,
            language_name=self.wrapper._get_language_name(lang_code),
            is_auto_generated=is_auto,
            format="vtt",
            source_url=url,
            video_id=video_id
        )
        
        # Create caption
        caption = Caption(metadata=metadata)
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Skip WebVTT header
            if content.startswith("WEBVTT"):
                content = re.sub(r"^WEBVTT.*?(?:\r\n|\r|\n){2}", "", content, flags=re.DOTALL)
            
            # Split into caption blocks (separated by blank lines)
            blocks = re.split(r"\n\s*\n", content.strip())
            
            index = 1
            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) < 2:
                    continue  # Skip invalid blocks
                
                try:
                    # Find line with time codes (format: 00:00:00.000 --> 00:00:05.000)
                    time_line_index = -1
                    for i, line in enumerate(lines):
                        if " --> " in line:
                            time_line_index = i
                            break
                    
                    if time_line_index == -1:
                        continue  # No time line found
                    
                    # Parse time codes
                    time_line = lines[time_line_index]
                    time_parts = time_line.split(" --> ")
                    if len(time_parts) != 2:
                        continue  # Skip invalid time format
                    
                    start_time = self._parse_vtt_time(time_parts[0])
                    end_time = self._parse_vtt_time(time_parts[1])
                    
                    # Join the remaining lines as the text
                    text = "\n".join(lines[time_line_index + 1:])
                    
                    # Create caption line
                    caption_line = CaptionLine(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=text
                    )
                    
                    caption.lines.append(caption_line)
                    index += 1
                    
                except (ValueError, IndexError) as exc:
                    self.logger.warning("Failed to parse VTT block: %s - %s", block, exc)
                    continue
            
            return caption
            
        except Exception as exc:
            raise CaptionError(f"Failed to parse VTT file: {exc}") from exc
    
    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT time format (HH:MM:SS,mmm) to seconds."""
        hours, minutes, seconds = time_str.replace(",", ".").split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    
    def _parse_vtt_time(self, time_str: str) -> float:
        """Parse VTT time format (HH:MM:SS.mmm) to seconds."""
        # VTT can have different formats: 00:00.000 or 00:00:00.000
        parts = time_str.strip().split(":")
        
        if len(parts) == 3:  # HH:MM:SS.mmm
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        elif len(parts) == 2:  # MM:SS.mmm
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid VTT time format: {time_str}")
    
    def _get_cached_caption(
        self, 
        video_id: str, 
        lang_code: str, 
        allow_auto: bool
    ) -> Optional[Caption]:
        """Retrieve a cached caption if available."""
        # Get path to cached caption JSON
        cache_path = self.captions_dir / f"{video_id}_{lang_code}_caption.json"
        
        if not cache_path.exists():
            return None
        
        try:
            import json
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            caption = Caption.from_dict(data)
            
            # Check if auto-generated caption is allowed
            if caption.metadata.is_auto_generated and not allow_auto:
                return None
                
            return caption
        except Exception as exc:
            self.logger.warning("Failed to load cached caption: %s", exc)
            return None
    
    def _cache_caption(self, caption: Caption) -> None:
        """Cache a caption for future use."""
        video_id = caption.metadata.video_id
        lang_code = caption.metadata.language_code
        
        # Get path to cached caption JSON
        cache_path = self.captions_dir / f"{video_id}_{lang_code}_caption.json"
        
        try:
            import json
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(caption.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as exc:
            self.logger.warning("Failed to cache caption: %s", exc)
    
    def get_caption_preview(
        self, 
        url: str, 
        lang_code: str = "en", 
        *,
        allow_auto: bool = True,
        max_lines: int = 5
    ) -> str:
        """Get a preview of the caption for a YouTube video.
        
        Parameters
        ----------
        url : str
            URL of the YouTube video
        lang_code : str, default 'en'
            Language code of the caption to retrieve
        allow_auto : bool, default True
            Whether to allow auto-generated captions if manual ones aren't available
        max_lines : int, default 5
            Maximum number of lines to include in the preview
            
        Returns
        -------
        str
            Preview of the caption text
        """
        try:
            caption = self.get_caption(url, lang_code, allow_auto=allow_auto)
            lines = caption.lines[:max_lines]
            
            preview_text = "\n".join(line.text for line in lines)
            
            if len(caption.lines) > max_lines:
                preview_text += "\n..."
                
            return preview_text
        except CaptionError as exc:
            return f"No preview available: {exc}" 