import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.services.caption_service import (
    CaptionService, Caption, CaptionLine, CaptionMetadata, CaptionError
)
from src.services.yt_dlp_wrapper import YtDlpWrapper, YtDlpError

@pytest.fixture
def mock_yt_wrapper():
    """Mock YtDlpWrapper."""
    return MagicMock(spec=YtDlpWrapper)

@pytest.fixture
def mock_storage():
    """Mock MediaStorage."""
    storage = MagicMock()
    storage.base_path = Path("/tmp")
    return storage

@pytest.fixture
def caption_service(mock_yt_wrapper, mock_storage):
    """Create a CaptionService with mocked dependencies."""
    service = CaptionService(yt_wrapper=mock_yt_wrapper, storage=mock_storage)
    # Mock the captions directory
    service.captions_dir = Path("/tmp/captions")
    return service

@pytest.fixture
def sample_subtitle_info():
    """Sample subtitle information."""
    return {
        "en": {
            "is_auto": False,
            "name": "English",
            "format": "srt",
            "url": "https://example.com/subtitle.en.srt"
        },
        "fr": {
            "is_auto": False,
            "name": "French",
            "format": "srt",
            "url": "https://example.com/subtitle.fr.srt"
        },
        "es": {
            "is_auto": True,
            "name": "Spanish",
            "format": "srt",
            "url": "https://example.com/subtitle.es.srt"
        }
    }

