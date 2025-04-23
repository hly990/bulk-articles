# Task 3.4: Add support for auto-generated and manual captions

## Implementation Summary

Task 3.4 has been successfully implemented, adding comprehensive support for different caption types in the YouTube captions extraction service. The implementation focuses on distinguishing between auto-generated and manual captions, with special handling for speaker identification in auto-generated captions.

## Key Components Modified

1. **Caption Metadata Model** (`src/services/caption_model.py`):
   - Extended `CaptionMetadata` class with new fields:
     - `caption_type`: Identifying manual, auto-generated, or translated captions
     - `has_speaker_identification`: Flag for captions with speaker information
     - `is_default`: Flag for default caption tracks
     - `quality_score`: Optional field for caption quality estimation
     - `provider`: Source of captions (usually "youtube")

2. **YtDlpWrapper** (`src/services/yt_dlp_wrapper.py`):
   - Enhanced `list_subtitles` method to include detailed caption type information
   - Improved `download_subtitle` method to return rich metadata and detect caption features
   - Added detection for special caption types like translated captions
   - Implemented robust speaker identification detection in downloaded content

3. **CaptionService** (`src/services/caption_service.py`):
   - Added methods to filter captions by type: `filter_captions_by_type()`
   - Added method to find captions with speaker identification: `has_speaker_identification()`
   - Added method to get default caption track: `get_default_caption()`
   - Updated `get_caption()` to utilize enhanced metadata from YtDlpWrapper

4. **VttParser** (`src/services/subtitle_parser.py`):
   - Added advanced speaker identification in VTT captions
   - Implemented parsing for different speaker formats:
     - VTT voice tags: `<v Speaker 1>Text</v>`
     - Speaker prefixes: `[SPEAKER 1]: Text`
     - Bracketed speakers: `[John] Text`
   - Added preservation of speaker information in clean text

## Tests Created

A new test script `tests/test_caption_types.py` was created to verify:

1. Auto-generated caption speaker detection
2. Caption service type handling
3. Subtitle download with proper type detection

All tests pass successfully, confirming that the implementation meets the requirements.

## Documentation

Comprehensive documentation was created in `docs/caption_types.md` covering:

1. Types of captions supported
2. Enhanced metadata model
3. Speaker identification features
4. YtDlpWrapper enhancements
5. CaptionService features
6. Usage examples for different caption types
7. Future extension possibilities

## Future Improvements

1. Add quality estimation for auto-generated captions
2. Implement AI-based speaker diarization for captions without speaker information
3. Support merging/synchronization of multiple caption tracks
4. Add customizable speaker detection patterns 