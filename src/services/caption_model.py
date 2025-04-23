"""Caption data model module.

This module defines the core data structures used for captions:
* `CaptionLine` - Single line of caption with timing and text
* `CaptionMetadata` - Metadata for a caption track
* `Caption` - Full caption with metadata and lines
* `CaptionError` - Base exception for caption-related errors

By separating these models into a dedicated module, we avoid circular imports
between the subtitle parser and caption service.
"""

import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

__all__ = [
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
    # New fields for enhanced caption type information
    caption_type: str = "unknown"  # "manual", "auto_generated", "translated", etc.
    has_speaker_identification: bool = False
    quality_score: Optional[float] = None  # Estimated quality of auto captions (0-1)
    provider: str = "youtube"  # Source provider of captions
    is_default: bool = False  # Whether this is the default caption track


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
                "caption_type": self.metadata.caption_type,
                "has_speaker_identification": self.metadata.has_speaker_identification,
                "quality_score": self.metadata.quality_score,
                "provider": self.metadata.provider,
                "is_default": self.metadata.is_default,
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
            caption_type=data["metadata"].get("caption_type", "unknown"),
            has_speaker_identification=data["metadata"].get("has_speaker_identification", False),
            quality_score=data["metadata"].get("quality_score"),
            provider=data["metadata"].get("provider", "youtube"),
            is_default=data["metadata"].get("is_default", False),
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