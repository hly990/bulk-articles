# Caption Preview Functionality

## Overview

The Caption Preview functionality allows for efficient display and inspection of YouTube video captions in multiple formats and languages. This feature is particularly useful for quickly verifying caption content and quality without needing to load the full caption data.

## Key Features

### Multiple Format Options

The system supports different preview formats for various use cases:

| Format | Description | Use Case |
|--------|-------------|----------|
| `default` | Text with timestamps | Quick inspection of timing and content |
| `plain` | Text only without timestamps | Clean text for content review |
| `srt` | Standard SRT format | Compatibility with external tools |
| `html` | HTML-formatted with CSS classes | Web display integration |

### Multilingual Support

The system can generate previews for multiple languages simultaneously, allowing for easy comparison between different language versions of the same caption.

### Metadata Display

Caption metadata can be included in previews, showing details such as:
- Language name and code
- Caption type (manual, auto-generated, translated)
- Auto-generation status
- Speaker identification presence
- Default status

### Cache Integration

Previews can be generated directly from cached captions without needing to redownload from YouTube, significantly improving performance.

## API Reference

### Basic Preview Generation

```python
from services.caption_service import CaptionService
from services.yt_dlp_wrapper import YtDlpWrapper

yt_dlp = YtDlpWrapper()
service = CaptionService(yt_dlp_wrapper=yt_dlp)

# Get a caption
caption = service.get_caption(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Generate a basic preview (default format)
preview = service.get_caption_preview(
    caption=caption,
    max_lines=5  # Show only first 5 lines
)
print(preview)
```

Example output:
```
[0.0-5.0] We're no strangers to love
[5.0-10.0] You know the rules and so do I
[10.0-15.0] A full commitment's what I'm thinking of
[15.0-20.0] You wouldn't get this from any other guy
[20.0-25.0] I just wanna tell you how I'm feeling
... and 20 more lines
```

### Formatted Previews

```python
# Plain text preview
plain_preview = service.get_caption_preview(
    caption=caption,
    max_lines=3,
    format_type='plain'
)
print(plain_preview)

# SRT format preview
srt_preview = service.get_caption_preview(
    caption=caption,
    max_lines=2,
    format_type='srt'
)
print(srt_preview)

# HTML format preview
html_preview = service.get_caption_preview(
    caption=caption,
    max_lines=1,
    format_type='html'
)
print(html_preview)
```

### Including Metadata

```python
# Preview with metadata
preview_with_meta = service.get_caption_preview(
    caption=caption,
    max_lines=3,
    include_metadata=True
)
print(preview_with_meta)
```

Example output:
```
Language: English (en)
Type: manual
Auto-generated: No
Has speaker identification: No

[0.0-5.0] We're no strangers to love
[5.0-10.0] You know the rules and so do I
[10.0-15.0] A full commitment's what I'm thinking of
... and 22 more lines
```

### Multilingual Previews

```python
# Get previews in multiple languages
multilingual_previews = service.get_caption_previews_multilingual(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    languages=["en", "es", "fr"],  # English, Spanish, French
    max_lines=2,
    format_type='plain'
)

# Print each language preview
for language, preview in multilingual_previews.items():
    print(f"\n=== {language} ===")
    print(preview)
```

### From Cache

```python
# Get preview from cache without downloading
preview = service.get_caption_preview_cached(
    video_id="dQw4w9WgXcQ",
    language="en",
    max_lines=3
)

if preview:
    print("Cached preview:")
    print(preview)
else:
    print("Caption not in cache")
```

## HTML Integration

When using the `html` format type, the preview includes CSS classes for styling:

```html
<div class="caption-metadata">
  <div>Language: English (en)</div>
  <div>Type: manual</div>
  <div>Auto-generated: No</div>
  <div>Has speaker identification: No</div>
</div>

<div class="caption-line">
  <span class="timestamp">[0.0s-5.0s]</span> 
  <span class="text">We're no strangers to love</span>
</div>

<div class="more-info">... and 24 more lines</div>
```

This allows for easy styling with CSS:

```css
.caption-line {
  margin-bottom: 10px;
  line-height: 1.4;
}

.timestamp {
  color: #666;
  font-size: 0.9em;
}

.caption-metadata {
  background: #f5f5f5;
  padding: 10px;
  margin-bottom: 15px;
  border-left: 3px solid #0077cc;
}

.more-info {
  font-style: italic;
  color: #888;
  margin-top: 10px;
}
```

## Performance Considerations

- For large caption files, always specify a reasonable `max_lines` value to avoid processing the entire file
- Use `get_caption_preview_cached` when possible to avoid network requests
- For multiple previews, use `get_caption_previews_multilingual` which optimizes caching and retrieval
- HTML formatting adds minimal overhead but produces larger output strings

## Future Extensions

The preview system can be extended in several ways:

1. Custom timestamp formatting options
2. Search highlighting in preview text
3. Speaker-aware formatting for auto-generated captions
4. Thumbnail integration for keyframes at caption points
5. Pagination support for viewing different sections of long captions 