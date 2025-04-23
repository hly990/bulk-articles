# Subtitle Parser Documentation

## Overview

This document describes the implementation of Task 3.3: "Implement caption parsing functionality" for the YT Article Craft project. The subtitle parser system provides a flexible and extensible way to parse subtitles from various formats into a common data structure.

## Components

### Data Model (`caption_model.py`)

Core data structures for working with captions:

- `CaptionError`: Base exception class for caption-related errors
- `CaptionLine`: Represents a single line of caption with timing and text
- `CaptionMetadata`: Stores metadata about a caption track
- `Caption`: Main container for a complete caption with metadata and lines

### Parser System (`subtitle_parser.py`)

A flexible parsing system with:

- `CaptionParser`: Abstract base class defining the parser interface
- `SrtParser`: Parser for SubRip Text (SRT) format
- `VttParser`: Parser for WebVTT format
- `JsonParser`: Parser for JSON-based formats
- `ParserFactory`: Factory class to create the appropriate parser based on format

### Integration with Caption Service

The `CaptionService` in `caption_service.py` uses the parser system to:

1. Download subtitles from YouTube videos using `YtDlpWrapper`
2. Parse the subtitle content into `Caption` objects
3. Manage caching of parsed captions
4. Provide formatted output (SRT, plain text)

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| SRT | .srt | SubRip Text format with timing and text |
| WebVTT | .vtt | Web Video Text Tracks format with advanced styling |
| JSON | .json | JSON-based formats (including YouTube API format) |

## Usage Examples

### Basic usage with ParserFactory

```python
from services import ParserFactory, CaptionMetadata

# Prepare metadata
metadata = CaptionMetadata(
    language_code="en",
    language_name="English",
    is_auto_generated=False,
    format="srt",
    source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ"
)

# Parse subtitle content
with open("subtitle.srt", "r") as f:
    content = f.read()

# Auto-detect format and parse
caption = ParserFactory.parse_subtitle(
    content=content,
    metadata=metadata
)

# Work with parsed caption
print(f"Found {len(caption.lines)} caption lines")
print(caption.to_plain_text())  # Get just the text
print(caption.to_srt())  # Convert to SRT format
```

### Using CaptionService

```python
from services import CaptionService, YtDlpWrapper

# Initialize service
yt_dlp = YtDlpWrapper()
service = CaptionService(
    yt_dlp_wrapper=yt_dlp,
    cache_dir="./cache"
)

# Get available captions
video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
available = service.get_available_captions(video_url)
print(available)

# Download and parse caption
caption = service.get_caption(
    url=video_url,
    language="en",
    formats=["vtt", "srt"]
)

# Get a preview
print(service.get_caption_preview(caption))
```

## Testing

Two test scripts are provided to verify the functionality:

1. `tests/test_subtitle_parser.py`: Tests the parsing of SRT and VTT formats
2. `tests/test_caption_service.py`: Tests the integration with CaptionService

Run the tests with:

```bash
python tests/test_subtitle_parser.py
python tests/test_caption_service.py
```

## Extending the System

To add support for a new subtitle format:

1. Create a new parser class extending `CaptionParser`
2. Implement the `parse()` and `detect_format()` methods
3. Add the new parser to `ParserFactory.PARSER_MAP` 

## Overview

This document describes the implementation of Task 3.3: "Implement caption parsing functionality" for the YT Article Craft project. The subtitle parser system provides a flexible and extensible way to parse subtitles from various formats into a common data structure.

## Components

### Data Model (`caption_model.py`)

Core data structures for working with captions:

- `CaptionError`: Base exception class for caption-related errors
- `CaptionLine`: Represents a single line of caption with timing and text
- `CaptionMetadata`: Stores metadata about a caption track
- `Caption`: Main container for a complete caption with metadata and lines

### Parser System (`subtitle_parser.py`)

A flexible parsing system with:

- `CaptionParser`: Abstract base class defining the parser interface
- `SrtParser`: Parser for SubRip Text (SRT) format
- `VttParser`: Parser for WebVTT format
- `JsonParser`: Parser for JSON-based formats
- `ParserFactory`: Factory class to create the appropriate parser based on format

### Integration with Caption Service

The `CaptionService` in `caption_service.py` uses the parser system to:

1. Download subtitles from YouTube videos using `YtDlpWrapper`
2. Parse the subtitle content into `Caption` objects
3. Manage caching of parsed captions
4. Provide formatted output (SRT, plain text)

## Supported Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| SRT | .srt | SubRip Text format with timing and text |
| WebVTT | .vtt | Web Video Text Tracks format with advanced styling |
| JSON | .json | JSON-based formats (including YouTube API format) |

## Usage Examples

### Basic usage with ParserFactory

```python
from services import ParserFactory, CaptionMetadata

# Prepare metadata
metadata = CaptionMetadata(
    language_code="en",
    language_name="English",
    is_auto_generated=False,
    format="srt",
    source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ"
)

# Parse subtitle content
with open("subtitle.srt", "r") as f:
    content = f.read()

# Auto-detect format and parse
caption = ParserFactory.parse_subtitle(
    content=content,
    metadata=metadata
)

# Work with parsed caption
print(f"Found {len(caption.lines)} caption lines")
print(caption.to_plain_text())  # Get just the text
print(caption.to_srt())  # Convert to SRT format
```

### Using CaptionService

```python
from services import CaptionService, YtDlpWrapper

# Initialize service
yt_dlp = YtDlpWrapper()
service = CaptionService(
    yt_dlp_wrapper=yt_dlp,
    cache_dir="./cache"
)

# Get available captions
video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
available = service.get_available_captions(video_url)
print(available)

# Download and parse caption
caption = service.get_caption(
    url=video_url,
    language="en",
    formats=["vtt", "srt"]
)

# Get a preview
print(service.get_caption_preview(caption))
```

## Testing

Two test scripts are provided to verify the functionality:

1. `tests/test_subtitle_parser.py`: Tests the parsing of SRT and VTT formats
2. `tests/test_caption_service.py`: Tests the integration with CaptionService

Run the tests with:

```bash
python tests/test_subtitle_parser.py
python tests/test_caption_service.py
```

## Extending the System

To add support for a new subtitle format:

1. Create a new parser class extending `CaptionParser`
2. Implement the `parse()` and `detect_format()` methods
3. Add the new parser to `ParserFactory.PARSER_MAP` 