from __future__ import annotations

"""Caption extraction service for YouTube videos.

Implements *task 3.1 (Setup yt-dlp integration for caption extraction)* by providing:

* `CaptionService` - Main service for retrieving and managing captions from YouTube videos

This service uses the enhanced `YtDlpWrapper` to fetch subtitle tracks from videos
and provides additional parsing, formatting, and caching capabilities.
"""

import logging
import json
import re
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .yt_dlp_wrapper import YtDlpWrapper, YtDlpError
from .media_storage import MediaStorage
from .youtube_utils import YouTubeValidator
from .caption_model import Caption, CaptionLine, CaptionMetadata, CaptionError
from .subtitle_parser import ParserFactory, ParserError

__all__ = [
    "CaptionService",
]


class CaptionService:
    """Service for retrieving and managing captions from YouTube videos."""
    
    def __init__(
        self,
        yt_dlp_wrapper,
        cache_dir: Optional[Union[str, Path]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the caption service.
        
        Parameters
        ----------
        yt_dlp_wrapper : YtDlpWrapper
            Instance of YtDlpWrapper for YouTube operations
        cache_dir : Optional[Union[str, Path]], default None
            Directory for caching captions
        logger : Optional[logging.Logger], default None
            Logger for recording issues
        """
        self.yt_dlp = yt_dlp_wrapper
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.logger = logger or logging.getLogger(__name__)
        
        # Create cache directory if it doesn't exist
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_available_captions(self, url: str) -> Dict[str, List[Dict]]:
        """Get available captions for a YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
            
        Returns
        -------
        Dict[str, List[Dict]]
            Dictionary with keys 'automatic' and 'manual', each containing a list of
            available caption tracks with their metadata
            
        Raises
        ------
        CaptionError
            If there's an error retrieving captions information
        """
        try:
            return self.yt_dlp.list_subtitles(url)
        except Exception as exc:
            raise CaptionError(f"Failed to get available captions: {exc}")
    
    def get_caption(
        self,
        url: str,
        language: str = "en",
        source: str = "manual",
        formats: List[str] = None,
        use_cache: bool = True
    ) -> Caption:
        """Get caption for a YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str, default 'en'
            Language code (e.g., 'en', 'fr')
        source : str, default 'manual'
            Source of caption ('manual' or 'automatic')
        formats : List[str], default None
            List of preferred formats in order (e.g., ['vtt', 'srt'])
            If None, defaults to ['vtt', 'srt', 'json']
        use_cache : bool, default True
            Whether to use cached captions if available
            
        Returns
        -------
        Caption
            Caption object with metadata and lines
            
        Raises
        ------
        CaptionError
            If there's an error retrieving or parsing captions
        """
        formats = formats or ["vtt", "srt", "json"]
        video_id = self._extract_video_id(url)
        
        # Try to get from cache first
        if use_cache and self.cache_dir:
            cached_caption = self._get_cached_caption(video_id, language, source)
            if cached_caption:
                self.logger.info(f"Using cached caption for video {video_id}, language {language}")
                return cached_caption
        
        # Prepare metadata
        metadata = CaptionMetadata(
            video_id=video_id,
            language_code=language,
            language_name="Unknown",  # Will be updated after download
            is_auto_generated=source == "automatic",
            format="auto",  # Will be updated after download
            source_url=url
        )
        
        # Create a temporary directory for download
        with self._create_temp_dir() as temp_dir:
            temp_file = temp_dir / f"subtitle_{video_id}_{language}"
            
            try:
                # Download subtitle in preferred format
                subtitle_info = self.yt_dlp.download_subtitle(
                    url=url,
                    output_path=str(temp_file),
                    language=language,
                    formats=formats,
                    source=source
                )
                
                if not subtitle_info:
                    raise CaptionError(f"No subtitles available for video {video_id} in language {language}")
                
                # Update metadata
                metadata.format = subtitle_info.get("ext", "auto")
                metadata.language_name = subtitle_info.get("language_name", metadata.language_name)
                
                # Parse subtitle file
                downloaded_file = f"{temp_file}.{metadata.format}"
                if not os.path.exists(downloaded_file):
                    raise CaptionError(f"Downloaded subtitle file not found: {downloaded_file}")
                
                with open(downloaded_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                caption = self._parse_subtitle_file(content, metadata)
                
                # Cache the caption
                if self.cache_dir:
                    self._cache_caption(caption)
                
                return caption
                
            except Exception as exc:
                raise CaptionError(f"Failed to get caption: {exc}")
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL or return ID if already provided.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
            
        Returns
        -------
        str
            YouTube video ID
            
        Raises
        ------
        CaptionError
            If video ID cannot be extracted
        """
        # Check if it's already a video ID (11 chars)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        # Try to extract from YouTube URL
        patterns = [
            r'youtu\.be/([a-zA-Z0-9_-]{11})',                # youtu.be/{video_id}
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',    # youtube.com/watch?v={video_id}
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'        # youtube.com/embed/{video_id}
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise CaptionError(f"Could not extract video ID from URL: {url}")
    
    def _parse_subtitle_file(self, content: str, metadata: CaptionMetadata) -> Caption:
        """Parse subtitle file content into a Caption object.
        
        Parameters
        ----------
        content : str
            Subtitle file content
        metadata : CaptionMetadata
            Metadata for the caption
            
        Returns
        -------
        Caption
            Parsed caption
            
        Raises
        ------
        CaptionError
            If there's an error parsing the subtitle file
        """
        try:
            # Use ParserFactory to detect format and parse content
            format_name = metadata.format if metadata.format != "auto" else None
            caption = ParserFactory.parse_subtitle(
                content=content,
                metadata=metadata,
                format_name=format_name,
                logger=self.logger
            )
            
            self.logger.info(f"Successfully parsed {metadata.format} subtitle with {len(caption.lines)} lines")
            return caption
            
        except ParserError as exc:
            raise CaptionError(f"Failed to parse subtitle file: {exc}")
        except Exception as exc:
            raise CaptionError(f"Unexpected error parsing subtitle file: {exc}")
    
    def _get_cached_caption(self, video_id: str, language: str, source: str) -> Optional[Caption]:
        """Get caption from cache if available.
        
        Parameters
        ----------
        video_id : str
            YouTube video ID
        language : str
            Language code
        source : str
            Source of caption ('manual' or 'automatic')
            
        Returns
        -------
        Optional[Caption]
            Caption from cache, or None if not available
        """
        if not self.cache_dir:
            return None
        
        cache_file = self.cache_dir / f"{video_id}_{language}_{source}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return Caption.from_dict(data)
        except Exception as exc:
            self.logger.warning(f"Failed to load cached caption: {exc}")
            return None
    
    def _cache_caption(self, caption: Caption) -> bool:
        """Cache a caption for future use.
        
        Parameters
        ----------
        caption : Caption
            Caption to cache
            
        Returns
        -------
        bool
            True if caching was successful, False otherwise
        """
        if not self.cache_dir:
            return False
        
        metadata = caption.metadata
        # Determine source based on is_auto_generated flag
        source = "automatic" if metadata.is_auto_generated else "manual"
        cache_file = self.cache_dir / f"{metadata.video_id}_{metadata.language_code}_{source}.json"
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(caption.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Caption cached to {cache_file}")
            return True
        except Exception as exc:
            self.logger.warning(f"Failed to cache caption: {exc}")
            return False
    
    def get_caption_preview(self, caption: Caption, max_lines: int = 5) -> str:
        """Get a preview of the caption text.
        
        Parameters
        ----------
        caption : Caption
            Caption to preview
        max_lines : int, default 5
            Maximum number of caption lines to include
            
        Returns
        -------
        str
            Preview of the caption text
        """
        if not caption.lines:
            return "No caption lines available"
        
        preview_lines = caption.lines[:max_lines]
        preview_text = "\n".join(f"[{line.start_time:.1f}-{line.end_time:.1f}] {line.text}" 
                                for line in preview_lines)
        
        if len(caption.lines) > max_lines:
            preview_text += f"\n... and {len(caption.lines) - max_lines} more lines"
        
        return preview_text
    
    def _create_temp_dir(self):
        """Create a temporary directory for subtitle downloads.
        Returns a context manager that will clean up the directory when done.
        """
        import tempfile
        import shutil
        
        temp_dir = Path(tempfile.mkdtemp(prefix="youtube_subtitles_"))
        
        class TempDirContext:
            def __init__(self, path):
                self.path = path
            
            def __enter__(self):
                return self.path
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                shutil.rmtree(self.path, ignore_errors=True)
        
        return TempDirContext(temp_dir) 