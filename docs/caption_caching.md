# YouTube Caption Caching System

## Overview

The YouTube Caption Caching System provides an efficient mechanism for storing and retrieving parsed YouTube captions locally. This system optimizes application performance by reducing the need for repeated network requests and subtitle parsing operations when working with the same video captions multiple times.

## Key Components

### `CacheConfig`

Configuration class that controls cache behavior:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `True` | Toggle to enable/disable caching completely |
| `max_age` | int | 604800 (7 days) | Maximum age in seconds before entries expire |
| `max_size` | int | 104857600 (100 MB) | Maximum size of cache in bytes |
| `auto_clean` | bool | `True` | Whether to automatically remove old entries when cache exceeds `max_size` |
| `min_entries` | int | 10 | Minimum number of entries to keep when cleaning |
| `refresh_on_access` | bool | `False` | Whether to reset expiration timer when retrieving an entry |
| `format` | str | "json" | Storage format ("json" or "pickle") |

Example usage:

```python
from src.services.caption_cache import CacheConfig

# Create custom cache configuration
config = CacheConfig(
    max_age=3600 * 24,  # 1 day
    format="pickle",
    auto_clean=True
)
```

### `CacheKey`

Helper class for generating and parsing cache keys that uniquely identify caption entries:

- `generate(video_id, language, source, **kwargs)`: Creates a unique key string
- `parse(key)`: Extracts components from a key string

Keys are formatted as: `{video_id}_{language}_{source}_{param1=value1}_{param2=value2}...`

Example:

```python
from src.services.caption_cache import CacheKey

# Generate a key
key = CacheKey.generate("dQw4w9WgXcQ", "en", "manual", format="vtt")
# Result: "dQw4w9WgXcQ_en_manual_format=vtt"

# Parse a key
components = CacheKey.parse(key)
# Result: {'video_id': 'dQw4w9WgXcQ', 'language': 'en', 'source': 'manual', 'format': 'vtt'}
```

### `CaptionCache`

Main class that handles the storage and retrieval of captions:

**Constructor:**

```python
CaptionCache(cache_dir, config=None, logger=None)
```

- `cache_dir`: Directory path to store cached files
- `config`: Optional `CacheConfig` instance for custom settings
- `logger`: Optional logger instance

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get(video_id, language, source, **kwargs)` | Retrieve a caption if cached and valid |
| `store(caption, source=None, expires=None, **kwargs)` | Store a caption in the cache |
| `invalidate(video_id, language=None, source=None)` | Remove specific entries from the cache |
| `clear()` | Remove all entries from the cache |
| `get_stats()` | Get statistics about the cache (hits, misses, size, etc.) |

### `CaptionService` Integration

The `CaptionService` class integrates with the caching system automatically:

```python
from src.services.caption_service import CaptionService
from src.services.caption_cache import CacheConfig
from src.services.yt_dlp_wrapper import YtDlpWrapper

# Create a service with caching enabled
service = CaptionService(
    yt_dlp_wrapper=YtDlpWrapper(),
    cache_dir="./cache/captions",
    cache_config=CacheConfig(max_age=3600 * 24 * 3)  # 3 days
)

# Fetch a caption (automatically uses cache)
caption = service.get_caption(
    url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en",
    use_cache=True
)
```

## Key Features

### Configurable Caching

The caching system can be extensively customized by adjusting the `CacheConfig` parameters to suit specific use cases, from disabling it entirely to fine-tuning expiration times and storage formats.

### Intelligent Cache Keys

The key generation system ensures that captions are uniquely identified based on the video ID, language, source, and any additional parameters that might affect the caption content.

### Cache Control Mechanisms

The cache provides multiple ways to control cached content:

- **Time-based expiration**: Entries older than `max_age` are automatically considered invalid
- **Explicit expiration**: Setting a specific expiration datetime when storing an entry
- **Manual invalidation**: Selectively removing entries based on video ID, language, or source
- **Complete clearing**: Removing all cached entries at once

### Expiration Policies

The system supports two types of expiration:

1. **Time-based expiration** based on file modification time
2. **Explicit expiration** using a stored datetime in the cache entry

When `refresh_on_access` is enabled, accessing a cache entry updates its modification time, effectively extending its lifespan.

### Cache Size Management

To prevent the cache from growing too large:

1. The cache monitors its total size during storage operations
2. When the size exceeds `max_size`, older entries are removed first
3. At least `min_entries` are always kept, regardless of size

## Usage Examples

### Basic Usage

```python
from src.services.caption_cache import CaptionCache, CacheConfig
from src.services.caption_model import Caption

# Initialize the cache
cache = CaptionCache("./cache/captions")

# Store a caption
cache.store(caption, source="manual")

# Retrieve the caption
retrieved = cache.get(
    video_id="dQw4w9WgXcQ",
    language="en",
    source="manual"
)

if retrieved:
    print(f"Found cached caption with {len(retrieved.lines)} lines")
else:
    print("Caption not found in cache")
```

### Advanced Usage

```python
from src.services.caption_cache import CaptionCache, CacheConfig
from src.services.caption_model import Caption
from datetime import datetime, timedelta

# Custom configuration
config = CacheConfig(
    max_age=3600,  # 1 hour
    format="pickle",  # Use pickle for storage (faster serialization/deserialization)
    refresh_on_access=True  # Reset expiration timer on access
)

# Initialize the cache
cache = CaptionCache("./cache/captions", config=config)

# Store with explicit expiration
expires = datetime.now() + timedelta(hours=2)
cache.store(
    caption,
    source="manual",
    expires=expires,
    format="vtt",  # Additional key parameter
    quality="high"  # Additional key parameter
)

# Get cache statistics
stats = cache.get_stats()
print(f"Cache has {stats['entries']} entries using {stats['size_mb']:.2f} MB")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")

# Clean up old entries for a specific video
removed = cache.invalidate("dQw4w9WgXcQ", language="en")
print(f"Removed {removed} entries from cache")
```

### Cache Entry Management

```python
# Clear cache for specific video and language
cache.invalidate(video_id="dQw4w9WgXcQ", language="en")

# Clear all entries for a video
cache.invalidate(video_id="dQw4w9WgXcQ")

# Clear the entire cache
cache.clear()
```

## Testing

The caching system includes comprehensive unit tests that verify:

- Key generation and parsing
- Cache initialization and configuration
- Storage and retrieval
- Expiration mechanisms
- Invalidation and clearing
- Statistics gathering
- Automatic cleaning

Run the tests with:

```bash
pytest tests/test_caption_cache.py -v
```

## Future Enhancements

Potential future improvements to the caching system include:

1. **Compressed storage**: Reducing disk space usage by compressing cache entries
2. **Multiple cache backends**: Supporting other storage methods (Redis, SQLite, etc.)
3. **Asynchronous operations**: Non-blocking cache access for improved performance
4. **Prefetching**: Anticipating user needs by proactively caching related captions
5. **Enhanced cache analytics**: More detailed statistics and monitoring 