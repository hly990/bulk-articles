"""Test script for caption preview functionality (Task 3.7).

This script tests the enhanced caption preview functionality by:
1. Testing the basic caption preview with different formats
2. Testing multilingual preview generation
3. Testing cached preview retrieval
4. Verifying proper formatting and truncation
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.caption_service import CaptionService
from services.caption_model import Caption, CaptionMetadata, CaptionLine
from services.yt_dlp_wrapper import YtDlpWrapper


def create_test_caption(video_id="test_video", language="en", is_auto=False, lines=10):
    """Create a test caption for testing."""
    caption_type = "auto_generated" if is_auto else "manual"
    metadata = CaptionMetadata(
        video_id=video_id,
        language_code=language,
        language_name="English" if language == "en" else "Spanish",
        is_auto_generated=is_auto,
        format="vtt",
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        caption_type=caption_type,
        has_speaker_identification=is_auto,
        provider="youtube",
        is_default=language == "en"
    )
    
    caption = Caption(metadata=metadata)
    for i in range(lines):
        caption.lines.append(
            CaptionLine(
                index=i,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                text=f"Test caption line {i+1}"
            )
        )
    
    return caption


def test_basic_preview():
    """Test basic caption preview functionality."""
    # Create a mock YtDlpWrapper
    mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
    
    # Create the service
    service = CaptionService(yt_dlp_wrapper=mock_yt_dlp)
    
    # Create test caption
    caption = create_test_caption()
    
    # Test default preview
    preview = service.get_caption_preview(caption, max_lines=3)
    assert "[0.0-5.0] Test caption line 1" in preview
    assert "... and 7 more lines" in preview
    
    # Test all lines
    preview = service.get_caption_preview(caption, max_lines=10)
    assert "... and" not in preview
    assert "Test caption line 10" in preview


def test_preview_formats():
    """Test different preview formats."""
    # Create a mock YtDlpWrapper
    mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
    
    # Create the service
    service = CaptionService(yt_dlp_wrapper=mock_yt_dlp)
    
    # Create test caption
    caption = create_test_caption()
    
    # Test plain format
    plain_preview = service.get_caption_preview(caption, max_lines=2, format_type='plain')
    assert "[0.0-5.0]" not in plain_preview
    assert "Test caption line 1" in plain_preview
    assert "Test caption line 2" in plain_preview
    
    # Test SRT format
    srt_preview = service.get_caption_preview(caption, max_lines=1, format_type='srt')
    assert "00:00:00,000 --> 00:00:05,000" in srt_preview
    
    # Test HTML format
    html_preview = service.get_caption_preview(caption, max_lines=1, format_type='html')
    assert '<div class="caption-line">' in html_preview
    assert '<span class="timestamp">' in html_preview
    assert '<span class="text">' in html_preview


def test_preview_with_metadata():
    """Test preview with metadata included."""
    # Create a mock YtDlpWrapper
    mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
    
    # Create the service
    service = CaptionService(yt_dlp_wrapper=mock_yt_dlp)
    
    # Create test captions, one manual and one auto
    manual_caption = create_test_caption(is_auto=False)
    auto_caption = create_test_caption(is_auto=True)
    
    # Test manual caption with metadata
    manual_preview = service.get_caption_preview(manual_caption, max_lines=1, include_metadata=True)
    assert "Language: English (en)" in manual_preview
    assert "Type: manual" in manual_preview
    assert "Auto-generated: No" in manual_preview
    
    # Test auto caption with metadata
    auto_preview = service.get_caption_preview(auto_caption, max_lines=1, include_metadata=True)
    assert "Type: auto_generated" in auto_preview
    assert "Auto-generated: Yes" in auto_preview
    assert "Has speaker identification: Yes" in auto_preview
    
    # Test HTML format with metadata
    html_preview = service.get_caption_preview(
        auto_caption, max_lines=1, format_type='html', include_metadata=True
    )
    assert '<div class="caption-metadata">' in html_preview
    assert '<div>Language: English (en)</div>' in html_preview


@patch('services.caption_service.CaptionService.get_available_captions')
@patch('services.caption_service.CaptionService.get_caption')
def test_multilingual_preview(mock_get_caption, mock_get_available):
    """Test multilingual preview generation."""
    # Create a mock YtDlpWrapper
    mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
    
    # Create the service
    service = CaptionService(yt_dlp_wrapper=mock_yt_dlp)
    
    # Mock available captions response
    mock_get_available.return_value = {
        'manual': [
            {'language': 'en', 'name': 'English'},
            {'language': 'es', 'name': 'Spanish'}
        ],
        'automatic': []
    }
    
    # Mock get_caption to return test captions
    def get_caption_side_effect(url, language, **kwargs):
        return create_test_caption(language=language)
    
    mock_get_caption.side_effect = get_caption_side_effect
    
    # Test multilingual preview
    url = "https://www.youtube.com/watch?v=test123"
    previews = service.get_caption_previews_multilingual(
        url, languages=['en', 'es'], max_lines=2
    )
    
    # Check results
    assert 'en' in previews
    assert 'es' in previews
    assert "English (en)" in previews['en']
    assert "Spanish (es)" in previews['es']
    assert "Test caption line 1" in previews['en']
    assert "Test caption line 2" in previews['en']


def test_cached_preview():
    """Test cached preview functionality."""
    # Create a temporary directory for cache
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock YtDlpWrapper
        mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
        
        # Create the service with cache enabled
        service = CaptionService(
            yt_dlp_wrapper=mock_yt_dlp,
            cache_dir=temp_dir
        )
        
        # Create and store a test caption
        caption = create_test_caption(video_id="cached_video")
        service.cache.store(caption)
        
        # Test cached preview
        preview = service.get_caption_preview_cached(
            video_id="cached_video",
            language="en",
            source="manual",
            max_lines=3
        )
        
        # Check result
        assert preview is not None
        assert "Test caption line 1" in preview
        assert "... and 7 more lines" in preview
        
        # Test non-existent cached preview
        none_preview = service.get_caption_preview_cached(
            video_id="non_existent",
            language="en",
            source="manual"
        )
        assert none_preview is None


# Verify that task 3.7 is completed successfully
def test_task_37_completion():
    """Verify that task 3.7 is completed successfully."""
    # Create a mock YtDlpWrapper
    mock_yt_dlp = MagicMock(spec=YtDlpWrapper)
    
    # Create the service
    service = CaptionService(yt_dlp_wrapper=mock_yt_dlp)
    
    # Create a test caption
    caption = create_test_caption()
    
    # Check all required functionality:
    
    # 1. Basic preview with timestamps
    preview1 = service.get_caption_preview(caption, max_lines=2)
    assert "[0.0-5.0]" in preview1
    
    # 2. Plain text preview
    preview2 = service.get_caption_preview(caption, max_lines=2, format_type='plain')
    assert "[0.0-5.0]" not in preview2
    assert "Test caption line" in preview2
    
    # 3. SRT format preview
    preview3 = service.get_caption_preview(caption, max_lines=1, format_type='srt')
    assert "00:00:00,000 --> 00:00:05,000" in preview3
    
    # 4. HTML format preview with metadata
    preview4 = service.get_caption_preview(
        caption, max_lines=1, format_type='html', include_metadata=True
    )
    assert '<div class="caption-metadata">' in preview4
    assert '<span class="timestamp">' in preview4
    
    # Functionality requirements met!
    assert True


if __name__ == "__main__":
    # Run all tests
    pytest.main(["-xvs", __file__]) 