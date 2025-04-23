"""Test script for CaptionService with the subtitle parser integration (Task 3.3).

This script demonstrates how CaptionService uses the subtitle parser by:
1. Creating a mock YtDlpWrapper that returns sample subtitle data
2. Initializing a CaptionService with the mock wrapper
3. Testing the get_caption method with different formats
"""

import sys
import os
import logging
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.yt_dlp_wrapper import YtDlpWrapper
from services.caption_service import CaptionService
from services.caption_model import Caption, CaptionMetadata

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("caption_service_test")

def create_test_file(content, extension):
    """Create a temporary file with the given content and extension."""
    fd, path = tempfile.mkstemp(suffix=f".{extension}")
    os.write(fd, content.encode('utf-8'))
    os.close(fd)
    return path

def create_mock_yt_dlp_wrapper():
    """Create a mock YtDlpWrapper that returns sample subtitle content."""
    mock_wrapper = MagicMock(spec=YtDlpWrapper)
    
    # Sample subtitles in different formats
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
This is a sample SRT subtitle.

2
00:00:05,000 --> 00:00:09,500
Testing the CaptionService with SRT format.
"""
    
    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is a sample VTT subtitle.

00:00:05.000 --> 00:00:09.500
Testing the CaptionService with VTT format.
"""
    
    # Configure mock to list available subtitles
    mock_wrapper.list_subtitles.return_value = {
        'manual': [
            {'name': 'English', 'code': 'en', 'ext': 'vtt'},
            {'name': 'Spanish', 'code': 'es', 'ext': 'vtt'}
        ],
        'automatic': [
            {'name': 'English (auto)', 'code': 'en', 'ext': 'vtt'}
        ]
    }
    
    # Configure mock to download subtitles
    def mock_download_subtitle(url, output_path, language, formats, source):
        """Mock the download_subtitle method to create subtitle files."""
        if language == 'en':
            if 'srt' in formats and formats.index('srt') < formats.index('vtt'):
                # Create SRT file
                ext = 'srt'
                content = sample_srt
            else:
                # Create VTT file
                ext = 'vtt'
                content = sample_vtt
                
            # Write file at the expected location
            file_path = f"{output_path}.{ext}"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                'ext': ext,
                'name': 'English',
                'language_name': 'English',
                'filepath': file_path
            }
        else:
            return None  # No subtitles available for other languages
    
    mock_wrapper.download_subtitle.side_effect = mock_download_subtitle
    
    return mock_wrapper

def test_caption_service():
    """Test the CaptionService with the subtitle parser integration."""
    logger.info("=== Testing CaptionService with Subtitle Parser ===")
    
    # Create mock wrapper
    mock_wrapper = create_mock_yt_dlp_wrapper()
    
    # Create temp directory for cache
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CaptionService with mock wrapper
        service = CaptionService(
            yt_dlp_wrapper=mock_wrapper,
            cache_dir=temp_dir,
            logger=logger
        )
        
        # Test getting available captions
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        available_captions = service.get_available_captions(video_url)
        
        logger.info(f"Available captions: {json.dumps(available_captions, indent=2)}")
        
        # Test getting caption with SRT format preference
        logger.info("Testing get_caption with SRT format preference...")
        try:
            caption_srt = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["srt", "vtt"],
                use_cache=False
            )
            
            logger.info(f"Successfully retrieved caption with {len(caption_srt.lines)} lines")
            logger.info(f"Caption metadata: format={caption_srt.metadata.format}")
            logger.info("Caption preview:")
            logger.info(service.get_caption_preview(caption_srt))
            
        except Exception as e:
            logger.error(f"Failed to get caption with SRT format: {e}")
        
        # Test getting caption with VTT format preference
        logger.info("Testing get_caption with VTT format preference...")
        try:
            caption_vtt = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["vtt", "srt"],
                use_cache=False
            )
            
            logger.info(f"Successfully retrieved caption with {len(caption_vtt.lines)} lines")
            logger.info(f"Caption metadata: format={caption_vtt.metadata.format}")
            logger.info("Caption preview:")
            logger.info(service.get_caption_preview(caption_vtt))
            
        except Exception as e:
            logger.error(f"Failed to get caption with VTT format: {e}")
        
        # Test caching functionality
        logger.info("Testing caption caching...")
        
        try:
            # Get caption with caching enabled
            caption_cached = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["vtt", "srt"],
                use_cache=True
            )
            
            # Print cache info
            cache_files = list(Path(temp_dir).glob("*.json"))
            logger.info(f"Cache directory contains {len(cache_files)} files")
            for cache_file in cache_files:
                logger.info(f"Cache file: {cache_file.name}")
                
            logger.info("Successfully tested caching")
            
        except Exception as e:
            logger.error(f"Failed to test caching: {e}")
        
        logger.info("=== CaptionService Testing Completed ===")

if __name__ == "__main__":
    test_caption_service() 

