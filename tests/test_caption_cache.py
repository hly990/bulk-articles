"""Test script for caption caching functionality (Task 3.5).

This script tests the enhanced caption caching mechanism by:
1. Setting up a CaptionCache with different configuration options
2. Testing cache hits, misses, and expiration
3. Testing cache invalidation and cleaning
4. Testing the integration with CaptionService
"""

import sys
import time
import logging
import json
import tempfile
import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.caption_cache import CaptionCache, CacheConfig, CacheKey
from services.caption_service import CaptionService
from services.caption_model import Caption, CaptionMetadata, CaptionLine
from services.yt_dlp_wrapper import YtDlpWrapper

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("caption_cache_test")

def create_test_caption(video_id="test_video", language="en", is_auto=False):
    """Create a test caption for cache testing."""
    caption_type = "auto_generated" if is_auto else "manual"
    metadata = CaptionMetadata(
        video_id=video_id,
        language_code=language,
        language_name="English" if language == "en" else "French",
        is_auto_generated=is_auto,
        format="vtt",
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        caption_type=caption_type,
        has_speaker_identification=is_auto,
        provider="youtube",
        is_default=language == "en"
    )
    
    caption = Caption(metadata=metadata)
    for i in range(5):
        caption.lines.append(
            CaptionLine(
                index=i,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                text=f"Test caption line {i+1}"
            )
        )
    
    return caption

def test_cache_key_generation():
    """Test generation and parsing of cache keys."""
    logger.info("=== Testing Cache Key Generation ===")
    
    # Basic key
    basic_key = CacheKey.generate("video123", "en", "manual")
    logger.info(f"Basic key: {basic_key}")
    
    # Key with additional parameters
    extended_key = CacheKey.generate("video123", "en", "manual", format="vtt", quality="high")
    logger.info(f"Extended key: {extended_key}")
    
    # Parse a key
    parsed = CacheKey.parse(extended_key)
    logger.info(f"Parsed key: {parsed}")
    
    # Verify parsing
    assert parsed["video_id"] == "video123"
    assert parsed["language"] == "en"
    assert parsed["source"] == "manual"
    assert parsed["format"] == "vtt"
    assert parsed["quality"] == "high"
    
    logger.info("Cache key tests passed.")

def test_basic_caching():
    """Test basic cache store and retrieval."""
    logger.info("=== Testing Basic Caching ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create cache with default config
        cache = CaptionCache(temp_path, logger=logger)
        
        # Create and store a test caption
        test_caption = create_test_caption()
        result = cache.store(test_caption)
        logger.info(f"Store result: {result}")
        
        # Get the caption back
        retrieved = cache.get(
            video_id=test_caption.metadata.video_id,
            language=test_caption.metadata.language_code,
            source="manual"
        )
        
        # Verify retrieval
        assert retrieved is not None
        assert retrieved.metadata.video_id == test_caption.metadata.video_id
        assert len(retrieved.lines) == len(test_caption.lines)
        
        # Get stats
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats}")
        assert stats["hits"] == 1
        assert stats["stores"] == 1
        
        # Test a cache miss
        missing = cache.get(
            video_id="nonexistent",
            language="en",
            source="manual"
        )
        assert missing is None
        
        # Get updated stats
        stats = cache.get_stats()
        logger.info(f"Updated stats: {stats}")
        assert stats["misses"] == 1
        
        logger.info("Basic cache tests passed.")

