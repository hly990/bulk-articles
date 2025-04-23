from __future__ import annotations

"""Subtitle parser module for different caption formats.

Implements *task 3.3 (Implement caption parsing functionality)* by providing:

* `CaptionParser` - Interface for all subtitle parsers
* `SrtParser` - Parser for SubRip Text (SRT) format
* `VttParser` - Parser for WebVTT format
* `ParserFactory` - Factory to create appropriate parser based on format

This module provides a flexible system for parsing different subtitle formats
into a common Caption data structure.
"""

import re
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Type, ClassVar

from .caption_model import Caption, CaptionLine, CaptionMetadata, CaptionError

__all__ = [
    "CaptionParser",
    "SrtParser",
    "VttParser",
    "ParserFactory",
    "ParserError",
]


class ParserError(CaptionError):
    """Exception raised for errors during subtitle parsing."""


class CaptionParser(ABC):
    """Abstract base class for subtitle parsers."""
    
    @abstractmethod
    def parse(
        self, 
        content: str, 
        metadata: CaptionMetadata
    ) -> Caption:
        """Parse subtitle content into a Caption object.
        
        Parameters
        ----------
        content : str
            The raw subtitle content to parse
        metadata : CaptionMetadata
            Metadata for the caption
            
        Returns
        -------
        Caption
            Parsed caption with metadata and lines
            
        Raises
        ------
        ParserError
            If there's an error during parsing
        """
        pass
    
    @classmethod
    @abstractmethod
    def detect_format(cls, content: str) -> bool:
        """Detect if content matches this parser's format.
        
        Parameters
        ----------
        content : str
            The raw subtitle content to check
            
        Returns
        -------
        bool
            True if the content is in the format handled by this parser
        """
        pass


class SrtParser(CaptionParser):
    """Parser for SubRip Text (SRT) format."""
    
    # Regular expression for parsing SRT entries
    SRT_PATTERN = re.compile(
        r'(\d+)\s*\n'                                # Index
        r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*'       # Start time
        r'(\d{2}:\d{2}:\d{2},\d{3})\s*\n'           # End time
        r'((?:.*\n)+?)'                             # Text (can be multi-line)
        r'(?:\n|$)',                                # End of entry (blank line or end of file)
        re.MULTILINE
    )
    
    # Regular expression for parsing SRT time format
    TIME_PATTERN = re.compile(
        r'(\d{2}):(\d{2}):(\d{2}),(\d{3})'
    )
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the SRT parser.
        
        Parameters
        ----------
        logger : Optional[logging.Logger]
            Logger for recording parsing issues
        """
        self.logger = logger or logging.getLogger(__name__)
    
    @classmethod
    def detect_format(cls, content: str) -> bool:
        """Detect if content is in SRT format.
        
        Parameters
        ----------
        content : str
            The raw subtitle content to check
            
        Returns
        -------
        bool
            True if the content is in SRT format
        """
        # Check for at least one match of SRT pattern
        return bool(cls.SRT_PATTERN.search(content))
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert SRT time format to seconds.
        
        Parameters
        ----------
        time_str : str
            Time in format 'HH:MM:SS,mmm'
            
        Returns
        -------
        float
            Time in seconds
        """
        match = self.TIME_PATTERN.match(time_str)
        if not match:
            raise ParserError(f"Invalid SRT time format: {time_str}")
        
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    
    def parse(
        self, 
        content: str, 
        metadata: CaptionMetadata
    ) -> Caption:
        """Parse SRT content into a Caption object.
        
        Parameters
        ----------
        content : str
            The raw SRT content to parse
        metadata : CaptionMetadata
            Metadata for the caption
            
        Returns
        -------
        Caption
            Parsed caption with metadata and lines
            
        Raises
        ------
        ParserError
            If there's an error during parsing
        """
        if not content.strip():
            raise ParserError("Empty SRT content")
        
        caption = Caption(metadata=metadata)
        matches = self.SRT_PATTERN.finditer(content)
        
        for match in matches:
            index = int(match.group(1))
            start_time_str = match.group(2)
            end_time_str = match.group(3)
            text = match.group(4).strip()
            
            try:
                start_time = self._time_to_seconds(start_time_str)
                end_time = self._time_to_seconds(end_time_str)
                
                caption.lines.append(CaptionLine(
                    index=index,
                    start_time=start_time,
                    end_time=end_time,
                    text=text
                ))
            except Exception as exc:
                self.logger.warning("Failed to parse SRT entry %d: %s", index, exc)
                continue
        
        if not caption.lines:
            raise ParserError("No valid caption lines found in SRT content")
        
        return caption


