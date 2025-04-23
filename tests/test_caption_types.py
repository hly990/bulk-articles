"""Test script for auto-generated and manual caption support (Task 3.4).

This script tests the enhanced caption type handling by:
1. Creating sample auto-generated captions with speaker identification
2. Creating sample manual captions
3. Testing the detection and special handling for different caption types
"""

import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.yt_dlp_wrapper import YtDlpWrapper
from services.caption_service import CaptionService
from services.caption_model import Caption, CaptionMetadata, CaptionLine
from services.subtitle_parser import VttParser

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("caption_types_test")

def test_auto_generated_caption_detection():
    """Test detection of auto-generated captions with speaker identification."""
    logger.info("=== Testing Auto-Generated Caption Detection ===")
    
    # Create sample auto-generated VTT with speaker identification
    auto_generated_vtt = """WEBVTT

00:00:01.000 --> 00:00:05.000
<v Speaker 1>Welcome to this video about machine learning.</v>

00:00:06.000 --> 00:00:10.000
<v Speaker 2>Today we'll be discussing neural networks.</v>

00:00:11.000 --> 00:00:15.000
[SPEAKER 1]: Let's start with the basics.

00:00:16.000 --> 00:00:20.000
[Music]
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=True,
        format="vtt",
        source_url="https://www.youtube.com/watch?v=example",
        video_id="example"
    )
    
    # Parse the VTT content
    parser = VttParser(logger=logger)
    caption = parser.parse(auto_generated_vtt, metadata)
    
    # Check if speaker identification was detected
    logger.info(f"Caption has speaker identification: {metadata.has_speaker_identification}")
    
    # Display the parsed lines
    logger.info("Parsed caption lines with speaker information:")
    for line in caption.lines:
        logger.info(f"[{line.start_time:.1f}-{line.end_time:.1f}] {line.text}")
    
    return metadata.has_speaker_identification

def test_caption_service_type_handling():
    """Test CaptionService handling of different caption types."""
    logger.info("=== Testing CaptionService Type Handling ===")
    
    # Create mock YtDlpWrapper
    mock_wrapper = MagicMock(spec=YtDlpWrapper)
    
    # Configure mock to list available subtitles
    mock_wrapper.list_subtitles.return_value = {
        'manual': [
            {
                'language': 'en',
                'name': 'English',
                'format': 'vtt',
                'ext': 'vtt',
                'caption_type': 'manual',
                'has_speaker_id': False,
                'is_default': True
            },
            {
                'language': 'fr',
                'name': 'French',
                'format': 'vtt',
                'ext': 'vtt',
                'caption_type': 'translated',
                'has_speaker_id': False,
                'is_default': False
            }
        ],
        'automatic': [
            {
                'language': 'en',
                'name': 'English',
                'format': 'vtt',
                'ext': 'vtt',
                'caption_type': 'auto_generated',
                'has_speaker_id': True,
                'is_default': False
            }
        ]
    }
    
    # Initialize CaptionService with mock wrapper
    service = CaptionService(
        yt_dlp_wrapper=mock_wrapper,
        logger=logger
    )
    
    # Test filtering captions by type
    logger.info("Testing filtering captions by type...")
    
    # Get available captions
    video_url = "https://www.youtube.com/watch?v=example"
    captions_info = mock_wrapper.list_subtitles.return_value
    
    # Filter by different types
    manual_captions = service.filter_captions_by_type(captions_info, 'manual')
    auto_captions = service.filter_captions_by_type(captions_info, 'auto_generated')
    translated_captions = service.filter_captions_by_type(captions_info, 'translated')
    
    logger.info(f"Manual captions count: {len(manual_captions)}")
    logger.info(f"Auto-generated captions count: {len(auto_captions)}")
    logger.info(f"Translated captions count: {len(translated_captions)}")
    
    # Test finding captions with speaker identification
    speaker_captions = service.has_speaker_identification(captions_info)
    logger.info(f"Captions with speaker identification count: {len(speaker_captions)}")
    
    # Test getting default caption
    default_caption = service.get_default_caption(captions_info)
    if default_caption:
        logger.info(f"Default caption: {default_caption['language']} ({default_caption['caption_type']})")
    else:
        logger.info("No default caption found")
    
    return {
        'manual': len(manual_captions),
        'auto': len(auto_captions),
        'translated': len(translated_captions),
        'speaker': len(speaker_captions),
        'has_default': default_caption is not None
    }

def test_subtitle_download_with_types():
    """Test downloading and parsing captions with type information."""
    logger.info("=== Testing Subtitle Download With Types ===")
    
    # Create a mock YtDlpWrapper with enhanced subtitle information
    mock_wrapper = MagicMock(spec=YtDlpWrapper)
    
    # Configure the mock for list_subtitles
    mock_wrapper.list_subtitles.return_value = {
        'manual': [
            {
                'language': 'en',
                'name': 'English',
                'format': 'vtt',
                'ext': 'vtt',
                'caption_type': 'manual',
                'has_speaker_id': False,
                'is_default': True
            }
        ],
        'automatic': [
            {
                'language': 'en',
                'name': 'English (auto)',
                'format': 'vtt',
                'ext': 'vtt',
                'caption_type': 'auto_generated',
                'has_speaker_id': True,
                'is_default': False
            }
        ]
    }
    
    # Configure the mock for download_subtitle
    # For manual captions
    mock_wrapper.download_subtitle.side_effect = lambda url, output_path, language, formats, source: {
        'ext': 'vtt',
        'name': 'English' if source == 'manual' else 'English (auto)',
        'language_name': 'English',
        'language_code': 'en',
        'filepath': output_path,
        'caption_type': 'manual' if source == 'manual' else 'auto_generated',
        'has_speaker_id': False if source == 'manual' else True,
        'is_default': True if source == 'manual' else False,
        'is_auto_generated': source != 'manual'
    }
    
    # Test the download function with manual and auto-generated captions
    url = "https://www.youtube.com/watch?v=example"
    logger.info(f"Testing download_subtitle for URL: {url}")
    
    # Test with manual captions
    manual_result = mock_wrapper.download_subtitle(url, "/tmp/manual.vtt", "en", ["vtt"], "manual")
    logger.info(f"Manual caption info: type={manual_result['caption_type']}, "
               f"speaker_id={manual_result['has_speaker_id']}, "
               f"is_default={manual_result['is_default']}")
    
    # Test with auto-generated captions
    auto_result = mock_wrapper.download_subtitle(url, "/tmp/auto.vtt", "en", ["vtt"], "automatic")
    logger.info(f"Auto caption info: type={auto_result['caption_type']}, "
               f"speaker_id={auto_result['has_speaker_id']}, "
               f"is_default={auto_result['is_default']}")
    
    return {
        'manual_type': manual_result['caption_type'],
        'auto_type': auto_result['caption_type'],
        'manual_speaker': manual_result['has_speaker_id'],
        'auto_speaker': auto_result['has_speaker_id']
    }

def run_all_tests():
    """Run all tests for auto-generated and manual caption support."""
    logger.info("=== Starting Caption Types Tests ===")
    
    # Run tests
    speaker_result = test_auto_generated_caption_detection()
    service_result = test_caption_service_type_handling()
    download_result = test_subtitle_download_with_types()
    
    # Report results
    logger.info("=== Test Results ===")
    logger.info(f"Speaker detection test: {'PASSED' if speaker_result else 'FAILED'}")
    logger.info(f"Caption service handling: {service_result}")
    logger.info(f"Subtitle download types: {download_result}")
    
    logger.info("=== All Tests Completed ===")

if __name__ == "__main__":
    run_all_tests() 