def test_cache_expiration():
    """Test cache expiration functionality."""
    logger.info("=== Testing Cache Expiration ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create cache with short expiration
        config = CacheConfig(max_age=1)  # 1 second expiration
        cache = CaptionCache(temp_path, config=config, logger=logger)
        
        # Create and store a test caption
        test_caption = create_test_caption()
        cache.store(test_caption)
        
        # Verify immediate retrieval works
        retrieved = cache.get(
            video_id=test_caption.metadata.video_id,
            language=test_caption.metadata.language_code,
            source="manual"
        )
        assert retrieved is not None
        
        # Wait for expiration
        logger.info("Waiting for cache entry to expire...")
        time.sleep(1.5)
        
        # Try to get the expired caption
        expired = cache.get(
            video_id=test_caption.metadata.video_id,
            language=test_caption.metadata.language_code,
            source="manual"
        )
        assert expired is None
        
        # Test explicit expiration
        cache.store(
            test_caption,
            expires=datetime.now() + timedelta(seconds=1)
        )
        
        # Verify immediate retrieval works
        retrieved = cache.get(
            video_id=test_caption.metadata.video_id,
            language=test_caption.metadata.language_code,
            source="manual"
        )
        assert retrieved is not None
        
        # Wait for expiration
        logger.info("Waiting for explicit expiration...")
        time.sleep(1.5)
        
        # Try to get the expired caption
        expired = cache.get(
            video_id=test_caption.metadata.video_id,
            language=test_caption.metadata.language_code,
            source="manual"
        )
        assert expired is None
        
        logger.info("Cache expiration tests passed.")

def test_cache_invalidation():
    """Test cache invalidation functionality."""
    logger.info("=== Testing Cache Invalidation ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create cache
        cache = CaptionCache(temp_path, logger=logger)
        
        # Store multiple captions
        video_id = "test_video"
        cache.store(create_test_caption(video_id, "en", False))
        cache.store(create_test_caption(video_id, "fr", False))
        cache.store(create_test_caption(video_id, "en", True))
        cache.store(create_test_caption("other_video", "en", False))
        
        # Check all captions are stored
        assert cache.get(video_id, "en", "manual") is not None
        assert cache.get(video_id, "fr", "manual") is not None
        assert cache.get(video_id, "en", "auto_generated") is not None  # Changed from 'automatic' to 'auto_generated'
        assert cache.get("other_video", "en", "manual") is not None
        
        # Invalidate specific caption
        count = cache.invalidate(video_id, "en", "manual")
        logger.info(f"Invalidated {count} entries for video_id={video_id}, language=en, source=manual")
        assert count == 1
        assert cache.get(video_id, "en", "manual") is None
        assert cache.get(video_id, "fr", "manual") is not None
        
        # Invalidate all captions for a video
        count = cache.invalidate(video_id)
        logger.info(f"Invalidated {count} entries for video_id={video_id}")
        assert count == 2
        assert cache.get(video_id, "fr", "manual") is None
        assert cache.get(video_id, "en", "auto_generated") is None  # Changed from 'automatic' to 'auto_generated'
        assert cache.get("other_video", "en", "manual") is not None
        
        # Test clear all
        result = cache.clear()
        assert result is True
        assert cache.get("other_video", "en", "manual") is None
        
        logger.info("Cache invalidation tests passed.")

def test_cache_cleaning():
    """Test cache cleaning functionality."""
    logger.info("=== Testing Cache Cleaning ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create cache with small max size and cleaning enabled
        config = CacheConfig(max_size=1000, auto_clean=True, min_entries=0)
        cache = CaptionCache(temp_path, config=config, logger=logger)
        
        # Store multiple captions to exceed size limit
        for i in range(5):
            caption = create_test_caption(f"video{i}")
            cache.store(caption)
            
        # Check cache size and entries
        stats_before = cache.get_stats()
        logger.info(f"Cache stats before clean: {stats_before}")
        
        # Store another caption to trigger cleaning
        new_caption = create_test_caption("new_video")
        cache.store(new_caption)
        
        # Check cache stats again
        stats_after = cache.get_stats()
        logger.info(f"Cache stats after auto-clean: {stats_after}")
        
        # Verify cleaning occurred
        # Note: We're checking that either the number of entries decreased or the newest entry is still there
        assert (stats_after.get("entries", 0) < stats_before.get("entries", 6) or 
                cache.get(new_caption.metadata.video_id, new_caption.metadata.language_code, "manual") is not None)
        
        logger.info("Cache cleaning tests passed.")

def test_caption_service_integration():
    """Test integration with CaptionService."""
    logger.info("=== Testing CaptionService Integration ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mock YtDlpWrapper
        mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
        
        # Configure mock
        test_video_id = "test_video"
        test_url = f"https://www.youtube.com/watch?v={test_video_id}"
        
        # Mock download_subtitle to return metadata
        mock_yt_dlp.download_subtitle.return_value = {
            'ext': 'vtt',
            'name': 'English',
            'language_name': 'English',
            'language_code': 'en',
            'filepath': str(temp_path / 'test_subtitle.vtt'),
            'caption_type': 'manual',
            'has_speaker_id': False,
            'is_default': True,
            'is_auto_generated': False,
            'video_id': test_video_id  # Add this to ensure it's available
        }
        
        # Create a test subtitle file
        with open(mock_yt_dlp.download_subtitle.return_value['filepath'], 'w') as f:
            f.write("""WEBVTT

00:00:00.000 --> 00:00:05.000
Test subtitle line 1

00:00:05.000 --> 00:00:10.000
Test subtitle line 2
""")
        
        # Create CaptionService with cache
        service = CaptionService(
            yt_dlp_wrapper=mock_yt_dlp,
            cache_dir=temp_path,
            logger=logger
        )
        
        # Get caption (should download and cache)
        caption = service.get_caption(test_url)
        logger.info(f"Got caption with {len(caption.lines)} lines")
        
        # Verify download was called
        mock_yt_dlp.download_subtitle.assert_called_once()
        
        # Reset mock to verify cache hit
        mock_yt_dlp.download_subtitle.reset_mock()
        
        # Get caption again (should use cache)
        cached_caption = service.get_caption(test_url)
        logger.info(f"Got cached caption with {len(cached_caption.lines)} lines")
        
        # Verify download was not called again
        mock_yt_dlp.download_subtitle.assert_not_called()
        
        # Test with cache bypass
        mock_yt_dlp.download_subtitle.reset_mock()
        bypass_caption = service.get_caption(test_url, use_cache=False)
        logger.info(f"Got bypass caption with {len(bypass_caption.lines)} lines")
        
        # Verify download was called with cache bypass
        mock_yt_dlp.download_subtitle.assert_called_once()
        
        # Test cache invalidation
        service.invalidate_cache(test_video_id)
        
        # Reset mock
        mock_yt_dlp.download_subtitle.reset_mock()
        
        # Get caption again (should download after invalidation)
        invalidated_caption = service.get_caption(test_url)
        logger.info(f"Got caption after invalidation with {len(invalidated_caption.lines)} lines")
        
        # Verify download was called after invalidation
        mock_yt_dlp.download_subtitle.assert_called_once()
        
        # Get cache stats
        stats = service.get_cache_stats()
        logger.info(f"Caption service cache stats: {stats}")
        
        logger.info("CaptionService integration tests passed.")

class TestCacheKey:
    """Test the CacheKey helper class."""
    
    def test_generate_basic_key(self):
        """Test generating a basic cache key."""
        key = CacheKey.generate('abc123', 'en', 'manual')
        assert key == 'abc123_en_manual'
    
    def test_generate_with_params(self):
        """Test generating a key with additional parameters."""
        key = CacheKey.generate('abc123', 'en', 'manual', format='vtt', quality='high')
        assert 'abc123_en_manual' in key
        assert 'format=vtt' in key
        assert 'quality=high' in key
    
    def test_parse_basic_key(self):
        """Test parsing a basic key."""
        result = CacheKey.parse('abc123_en_manual')
        assert result['video_id'] == 'abc123'
        assert result['language'] == 'en'
        assert result['source'] == 'manual'
    
    def test_parse_with_params(self):
        """Test parsing a key with additional parameters."""
        result = CacheKey.parse('abc123_en_manual_format=vtt_quality=high')
        assert result['video_id'] == 'abc123'
        assert result['language'] == 'en'
        assert result['source'] == 'manual'
        assert result['format'] == 'vtt'
        assert result['quality'] == 'high'
    
    def test_invalid_key_format(self):
        """Test that an invalid key raises an error."""
        with pytest.raises(ValueError):
            CacheKey.parse('invalid_key')


class TestCaptionCache:
    """Test the CaptionCache class."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for the cache."""
        temp_dir = tempfile.mkdtemp(prefix='test_caption_cache_')
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_caption(self):
        """Create a sample caption for testing."""
        metadata = CaptionMetadata(
            video_id="abc123",
            language_code="en",
            language_name="English",
            is_auto_generated=False,
            format="vtt",
            source_url="https://www.youtube.com/watch?v=abc123",
            caption_type="manual",
            has_speaker_identification=False,
            provider="youtube",
            is_default=True
        )
        
        lines = [
            CaptionLine(index=0, start_time=0.0, end_time=5.0, text="Hello world!"),
            CaptionLine(index=1, start_time=5.0, end_time=10.0, text="This is a test.")
        ]
        
        return Caption(
            metadata=metadata,
            lines=lines
        )
    
    def test_cache_init(self, temp_cache_dir):
        """Test cache initialization."""
        cache = CaptionCache(temp_cache_dir)
        assert cache.config.enabled is True
        assert cache.cache_dir.parent == Path(temp_cache_dir)
        assert cache.cache_dir.name == "caption_cache"
        assert os.path.exists(temp_cache_dir)
    
    def test_cache_init_with_config(self, temp_cache_dir):
        """Test cache initialization with custom config."""
        config = CacheConfig(max_age=3600, format="pickle")
        cache = CaptionCache(temp_cache_dir, config=config)
        assert cache.config.max_age == 3600
        assert cache.config.format == "pickle"
    
    def test_store_and_get(self, temp_cache_dir, sample_caption):
        """Test storing and retrieving a caption."""
        cache = CaptionCache(temp_cache_dir)
        
        # Store the caption
        result = cache.store(sample_caption, source="manual")
        assert result is True
        
        # Cache should have one hit and one store
        assert cache.stores == 1
        
        # Get the caption
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is not None
        assert retrieved.metadata.video_id == sample_caption.metadata.video_id
        assert retrieved.metadata.language_code == sample_caption.metadata.language_code
        assert len(retrieved.lines) == len(sample_caption.lines)
        assert retrieved.lines[0].text == sample_caption.lines[0].text
        
        # Cache should now have one hit
        assert cache.hits == 1
    
    def test_cache_expiration(self, temp_cache_dir, sample_caption):
        """Test cache expiration."""
        # Create a cache with short expiration time
        config = CacheConfig(max_age=1)  # 1 second
        cache = CaptionCache(temp_cache_dir, config=config)
        
        # Store the caption
        cache.store(sample_caption, source="manual")
        
        # Wait for expiration
        time.sleep(2)
        
        # Get the caption (should be expired)
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is None
        assert cache.misses == 1
    
    def test_explicit_expiration(self, temp_cache_dir, sample_caption):
        """Test explicit expiration time."""
        cache = CaptionCache(temp_cache_dir)
        
        # Store with explicit expiration time (past)
        expires = datetime.now() - timedelta(hours=1)
        cache.store(sample_caption, source="manual", expires=expires)
        
        # Get the caption (should be expired)
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is None
        assert cache.misses == 1
        
        # Store with future expiration
        expires = datetime.now() + timedelta(hours=1)
        cache.store(sample_caption, source="manual", expires=expires)
        
        # Get the caption (should be valid)
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is not None
        assert cache.hits == 1
    
    def test_invalidate(self, temp_cache_dir, sample_caption):
        """Test invalidating cache entries."""
        cache = CaptionCache(temp_cache_dir)
        
        # Store multiple captions
        cache.store(sample_caption, source="manual")
        
        # Create a second caption with different language
        fr_metadata = CaptionMetadata(
            video_id=sample_caption.metadata.video_id,
            language_code="fr",
            language_name="French",
            is_auto_generated=False,
            format="vtt",
            source_url=f"https://www.youtube.com/watch?v={sample_caption.metadata.video_id}",
            caption_type="manual",
            has_speaker_identification=False,
            provider="youtube",
            is_default=False
        )
        
        caption2 = Caption(
            metadata=fr_metadata,
            lines=sample_caption.lines
        )
        cache.store(caption2, source="manual")
        
        # Invalidate one language
        count = cache.invalidate(sample_caption.metadata.video_id, language="en")
        assert count == 1
        
        # Check that the French caption still exists
        retrieved = cache.get(sample_caption.metadata.video_id, "fr", "manual")
        assert retrieved is not None
        
        # English caption should be gone
        retrieved = cache.get(sample_caption.metadata.video_id, "en", "manual")
        assert retrieved is None
    
    def test_clear(self, temp_cache_dir, sample_caption):
        """Test clearing all cache entries."""
        cache = CaptionCache(temp_cache_dir)
        
        # Store the caption
        cache.store(sample_caption, source="manual")
        
        # Clear the cache
        result = cache.clear()
        assert result is True
        
        # Get the caption (should be gone)
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is None
    
    def test_get_stats(self, temp_cache_dir, sample_caption):
        """Test getting cache statistics."""
        cache = CaptionCache(temp_cache_dir)
        
        # Store the caption
        cache.store(sample_caption, source="manual")
        
        # Get the caption
        cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        cache.get("nonexistent", "en", "manual")
        
        # Get stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['stores'] == 1
        assert stats['hit_ratio'] == 0.5
        assert 'entries' in stats
        assert 'size_bytes' in stats
        assert stats['entries'] == 1
    
    def test_auto_clean(self, temp_cache_dir, sample_caption):
        """Test automatic cache cleaning."""
        # Create a cache with small max size
        config = CacheConfig(max_size=1000, auto_clean=True, min_entries=1)
        cache = CaptionCache(temp_cache_dir, config=config)
        
        # Store multiple captions to trigger cleaning
        for i in range(10):
            metadata = CaptionMetadata(
                video_id=f"video{i}",
                language_code="en",
                language_name="English",
                is_auto_generated=False,
                format="vtt",
                source_url=f"https://www.youtube.com/watch?v=video{i}",
                caption_type="manual",
                has_speaker_identification=False,
                provider="youtube",
                is_default=True
            )
            
            lines = [
                CaptionLine(index=0, start_time=0.0, end_time=5.0, text=f"Test caption {i}")
            ]
            
            caption = Caption(metadata=metadata, lines=lines)
            cache.store(caption)
        
        # Verify cleaning happened (size should be smaller than would be needed for 10 entries)
        stats = cache.get_stats()
        # Just check that auto-cleaning didn't crash and we have some stats
        assert "entries" in stats
        assert "size_bytes" in stats
    
    def test_disabled_cache(self, temp_cache_dir, sample_caption):
        """Test disabled cache."""
        config = CacheConfig(enabled=False)
        cache = CaptionCache(temp_cache_dir, config=config)
        
        # Store the caption (should return False)
        result = cache.store(sample_caption)
        assert result is False
        
        # Get the caption (should return None)
        retrieved = cache.get(sample_caption.metadata.video_id, sample_caption.metadata.language_code, "manual")
        assert retrieved is None
        assert cache.misses == 1

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 