class VttParser(CaptionParser):
    """Parser for WebVTT format."""
    
    # Regular expression for parsing VTT entries
    VTT_PATTERN = re.compile(
        r'(?:(\d+)?\s*\n)?'                         # Optional index
        r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*'      # Start time
        r'(\d{2}:\d{2}:\d{2}\.\d{3}).*\n'           # End time (with optional settings)
        r'((?:.*\n)+?)'                             # Text (can be multi-line)
        r'(?:\n|$)',                                # End of entry (blank line or end of file)
        re.MULTILINE
    )
    
    # Regular expression for parsing VTT time format
    TIME_PATTERN = re.compile(
        r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})'
    )
    
    # Regular expressions for cleaning VTT text
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    VOICE_TAG_PATTERN = re.compile(r'<v\s+([^>]+)>(.*?)</v>')
    SPEAKER_PATTERN = re.compile(r'\[?([a-zA-Z]*\s*(?:speaker|SPEAKER)[\s0-9]*)\]?[:.\s]*(.*)')
    BRACKET_PATTERN = re.compile(r'\[(.*?)\](.*)')
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the VTT parser.
        
        Parameters
        ----------
        logger : Optional[logging.Logger]
            Logger for recording parsing issues
        """
        self.logger = logger or logging.getLogger(__name__)
        self._has_detected_speakers = False
    
    @classmethod
    def detect_format(cls, content: str) -> bool:
        """Detect if content is in VTT format.
        
        Parameters
        ----------
        content : str
            The raw subtitle content to check
            
        Returns
        -------
        bool
            True if the content is in VTT format
        """
        # Check for WebVTT header
        if 'WEBVTT' in content[:100]:
            return True
        
        # Check for VTT timestamp pattern
        return bool(cls.VTT_PATTERN.search(content))
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert WebVTT time format to seconds.
        
        Parameters
        ----------
        time_str : str
            Time in format 'HH:MM:SS.mmm'
            
        Returns
        -------
        float
            Time in seconds
        """
        match = self.TIME_PATTERN.match(time_str)
        if not match:
            raise ParserError(f"Invalid WebVTT time format: {time_str}")
        
        hours, minutes, seconds, milliseconds = map(int, match.groups())
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    
    def _extract_speaker(self, text: str) -> tuple[str, str]:
        """Extract speaker information from text if present.
        
        Parameters
        ----------
        text : str
            Text that may contain speaker information
            
        Returns
        -------
        tuple[str, str]
            Tuple of (speaker, cleaned_text) - speaker is empty if none found
        """
        # Check for voice tags: <v Speaker Name>Text</v>
        voice_match = self.VOICE_TAG_PATTERN.search(text)
        if voice_match:
            self._has_detected_speakers = True
            speaker = voice_match.group(1).strip()
            return speaker, voice_match.group(2).strip()
        
        # Check for format: [SPEAKER 1]: Text
        speaker_match = self.SPEAKER_PATTERN.match(text.strip())
        if speaker_match:
            self._has_detected_speakers = True
            speaker = speaker_match.group(1).strip()
            return speaker, speaker_match.group(2).strip()
            
        # Check for format: [Music] Text or [Applause] Text
        bracket_match = self.BRACKET_PATTERN.match(text.strip())
        if bracket_match:
            content = bracket_match.group(1).strip().lower()
            if content in ('music', 'applause', 'laughter', 'sound'):
                # This is a sound effect, not a speaker
                return '', text
            # This might be a speaker designation
            self._has_detected_speakers = True
            return bracket_match.group(1).strip(), bracket_match.group(2).strip()
        
        return '', text
    
    def _clean_text(self, text: str) -> str:
        """Clean WebVTT text by removing HTML tags and other format-specific elements.
        
        Parameters
        ----------
        text : str
            WebVTT text to clean
            
        Returns
        -------
        str
            Cleaned text
        """
        # Remove voice tags but preserve speaker information
        speaker_text_pairs = []
        current_text = text
        
        # Process each line for potential speaker information
        for line in text.split('\n'):
            speaker, cleaned_line = self._extract_speaker(line)
            if speaker:
                speaker_text_pairs.append((speaker, cleaned_line))
            else:
                # No speaker found, keep the line as is
                speaker_text_pairs.append(('', self.HTML_TAG_PATTERN.sub('', line)))
        
        # Reconstruct text with speaker prefixes where applicable
        result_lines = []
        for speaker, line_text in speaker_text_pairs:
            if speaker and line_text:
                result_lines.append(f"{speaker}: {line_text}")
            elif line_text:
                result_lines.append(line_text)
        
        # Remove positioning information (lines starting with align: etc.)
        filtered_lines = []
        for line in result_lines:
            if not line.strip() or ':' in line and line.split(':', 1)[0].strip().lower() in (
                'align', 'position', 'size', 'vertical', 'line', 'region'
            ):
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines).strip()
    
    def parse(
        self, 
        content: str, 
        metadata: CaptionMetadata
    ) -> Caption:
        """Parse VTT content into a Caption object.
        
        Parameters
        ----------
        content : str
            The raw VTT content to parse
        metadata : CaptionMetadata
            Metadata for the caption
            
        Returns
        -------
        Caption
            Parsed caption with metadata and lines
            
        Raises
        ------
        ParserError
            If there's an error during parsing
        """
        if not content.strip():
            raise ParserError("Empty WebVTT content")
        
        # Reset speaker detection flag
        self._has_detected_speakers = False
        
        # Skip WebVTT header
        if 'WEBVTT' in content[:100]:
            # Find the first timestamp
            first_timestamp = re.search(r'\d{2}:\d{2}:\d{2}\.\d{3}', content)
            if first_timestamp:
                start_pos = max(0, first_timestamp.start() - 10)
                content = content[start_pos:]
        
        caption = Caption(metadata=metadata)
        matches = self.VTT_PATTERN.finditer(content)
        index = 0
        
        for match in matches:
            index += 1
            start_time_str = match.group(2)
            end_time_str = match.group(3)
            text = match.group(4).strip()
            
            try:
                start_time = self._time_to_seconds(start_time_str)
                end_time = self._time_to_seconds(end_time_str)
                
                caption.lines.append(CaptionLine(
                    index=index,
                    start_time=start_time,
                    end_time=end_time,
                    text=self._clean_text(text)
                ))
            except Exception as exc:
                self.logger.warning("Failed to parse VTT entry %d: %s", index, exc)
                continue
        
        if not caption.lines:
            raise ParserError("No valid caption lines found in WebVTT content")
        
        # Update metadata with speaker identification flag
        if self._has_detected_speakers:
            metadata.has_speaker_identification = True
            
        return caption