class TestCaptionService:
    """Tests for CaptionService."""
    
    def test_init(self, caption_service):
        """Test initialization."""
        assert caption_service.wrapper is not None
        assert caption_service.storage is not None
        assert caption_service.captions_dir == Path("/tmp/captions")
    
    def test_get_available_captions(self, caption_service, mock_yt_wrapper, sample_subtitle_info):
        """Test getting available captions."""
        # Setup
        mock_yt_wrapper.list_available_subtitles.return_value = sample_subtitle_info
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Exercise
        captions = caption_service.get_available_captions(url)
        
        # Verify
        assert captions == sample_subtitle_info
        mock_yt_wrapper.list_available_subtitles.assert_called_once_with(url)
    
    def test_get_available_captions_invalid_url(self, caption_service):
        """Test getting available captions with invalid URL."""
        # Setup
        url = "not-a-youtube-url"
        
        # Exercise and Verify
        with pytest.raises(CaptionError, match=r"Invalid YouTube URL"):
            caption_service.get_available_captions(url)
    
    def test_get_available_captions_yt_dlp_error(self, caption_service, mock_yt_wrapper):
        """Test getting available captions with YtDlpError."""
        # Setup
        mock_yt_wrapper.list_available_subtitles.side_effect = YtDlpError("Error fetching subtitles")
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Exercise and Verify
        with pytest.raises(CaptionError, match=r"Failed to get available captions"):
            caption_service.get_available_captions(url)
    
    def test_get_caption(self, caption_service, mock_yt_wrapper, tmp_path):
        """Test getting and parsing a caption."""
        # Setup
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        lang_code = "en"
        subtitle_path = tmp_path / "subtitle.srt"
        
        # Mock available captions
        mock_yt_wrapper.list_available_subtitles.return_value = {
            "en": {
                "is_auto": False,
                "name": "English",
                "format": "srt",
                "url": "https://example.com/subtitle.en.srt"
            }
        }
        
        # Create a simple SRT file for testing
        subtitle_path.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\nHello world\n\n"
            "2\n00:00:05,000 --> 00:00:10,000\nThis is a test\n\n"
        )
        
        # Mock downloading the subtitle
        with patch.object(caption_service, '_get_cached_caption', return_value=None), \
             patch.object(caption_service, '_parse_subtitle_file') as mock_parse:
            
            # Create a sample parsed Caption
            metadata = CaptionMetadata(
                language_code="en",
                language_name="English",
                is_auto_generated=False,
                format="srt",
                source_url=url,
                video_id="dQw4w9WgXcQ"
            )
            
            lines = [
                CaptionLine(index=1, start_time=0.0, end_time=5.0, text="Hello world"),
                CaptionLine(index=2, start_time=5.0, end_time=10.0, text="This is a test")
            ]
            
            expected_caption = Caption(metadata=metadata, lines=lines)
            mock_parse.return_value = expected_caption
            
            # Exercise
            caption = caption_service.get_caption(url, lang_code)
            
            # Verify
            assert caption is expected_caption
            mock_yt_wrapper.list_available_subtitles.assert_called_once_with(url)
    
    def test_get_caption_language_not_available(self, caption_service, mock_yt_wrapper):
        """Test getting a caption with unavailable language."""
        # Setup
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        lang_code = "es"  # Not available
        
        # Mock available captions
        mock_yt_wrapper.list_available_subtitles.return_value = {
            "en": {
                "is_auto": False,
                "name": "English",
                "format": "srt",
                "url": "https://example.com/subtitle.en.srt"
            }
        }
        
        # Exercise and Verify
        with patch.object(caption_service, '_get_cached_caption', return_value=None):
            with pytest.raises(CaptionError, match=r"Caption in language 'es' not available"):
                caption_service.get_caption(url, lang_code)
    
    def test_get_caption_auto_not_allowed(self, caption_service, mock_yt_wrapper):
        """Test getting an auto-generated caption when not allowed."""
        # Setup
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        lang_code = "en"
        
        # Mock available captions
        mock_yt_wrapper.list_available_subtitles.return_value = {
            "en": {
                "is_auto": True,  # Auto-generated
                "name": "English",
                "format": "srt",
                "url": "https://example.com/subtitle.en.srt"
            }
        }
        
        # Exercise and Verify
        with patch.object(caption_service, '_get_cached_caption', return_value=None):
            with pytest.raises(CaptionError, match=r"Only auto-generated captions available"):
                caption_service.get_caption(url, lang_code, allow_auto=False)
    
    def test_get_caption_from_cache(self, caption_service):
        """Test getting a caption from cache."""
        # Setup
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        lang_code = "en"
        
        # Create a sample cached Caption
        metadata = CaptionMetadata(
            language_code="en",
            language_name="English",
            is_auto_generated=False,
            format="srt",
            source_url=url,
            video_id="dQw4w9WgXcQ"
        )
        
        lines = [
            CaptionLine(index=1, start_time=0.0, end_time=5.0, text="Hello world"),
            CaptionLine(index=2, start_time=5.0, end_time=10.0, text="This is a test")
        ]
        
        cached_caption = Caption(metadata=metadata, lines=lines)
        
        # Mock getting from cache
        with patch.object(caption_service, '_get_cached_caption', return_value=cached_caption):
            # Exercise
            caption = caption_service.get_caption(url, lang_code)
            
            # Verify
            assert caption is cached_caption
            caption_service._get_cached_caption.assert_called_once_with("dQw4w9WgXcQ", lang_code, True)
    
    def test_get_caption_preview(self, caption_service):
        """Test getting a caption preview."""
        # Setup
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        lang_code = "en"
        max_lines = 3
        
        # Create a sample Caption
        metadata = CaptionMetadata(
            language_code="en",
            language_name="English",
            is_auto_generated=False,
            format="srt",
            source_url=url,
            video_id="dQw4w9WgXcQ"
        )
        
        lines = [
            CaptionLine(index=1, start_time=0.0, end_time=5.0, text="Line 1"),
            CaptionLine(index=2, start_time=5.0, end_time=10.0, text="Line 2"),
            CaptionLine(index=3, start_time=10.0, end_time=15.0, text="Line 3"),
            CaptionLine(index=4, start_time=15.0, end_time=20.0, text="Line 4"),
            CaptionLine(index=5, start_time=20.0, end_time=25.0, text="Line 5")
        ]
        
        caption = Caption(metadata=metadata, lines=lines)
        
        # Mock getting the full caption
        with patch.object(caption_service, 'get_caption', return_value=caption):
            # Exercise
            preview = caption_service.get_caption_preview(url, lang_code, max_lines=max_lines)
            
            # Verify
            # The actual implementation adds a newline and '...' at the end when there are more lines
            expected = "Line 1\nLine 2\nLine 3\n..."
            assert preview == expected
            assert "Line 4" not in preview
            assert "Line 5" not in preview 