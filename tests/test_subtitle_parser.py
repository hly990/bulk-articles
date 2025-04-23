"""Test script for subtitle parsing functionality (Task 3.3).

This script tests the subtitle parsers by:
1. Creating sample subtitle content in SRT and VTT formats
2. Using ParserFactory to parse these subtitles
3. Displaying the resulting Caption objects
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.subtitle_parser import ParserFactory, ParserError
from services.caption_model import CaptionMetadata, Caption

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("subtitle_parser_test")

def test_srt_parser():
    """Test parsing SRT format subtitles."""
    logger.info("Testing SRT parser...")
    
    # Sample SRT content
    srt_content = """1
00:00:01,000 --> 00:00:04,000
This is the first subtitle.

2
00:00:05,000 --> 00:00:09,500
This is the second subtitle
with multiple lines.

3
00:00:10,000 --> 00:00:14,000
And this is the third one.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="srt",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    try:
        # Parse using factory
        caption = ParserFactory.parse_subtitle(
            content=srt_content,
            metadata=metadata,
            format_name="srt",
            logger=logger
        )
        
        # Display results
        logger.info(f"Successfully parsed SRT content with {len(caption.lines)} lines")
        for line in caption.lines:
            logger.info(f"Line {line.index}: [{line.start_time:.3f} - {line.end_time:.3f}] {line.text}")
        
        return caption
    except ParserError as e:
        logger.error(f"Failed to parse SRT content: {e}")
        return None

def test_vtt_parser():
    """Test parsing WebVTT format subtitles."""
    logger.info("Testing VTT parser...")
    
    # Sample VTT content
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is the first subtitle.

00:00:05.000 --> 00:00:09.500
This is the second subtitle
with multiple lines.

00:00:10.000 --> 00:00:14.000
And this is the third one.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="vtt",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    try:
        # Parse using factory
        caption = ParserFactory.parse_subtitle(
            content=vtt_content,
            metadata=metadata,
            format_name="vtt",
            logger=logger
        )
        
        # Display results
        logger.info(f"Successfully parsed VTT content with {len(caption.lines)} lines")
        for line in caption.lines:
            logger.info(f"Line {line.index}: [{line.start_time:.3f} - {line.end_time:.3f}] {line.text}")
        
        return caption
    except ParserError as e:
        logger.error(f"Failed to parse VTT content: {e}")
        return None

def test_format_detection():
    """Test automatic subtitle format detection."""
    logger.info("Testing format auto-detection...")
    
    # Sample subtitle contents
    srt_content = """1
00:00:01,000 --> 00:00:04,000
This is an SRT subtitle.
"""
    
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is a VTT subtitle.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="auto",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    # Test detection for SRT
    detected_format = ParserFactory.detect_format(srt_content)
    logger.info(f"Detected format for SRT content: {detected_format}")
    
    # Test detection for VTT
    detected_format = ParserFactory.detect_format(vtt_content)
    logger.info(f"Detected format for VTT content: {detected_format}")
    
    # Test parsing with auto-detection
    try:
        caption = ParserFactory.parse_subtitle(
            content=srt_content,
            metadata=metadata,
            format_name=None,  # Auto-detect
            logger=logger
        )
        logger.info(f"Auto-detected and parsed content with {len(caption.lines)} lines")
        return True
    except ParserError as e:
        logger.error(f"Failed to auto-detect and parse: {e}")
        return False

def run_all_tests():
    """Run all subtitle parser tests."""
    logger.info("=== Starting Subtitle Parser Tests ===")
    
    # Run tests
    srt_result = test_srt_parser()
    vtt_result = test_vtt_parser()
    detection_result = test_format_detection()
    
    # Report results
    logger.info("=== Test Results ===")
    logger.info(f"SRT Parser Test: {'PASSED' if srt_result else 'FAILED'}")
    logger.info(f"VTT Parser Test: {'PASSED' if vtt_result else 'FAILED'}")
    logger.info(f"Format Detection Test: {'PASSED' if detection_result else 'FAILED'}")
    
    # Convert to SRT and plain text
    if srt_result:
        logger.info("=== Sample SRT Output ===")
        logger.info(srt_result.to_srt()[:200] + "...")  # Show first 200 chars
        
        logger.info("=== Sample Plain Text Output ===")
        logger.info(srt_result.to_plain_text())
    
    logger.info("=== All Tests Completed ===")

if __name__ == "__main__":
    run_all_tests() 

