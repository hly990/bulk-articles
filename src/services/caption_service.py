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
from .caption_cache import CaptionCache, CacheConfig

__all__ = [
    "CaptionService",
]


class CaptionService:
    """Service for retrieving and managing captions from YouTube videos."""
    
    def __init__(
        self,
        yt_dlp_wrapper,
        cache_dir: Optional[Union[str, Path]] = None,
        cache_config: Optional[CacheConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the caption service.
        
        Parameters
        ----------
        yt_dlp_wrapper : YtDlpWrapper
            Instance of YtDlpWrapper for YouTube operations
        cache_dir : Optional[Union[str, Path]], default None
            Directory for caching captions
        cache_config : Optional[CacheConfig], default None
            Configuration for the caption cache
        logger : Optional[logging.Logger], default None
            Logger for recording issues
        """
        self.yt_dlp = yt_dlp_wrapper
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up caching
        if cache_dir:
            self.cache = CaptionCache(
                cache_dir=Path(cache_dir),
                config=cache_config,
                logger=self.logger
            )
            self.cache_enabled = True
        else:
            # Create disabled cache if no cache directory provided
            self.cache = None
            self.cache_enabled = False
    
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
        use_cache: bool = True,
        cache_kwargs: Optional[Dict[str, Any]] = None
    ) -> Caption:
        """Get caption for a YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        language : str, default 'en'
            Language code (e.g., 'en', 'fr')
        source : str, default 'manual'
            Source of caption ('manual', 'automatic', 'translated', or 'any')
        formats : List[str], default None
            List of preferred formats in order (e.g., ['vtt', 'srt'])
            If None, defaults to ['vtt', 'srt', 'json']
        use_cache : bool, default True
            Whether to use cached captions if available
        cache_kwargs : Optional[Dict[str, Any]], default None
            Additional parameters for the cache key
            
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
        cache_kwargs = cache_kwargs or {}
        
        # Try to get from cache first
        if use_cache and self.cache_enabled and self.cache:
            cached_caption = self.cache.get(
                video_id=video_id,
                language=language,
                source=source,
                **cache_kwargs
            )
            
            if cached_caption:
                self.logger.info(f"Using cached caption for video {video_id}, language {language}")
                return cached_caption
        
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
                
                # Prepare metadata using the enhanced information from download_subtitle
                metadata = CaptionMetadata(
                    video_id=video_id,
                    language_code=language,
                    language_name=subtitle_info.get('language_name', 'Unknown'),
                    is_auto_generated=subtitle_info.get('is_auto_generated', False),
                    format=subtitle_info.get('ext', 'auto'),
                    source_url=url,
                    caption_type=subtitle_info.get('caption_type', source),
                    has_speaker_identification=subtitle_info.get('has_speaker_id', False),
                    provider='youtube',
                    is_default=subtitle_info.get('is_default', False)
                )
                
                # Parse subtitle file
                downloaded_file = subtitle_info.get('filepath')
                if not os.path.exists(downloaded_file):
                    raise CaptionError(f"Downloaded subtitle file not found: {downloaded_file}")
                
                with open(downloaded_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                caption = self._parse_subtitle_file(content, metadata)
                
                # Cache the caption
                if self.cache_enabled and self.cache and use_cache:
                    self.cache.store(
                        caption=caption,
                        source=source,
                        **cache_kwargs
                    )
                
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
        # Check if it's already a video ID
        if not url.startswith(('http://', 'https://', 'www.')):
            return url
        
        # Try to extract from YouTube URL
        patterns = [
            r'youtu\.be/([^&?/]+)',                # youtu.be/{video_id}
            r'youtube\.com/watch\?v=([^&?/]+)',    # youtube.com/watch?v={video_id}
            r'youtube\.com/embed/([^&?/]+)'        # youtube.com/embed/{video_id}
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
    
    def clear_cache(self) -> bool:
        """Clear the caption cache.
        
        Returns
        -------
        bool
            True if clearing was successful, False otherwise
        """
        if self.cache_enabled and self.cache:
            return self.cache.clear()
        return False
    
    def invalidate_cache(
        self,
        video_id: str,
        language: str = None,
        source: str = None
    ) -> int:
        """Invalidate cache entries for a specific video.
        
        Parameters
        ----------
        video_id : str
            YouTube video ID
        language : str, optional
            Language code (if None, all languages are invalidated)
        source : str, optional
            Caption source (if None, all sources are invalidated)
            
        Returns
        -------
        int
            Number of cache entries invalidated
        """
        if self.cache_enabled and self.cache:
            return self.cache.invalidate(
                video_id=video_id,
                language=language,
                source=source
            )
        return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns
        -------
        Dict[str, Any]
            Dictionary of cache statistics or empty dict if caching is disabled
        """
        if self.cache_enabled and self.cache:
            return self.cache.get_stats()
        return {}
    
    def get_caption_preview(self, caption: Caption, max_lines: int = 5, 
                          format_type: str = 'default', include_metadata: bool = False) -> str:
        """Get a preview of the caption text.
        
        Parameters
        ----------
        caption : Caption
            Caption to preview
        max_lines : int, default 5
            Maximum number of caption lines to include
        format_type : str, default 'default'
            Format type for the preview:
            - 'default': Simple text with timestamps
            - 'plain': Text only, no timestamps
            - 'srt': SRT format
            - 'html': HTML formatted preview
        include_metadata : bool, default False
            Whether to include caption metadata in the preview
            
        Returns
        -------
        str
            Preview of the caption text
        """
        if not caption.lines:
            return "No caption lines available"
        
        preview_lines = caption.lines[:max_lines]
        
        # Generate formatted preview based on the format_type
        if format_type == 'plain':
            preview_text = "\n".join(line.text for line in preview_lines)
        elif format_type == 'srt':
            preview_text = "\n".join(line.to_srt() for line in preview_lines)
        elif format_type == 'html':
            preview_lines_html = []
            for line in preview_lines:
                timestamp = f"[{line.start_time:.1f}s-{line.end_time:.1f}s]"
                html_line = f'<div class="caption-line"><span class="timestamp">{timestamp}</span> <span class="text">{line.text}</span></div>'
                preview_lines_html.append(html_line)
            preview_text = "\n".join(preview_lines_html)
        else:  # default
            preview_text = "\n".join(f"[{line.start_time:.1f}-{line.end_time:.1f}] {line.text}" 
                                    for line in preview_lines)
        
        # Add ellipsis if there are more lines
        if len(caption.lines) > max_lines:
            if format_type == 'html':
                preview_text += f'\n<div class="more-info">... and {len(caption.lines) - max_lines} more lines</div>'
            else:
                preview_text += f"\n... and {len(caption.lines) - max_lines} more lines"
        
        # Add metadata if requested
        if include_metadata:
            metadata = caption.metadata
            if format_type == 'html':
                metadata_html = (
                    f'<div class="caption-metadata">\n'
                    f'  <div>Language: {metadata.language_name} ({metadata.language_code})</div>\n'
                    f'  <div>Type: {metadata.caption_type}</div>\n'
                    f'  <div>Auto-generated: {"Yes" if metadata.is_auto_generated else "No"}</div>\n'
                    f'  <div>Has speaker identification: {"Yes" if metadata.has_speaker_identification else "No"}</div>\n'
                    f'</div>\n'
                )
                preview_text = metadata_html + preview_text
            else:
                metadata_text = (
                    f"Language: {metadata.language_name} ({metadata.language_code})\n"
                    f"Type: {metadata.caption_type}\n"
                    f"Auto-generated: {'Yes' if metadata.is_auto_generated else 'No'}\n"
                    f"Has speaker identification: {'Yes' if metadata.has_speaker_identification else 'No'}\n\n"
                )
                preview_text = metadata_text + preview_text
        
        return preview_text
        
    def get_caption_previews_multilingual(self, url: str, languages: List[str] = None, 
                                        max_lines: int = 3, format_type: str = 'default',
                                        use_cache: bool = True) -> Dict[str, str]:
        """Get caption previews in multiple languages for a YouTube video.
        
        Parameters
        ----------
        url : str
            YouTube video URL or ID
        languages : List[str], default None
            List of language codes to get previews for.
            If None, will get previews for all available languages.
        max_lines : int, default 3
            Maximum number of caption lines to include in each preview
        format_type : str, default 'default'
            Format type for the preview ('default', 'plain', 'srt', 'html')
        use_cache : bool, default True
            Whether to use cached captions if available
            
        Returns
        -------
        Dict[str, str]
            Dictionary mapping language codes to caption previews
        """
        try:
            # Get video ID for cache key
            video_id = self._extract_video_id(url)
            
            # Get available captions
            available_captions = self.get_available_captions(url)
            
            # If no languages specified, use all available
            if not languages:
                languages = []
                for section in ['manual', 'automatic']:
                    for caption in available_captions.get(section, []):
                        lang = caption.get('language')
                        if lang and lang not in languages:
                            languages.append(lang)
            
            # Get previews for each language
            previews = {}
            for language in languages:
                try:
                    # Try to get manual first, then automatic
                    try:
                        caption = self.get_caption(
                            url=url,
                            language=language,
                            source="manual",
                            use_cache=use_cache
                        )
                    except CaptionError:
                        # Fall back to automatic if manual not available
                        caption = self.get_caption(
                            url=url,
                            language=language,
                            source="automatic",
                            use_cache=use_cache
                        )
                    
                    # Generate preview
                    preview = self.get_caption_preview(
                        caption=caption,
                        max_lines=max_lines,
                        format_type=format_type,
                        include_metadata=True
                    )
                    
                    previews[language] = preview
                    
                except Exception as e:
                    self.logger.warning(f"Error getting preview for language {language}: {e}")
                    previews[language] = f"Error: {str(e)}"
            
            return previews
            
        except Exception as exc:
            raise CaptionError(f"Failed to get multilingual previews: {exc}")
            
    def get_caption_preview_cached(self, video_id: str, language: str, source: str = 'manual',
                                max_lines: int = 5, format_type: str = 'default', 
                                include_metadata: bool = False) -> Optional[str]:
        """Get a preview of a cached caption without redownloading.
        
        Parameters
        ----------
        video_id : str
            YouTube video ID
        language : str
            Language code
        source : str, default 'manual'
            Caption source ('manual', 'automatic', etc.)
        max_lines : int, default 5
            Maximum number of caption lines to include
        format_type : str, default 'default'
            Format type for the preview
        include_metadata : bool, default False
            Whether to include caption metadata in the preview
            
        Returns
        -------
        Optional[str]
            Preview of the caption text, or None if not in cache
        """
        if not self.cache_enabled or not self.cache:
            return None
            
        # Try to get caption from cache
        cached_caption = self.cache.get(
            video_id=video_id,
            language=language,
            source=source
        )
        
        if not cached_caption:
            return None
            
        # Generate preview
        return self.get_caption_preview(
            caption=cached_caption,
            max_lines=max_lines,
            format_type=format_type,
            include_metadata=include_metadata
        )
    
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
    
    def filter_captions_by_type(self, captions_info: Dict[str, List[Dict]], caption_type: str) -> List[Dict]:
        """Filter available captions by type.
        
        Parameters
        ----------
        captions_info : Dict[str, List[Dict]]
            Dictionary with available captions as returned by get_available_captions
        caption_type : str
            Type of caption to filter ('manual', 'auto_generated', 'translated', etc.)
            
        Returns
        -------
        List[Dict]
            List of captions matching the specified type
        """
        result = []
        
        # Check in both manual and automatic sections
        for section in ['manual', 'automatic']:
            for caption in captions_info.get(section, []):
                if caption.get('caption_type') == caption_type:
                    result.append(caption)
        
        return result
    
    def has_speaker_identification(self, captions_info: Dict[str, List[Dict]]) -> List[Dict]:
        """Get captions that have speaker identification.
        
        Parameters
        ----------
        captions_info : Dict[str, List[Dict]]
            Dictionary with available captions as returned by get_available_captions
            
        Returns
        -------
        List[Dict]
            List of captions that have speaker identification
        """
        result = []
        
        # Check in both manual and automatic sections
        for section in ['manual', 'automatic']:
            for caption in captions_info.get(section, []):
                if caption.get('has_speaker_id', False):
                    result.append(caption)
        
        return result
    
    def get_default_caption(self, captions_info: Dict[str, List[Dict]]) -> Optional[Dict]:
        """Get the default caption track if available.
        
        Parameters
        ----------
        captions_info : Dict[str, List[Dict]]
            Dictionary with available captions as returned by get_available_captions
            
        Returns
        -------
        Optional[Dict]
            Default caption info or None if no default is set
        """
        # Check first in manual captions (preferred)
        for caption in captions_info.get('manual', []):
            if caption.get('is_default', False):
                return caption
        
        # Then check automatic captions
        for caption in captions_info.get('automatic', []):
            if caption.get('is_default', False):
                return caption
        
        return None 