This script demonstrates how CaptionService uses the subtitle parser by:
1. Creating a mock YtDlpWrapper that returns sample subtitle data
2. Initializing a CaptionService with the mock wrapper
3. Testing the get_caption method with different formats
"""

import sys
import os
import logging
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.yt_dlp_wrapper import YtDlpWrapper
from services.caption_service import CaptionService
from services.caption_model import Caption, CaptionMetadata

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("caption_service_test")

def create_test_file(content, extension):
    """Create a temporary file with the given content and extension."""
    fd, path = tempfile.mkstemp(suffix=f".{extension}")
    os.write(fd, content.encode('utf-8'))
    os.close(fd)
    return path

def create_mock_yt_dlp_wrapper():
    """Create a mock YtDlpWrapper that returns sample subtitle content."""
    mock_wrapper = MagicMock(spec=YtDlpWrapper)
    
    # Sample subtitles in different formats
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
This is a sample SRT subtitle.

2
00:00:05,000 --> 00:00:09,500
Testing the CaptionService with SRT format.
"""
    
    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is a sample VTT subtitle.

00:00:05.000 --> 00:00:09.500
Testing the CaptionService with VTT format.
"""
    
    # Configure mock to list available subtitles
    mock_wrapper.list_subtitles.return_value = {
        'manual': [
            {'name': 'English', 'code': 'en', 'ext': 'vtt'},
            {'name': 'Spanish', 'code': 'es', 'ext': 'vtt'}
        ],
        'automatic': [
            {'name': 'English (auto)', 'code': 'en', 'ext': 'vtt'}
        ]
    }
    
    # Configure mock to download subtitles
    def mock_download_subtitle(url, output_path, language, formats, source):
        """Mock the download_subtitle method to create subtitle files."""
        if language == 'en':
            if 'srt' in formats and formats.index('srt') < formats.index('vtt'):
                # Create SRT file
                ext = 'srt'
                content = sample_srt
            else:
                # Create VTT file
                ext = 'vtt'
                content = sample_vtt
                
            # Write file at the expected location
            file_path = f"{output_path}.{ext}"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                'ext': ext,
                'name': 'English',
                'language_name': 'English',
                'filepath': file_path
            }
        else:
            return None  # No subtitles available for other languages
    
    mock_wrapper.download_subtitle.side_effect = mock_download_subtitle
    
    return mock_wrapper

def test_caption_service():
    """Test the CaptionService with the subtitle parser integration."""
    logger.info("=== Testing CaptionService with Subtitle Parser ===")
    
    # Create mock wrapper
    mock_wrapper = create_mock_yt_dlp_wrapper()
    
    # Create temp directory for cache
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize CaptionService with mock wrapper
        service = CaptionService(
            yt_dlp_wrapper=mock_wrapper,
            cache_dir=temp_dir,
            logger=logger
        )
        
        # Test getting available captions
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        available_captions = service.get_available_captions(video_url)
        
        logger.info(f"Available captions: {json.dumps(available_captions, indent=2)}")
        
        # Test getting caption with SRT format preference
        logger.info("Testing get_caption with SRT format preference...")
        try:
            caption_srt = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["srt", "vtt"],
                use_cache=False
            )
            
            logger.info(f"Successfully retrieved caption with {len(caption_srt.lines)} lines")
            logger.info(f"Caption metadata: format={caption_srt.metadata.format}")
            logger.info("Caption preview:")
            logger.info(service.get_caption_preview(caption_srt))
            
        except Exception as e:
            logger.error(f"Failed to get caption with SRT format: {e}")
        
        # Test getting caption with VTT format preference
        logger.info("Testing get_caption with VTT format preference...")
        try:
            caption_vtt = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["vtt", "srt"],
                use_cache=False
            )
            
            logger.info(f"Successfully retrieved caption with {len(caption_vtt.lines)} lines")
            logger.info(f"Caption metadata: format={caption_vtt.metadata.format}")
            logger.info("Caption preview:")
            logger.info(service.get_caption_preview(caption_vtt))
            
        except Exception as e:
            logger.error(f"Failed to get caption with VTT format: {e}")
        
        # Test caching functionality
        logger.info("Testing caption caching...")
        
        try:
            # Get caption with caching enabled
            caption_cached = service.get_caption(
                url=video_url,
                language="en",
                source="manual",
                formats=["vtt", "srt"],
                use_cache=True
            )
            
            # Print cache info
            cache_files = list(Path(temp_dir).glob("*.json"))
            logger.info(f"Cache directory contains {len(cache_files)} files")
            for cache_file in cache_files:
                logger.info(f"Cache file: {cache_file.name}")
                
            logger.info("Successfully tested caching")
            
        except Exception as e:
            logger.error(f"Failed to test caching: {e}")
        
        logger.info("=== CaptionService Testing Completed ===")

if __name__ == "__main__":
    test_caption_service() 