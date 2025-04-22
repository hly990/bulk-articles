import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Union, Optional


class SubtitleConverter:
    """
    Class for converting between different subtitle formats and extracting text.
    Supports VTT and SRT formats for conversion to plain text and JSON.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def convert_to_plain_text(self, 
                              input_path: Union[str, Path], 
                              output_path: Union[str, Path]) -> Path:
        """
        Convert subtitle file to plain text, removing timestamps and formatting.
        
        Args:
            input_path: Path to the subtitle file (VTT or SRT)
            output_path: Path where the plain text will be saved
            
        Returns:
            Path to the saved plain text file
        
        Raises:
            ValueError: If the input file format is not supported
            FileNotFoundError: If the input file doesn't exist
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {input_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Determine the format based on file extension
        file_format = input_path.suffix.lower()[1:]  # Remove the dot
        
        if file_format == "vtt":
            self._convert_vtt_to_text(input_path, output_path)
        elif file_format == "srt":
            self._convert_srt_to_text(input_path, output_path)
        else:
            raise ValueError(f"Unsupported subtitle format: {file_format}. Supported formats: vtt, srt")
            
        return output_path
    
    def convert_to_json(self, 
                         input_path: Union[str, Path], 
                         output_path: Union[str, Path]) -> Path:
        """
        Convert subtitle file to JSON format for advanced processing.
        The JSON format will contain start time, end time, and text for each subtitle.
        
        Args:
            input_path: Path to the subtitle file (VTT or SRT)
            output_path: Path where the JSON will be saved
            
        Returns:
            Path to the saved JSON file
            
        Raises:
            ValueError: If the input file format is not supported
            FileNotFoundError: If the input file doesn't exist
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {input_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Determine the format based on file extension
        file_format = input_path.suffix.lower()[1:]  # Remove the dot
        
        if file_format == "vtt":
            subtitle_data = self._parse_vtt_to_data(input_path)
        elif file_format == "srt":
            subtitle_data = self._parse_srt_to_data(input_path)
        else:
            raise ValueError(f"Unsupported subtitle format: {file_format}. Supported formats: vtt, srt")
        
        # Write to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(subtitle_data, f, ensure_ascii=False, indent=2)
            
        return output_path
    
    def _convert_vtt_to_text(self, input_path: Path, output_path: Path) -> None:
        """Extract plain text from a VTT file, removing timestamps and other non-text elements."""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip the WEBVTT header
        if content.startswith('WEBVTT'):
            content = content.split('WEBVTT', 1)[1]
        
        # Remove timestamps (00:00:00.000 --> 00:00:00.000)
        content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', content)
        
        # Remove numeric identifiers (for cue identifiers)
        content = re.sub(r'^\d+$', '', content, flags=re.MULTILINE)
        
        # Remove any blank lines
        content = re.sub(r'\n\s*\n', '\n', content)
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _convert_srt_to_text(self, input_path: Path, output_path: Path) -> None:
        """Extract plain text from an SRT file, removing timestamps and sequence numbers."""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove sequence numbers and timestamps
        # SRT format: sequence number, timestamp, text, blank line
        content = re.sub(r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\s*\n', '', content, flags=re.MULTILINE)
        
        # Remove any blank lines
        content = re.sub(r'\n\s*\n', '\n', content)
        
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _parse_vtt_to_data(self, input_path: Path) -> List[Dict]:
        """Parse VTT file into structured data with timestamps and text."""
        subtitle_data = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Skip header
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == 'WEBVTT':
                start_idx = i + 1
                break
        
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip blank lines and comments
            if not line or line.startswith('NOTE') or line.startswith('STYLE'):
                i += 1
                continue
            
            # Skip cue identifier if present (it could be a number or a string)
            if not ' --> ' in line:
                i += 1
                continue
            
            # This should be a timestamp line
            if ' --> ' in line:
                timestamp = line.strip()
                start_time, end_time = timestamp.split(' --> ')
                
                # Move to the text content
                i += 1
                text_lines = []
                
                # Collect all text until we hit a blank line
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                text = ' '.join(text_lines)
                
                subtitle_data.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text
                })
            else:
                # Skip any unexpected line format
                i += 1
        
        return subtitle_data
    
    def _parse_srt_to_data(self, input_path: Path) -> List[Dict]:
        """Parse SRT file into structured data with timestamps and text."""
        subtitle_data = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by double newline to separate entries
        entries = re.split(r'\n\s*\n', content)
        
        for entry in entries:
            lines = entry.strip().split('\n')
            if len(lines) < 3:
                continue
            
            # First line is sequence number, second line is timestamp
            try:
                sequence = int(lines[0])
                timestamp = lines[1]
                start_time, end_time = timestamp.split(' --> ')
                
                # Remaining lines are the text
                text = ' '.join(lines[2:])
                
                subtitle_data.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text
                })
            except (ValueError, IndexError):
                # Skip malformed entries
                self.logger.warning(f"Skipping malformed SRT entry: {entry}")
                continue
        
        return subtitle_data 