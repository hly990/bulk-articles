import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.services.yt_dlp_wrapper import YtDlpWrapper
from src.services.subtitle_converter import SubtitleConverter


@pytest.fixture
def sample_subtitle_content():
    """Sample VTT subtitle content for testing"""
    return """WEBVTT

00:00:00.000 --> 00:00:03.000
Hello, welcome to this video

00:00:03.500 --> 00:00:06.000
Today we'll be discussing important topics

00:00:06.500 --> 00:00:10.000
Let's get started with our discussion
"""


@pytest.fixture
def mock_yt_dlp_wrapper(sample_subtitle_content):
    """Create a mocked YtDlpWrapper with predefined behavior"""
    wrapper = MagicMock(spec=YtDlpWrapper)
    
    # Mock list_available_subtitles
    wrapper.list_available_subtitles.return_value = {
        "en": {"name": "English", "formats": ["vtt", "srt"], "is_auto": False},
        "fr": {"name": "French", "formats": ["vtt", "srt"], "is_auto": False},
        "es": {"name": "Spanish", "formats": ["vtt"], "is_auto": True},
    }
    
    # Mock download_subtitle to write sample content to the requested path
    def mock_download(url, lang_code, output_path, auto_generated=False, format="vtt"):
        # Create the directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write sample subtitle content to the file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sample_subtitle_content)
        
        return output_path
    
    wrapper.download_subtitle.side_effect = mock_download
    return wrapper


@pytest.fixture
def subtitle_converter():
    """Create a real SubtitleConverter instance"""
    return SubtitleConverter()


class TestSubtitleExtractionPipeline:
    """Integration tests for the subtitle extraction and conversion pipeline"""
    
    def test_list_and_download_subtitles(self, mock_yt_dlp_wrapper, tmp_path):
        """Test listing and downloading subtitles"""
        url = "https://www.youtube.com/watch?v=test_video_id"
        
        # List available subtitles
        subtitles = mock_yt_dlp_wrapper.list_available_subtitles(url)
        
        # Verify we have the expected languages
        assert "en" in subtitles
        assert "fr" in subtitles
        assert "es" in subtitles
        
        # Download English subtitles
        output_path = tmp_path / "subtitles" / "test_video_id.en.vtt"
        result_path = mock_yt_dlp_wrapper.download_subtitle(
            url=url,
            lang_code="en",
            output_path=output_path,
            auto_generated=False,
            format="vtt"
        )
        
        # Verify the file exists and has content
        assert result_path.exists()
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "Hello, welcome to this video" in content
    
    def test_subtitle_conversion_pipeline(self, mock_yt_dlp_wrapper, subtitle_converter, tmp_path):
        """Test the complete subtitle extraction and conversion pipeline"""
        url = "https://www.youtube.com/watch?v=test_video_id"
        
        # 1. List available subtitles
        subtitles = mock_yt_dlp_wrapper.list_available_subtitles(url)
        
        # 2. Download English subtitles as VTT
        vtt_path = tmp_path / "subtitles" / "test_video_id.en.vtt"
        mock_yt_dlp_wrapper.download_subtitle(
            url=url,
            lang_code="en",
            output_path=vtt_path,
            auto_generated=False,
            format="vtt"
        )
        
        # 3. Convert VTT to plain text
        text_path = tmp_path / "subtitles" / "test_video_id.en.txt"
        subtitle_converter.convert_to_plain_text(vtt_path, text_path)
        
        # Verify the plain text file exists and has the expected content
        assert text_path.exists()
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        # Check that the text contains the subtitle content without timestamps
        assert "Hello, welcome to this video" in text_content
        assert "Today we'll be discussing important topics" in text_content
        assert "Let's get started with our discussion" in text_content
        
        # Check that timestamps were removed
        assert "00:00:00.000" not in text_content
        
        # 4. Convert VTT to JSON format (for potential NLP processing)
        json_path = tmp_path / "subtitles" / "test_video_id.en.json"
        subtitle_converter.convert_to_json(vtt_path, json_path)
        
        # Verify the JSON file exists and has the expected structure
        assert json_path.exists()
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
        
        # Check JSON structure
        assert isinstance(json_content, list)
        assert len(json_content) == 3  # 3 subtitle entries
        
        # Check first subtitle entry
        assert "start" in json_content[0]
        assert "end" in json_content[0]
        assert "text" in json_content[0]
        assert json_content[0]["text"] == "Hello, welcome to this video" 