This script tests the subtitle parsers by:
1. Creating sample subtitle content in SRT and VTT formats
2. Using ParserFactory to parse these subtitles
3. Displaying the resulting Caption objects
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.subtitle_parser import ParserFactory, ParserError
from services.caption_model import CaptionMetadata, Caption

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("subtitle_parser_test")

def test_srt_parser():
    """Test parsing SRT format subtitles."""
    logger.info("Testing SRT parser...")
    
    # Sample SRT content
    srt_content = """1
00:00:01,000 --> 00:00:04,000
This is the first subtitle.

2
00:00:05,000 --> 00:00:09,500
This is the second subtitle
with multiple lines.

3
00:00:10,000 --> 00:00:14,000
And this is the third one.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="srt",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    try:
        # Parse using factory
        caption = ParserFactory.parse_subtitle(
            content=srt_content,
            metadata=metadata,
            format_name="srt",
            logger=logger
        )
        
        # Display results
        logger.info(f"Successfully parsed SRT content with {len(caption.lines)} lines")
        for line in caption.lines:
            logger.info(f"Line {line.index}: [{line.start_time:.3f} - {line.end_time:.3f}] {line.text}")
        
        return caption
    except ParserError as e:
        logger.error(f"Failed to parse SRT content: {e}")
        return None

def test_vtt_parser():
    """Test parsing WebVTT format subtitles."""
    logger.info("Testing VTT parser...")
    
    # Sample VTT content
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is the first subtitle.

00:00:05.000 --> 00:00:09.500
This is the second subtitle
with multiple lines.

00:00:10.000 --> 00:00:14.000
And this is the third one.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="vtt",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    try:
        # Parse using factory
        caption = ParserFactory.parse_subtitle(
            content=vtt_content,
            metadata=metadata,
            format_name="vtt",
            logger=logger
        )
        
        # Display results
        logger.info(f"Successfully parsed VTT content with {len(caption.lines)} lines")
        for line in caption.lines:
            logger.info(f"Line {line.index}: [{line.start_time:.3f} - {line.end_time:.3f}] {line.text}")
        
        return caption
    except ParserError as e:
        logger.error(f"Failed to parse VTT content: {e}")
        return None

def test_format_detection():
    """Test automatic subtitle format detection."""
    logger.info("Testing format auto-detection...")
    
    # Sample subtitle contents
    srt_content = """1
00:00:01,000 --> 00:00:04,000
This is an SRT subtitle.
"""
    
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
This is a VTT subtitle.
"""
    
    # Create metadata
    metadata = CaptionMetadata(
        language_code="en",
        language_name="English",
        is_auto_generated=False,
        format="auto",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ"
    )
    
    # Test detection for SRT
    detected_format = ParserFactory.detect_format(srt_content)
    logger.info(f"Detected format for SRT content: {detected_format}")
    
    # Test detection for VTT
    detected_format = ParserFactory.detect_format(vtt_content)
    logger.info(f"Detected format for VTT content: {detected_format}")
    
    # Test parsing with auto-detection
    try:
        caption = ParserFactory.parse_subtitle(
            content=srt_content,
            metadata=metadata,
            format_name=None,  # Auto-detect
            logger=logger
        )
        logger.info(f"Auto-detected and parsed content with {len(caption.lines)} lines")
        return True
    except ParserError as e:
        logger.error(f"Failed to auto-detect and parse: {e}")
        return False

def run_all_tests():
    """Run all subtitle parser tests."""
    logger.info("=== Starting Subtitle Parser Tests ===")
    
    # Run tests
    srt_result = test_srt_parser()
    vtt_result = test_vtt_parser()
    detection_result = test_format_detection()
    
    # Report results
    logger.info("=== Test Results ===")
    logger.info(f"SRT Parser Test: {'PASSED' if srt_result else 'FAILED'}")
    logger.info(f"VTT Parser Test: {'PASSED' if vtt_result else 'FAILED'}")
    logger.info(f"Format Detection Test: {'PASSED' if detection_result else 'FAILED'}")
    
    # Convert to SRT and plain text
    if srt_result:
        logger.info("=== Sample SRT Output ===")
        logger.info(srt_result.to_srt()[:200] + "...")  # Show first 200 chars
        
        logger.info("=== Sample Plain Text Output ===")
        logger.info(srt_result.to_plain_text())
    
    logger.info("=== All Tests Completed ===")

if __name__ == "__main__":
    run_all_tests() 