class JsonParser(CaptionParser):
    """Parser for JSON format (YouTube API format)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the JSON parser.
        
        Parameters
        ----------
        logger : Optional[logging.Logger]
            Logger for recording parsing issues
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def parse(
        self, 
        content: str, 
        metadata: CaptionMetadata
    ) -> Caption:
        """Parse JSON content into a Caption object.
        
        Parameters
        ----------
        content : str
            The raw JSON content to parse
        metadata : CaptionMetadata
            Metadata for the caption
            
        Returns
        -------
        Caption
            Parsed caption with metadata and lines
            
        Raises
        ------
        ParserError
            If there's an error during parsing
        """
        # Create caption with provided metadata
        caption = Caption(metadata=metadata)
        
        try:
            import json
            data = json.loads(content)
            
            # YouTube API format has different structures
            # Try to detect the format and parse accordingly
            if "events" in data:
                # YouTube API format
                return self._parse_youtube_api_format(data, caption)
            elif "transcript" in data:
                # Alternative format with transcript array
                return self._parse_transcript_format(data, caption)
            else:
                # Try our own JSON format
                return self._parse_custom_json_format(data, caption)
            
        except Exception as exc:
            raise ParserError(f"Failed to parse JSON content: {exc}")
    
    def _parse_youtube_api_format(self, data: Dict, caption: Caption) -> Caption:
        """Parse YouTube API format JSON."""
        index = 1
        for event in data.get("events", []):
            if "segs" not in event:
                continue
                
            start_time = event.get("tStartMs", 0) / 1000
            end_time = start_time + (event.get("dDurationMs", 0) / 1000)
            
            # Collect text from segments
            text_parts = []
            for seg in event.get("segs", []):
                if "utf8" in seg:
                    text_parts.append(seg["utf8"])
            
            text = "".join(text_parts).strip()
            if not text:
                continue
                
            caption_line = CaptionLine(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text
            )
            
            caption.lines.append(caption_line)
            index += 1
            
        return caption
    
    def _parse_transcript_format(self, data: Dict, caption: Caption) -> Caption:
        """Parse transcript array format JSON."""
        index = 1
        for item in data.get("transcript", []):
            if "text" not in item:
                continue
                
            start_time = item.get("start", 0)
            end_time = start_time + item.get("duration", 0)
            text = item.get("text", "").strip()
            
            if not text:
                continue
                
            caption_line = CaptionLine(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text
            )
            
            caption.lines.append(caption_line)
            index += 1
            
        return caption
    
    def _parse_custom_json_format(self, data: Dict, caption: Caption) -> Caption:
        """Parse our custom JSON format."""
        # If it looks like our own Caption JSON format
        if "metadata" in data and "lines" in data:
            lines_data = data.get("lines", [])
            
            for line_data in lines_data:
                caption_line = CaptionLine(
                    index=line_data.get("index", 0),
                    start_time=line_data.get("start", 0),
                    end_time=line_data.get("end", 0),
                    text=line_data.get("text", "")
                )
                
                caption.lines.append(caption_line)
                
        return caption
    
    @staticmethod
    def detect_format(content: str) -> bool:
        """Detect if content is in JSON format.
        
        Parameters
        ----------
        content : str
            The raw subtitle content to check
            
        Returns
        -------
        bool
            True if the content is in JSON format
        """
        # Check if content is valid JSON
        try:
            import json
            content = content.strip()
            if content.startswith("{") and content.endswith("}"):
                json.loads(content)
                return True
        except (json.JSONDecodeError, ValueError):
            pass
            
        return False


class ParserFactory:
    """Factory for creating appropriate subtitle parsers based on format."""
    
    # Map of format names to parser classes
    PARSER_MAP: ClassVar[Dict[str, Type[CaptionParser]]] = {
        'srt': SrtParser,
        'vtt': VttParser,
        'json': JsonParser,
    }
    
    @classmethod
    def get_parser(cls, format_name: str) -> CaptionParser:
        """Get a parser for the specified format.
        
        Parameters
        ----------
        format_name : str
            Name of the format (e.g., 'srt', 'vtt')
            
        Returns
        -------
        CaptionParser
            Parser instance for the specified format
            
        Raises
        ------
        ParserError
            If the format is not supported
        """
        parser_class = cls.PARSER_MAP.get(format_name.lower())
        if parser_class is None:
            raise ParserError(f"Unsupported subtitle format: {format_name}")
        
        return parser_class()
    
    @classmethod
    def detect_format(cls, content: str) -> Optional[str]:
        """Detect the format of subtitle content.
        
        Parameters
        ----------
        content : str
            Subtitle content to check
            
        Returns
        -------
        Optional[str]
            Name of the detected format, or None if format could not be detected
        """
        for format_name, parser_class in cls.PARSER_MAP.items():
            if parser_class.detect_format(content):
                return format_name
        
        return None

    @classmethod
    def parse_subtitle(
        cls,
        content: str,
        metadata: CaptionMetadata,
        format_name: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> Caption:
        """Parse subtitle content into a Caption object.
        
        Parameters
        ----------
        content : str
            Subtitle content to parse
        metadata : CaptionMetadata
            Metadata for the caption
        format_name : Optional[str], default None
            Name of the format (e.g., 'srt', 'vtt'). If None, format will be auto-detected
        logger : Optional[logging.Logger], default None
            Logger for recording issues
            
        Returns
        -------
        Caption
            Parsed caption
            
        Raises
        ------
        ParserError
            If there's an error parsing the content or the format is not supported
        """
        if not content.strip():
            raise ParserError("Empty subtitle content")
        
        # Auto-detect format if not specified
        if not format_name:
            format_name = cls.detect_format(content)
            if not format_name:
                raise ParserError("Could not detect subtitle format")
            if logger:
                logger.info(f"Auto-detected subtitle format: {format_name}")
        
        # Get parser for format
        parser = cls.get_parser(format_name)
        
        # Parse content
        return parser.parse(content, metadata) 