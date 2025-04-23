"""
Caption Caching Module for YouTube captions.

This module provides classes for efficiently caching YouTube captions to disk,
reducing the need for repeated downloads and improving performance.
"""

import os
import json
import logging
import time
import re
import glob
import pickle
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import shutil
from pathlib import Path

from .caption_model import Caption

__all__ = [
    "CaptionCache",
    "CacheConfig",
    "CacheKey",
]


@dataclass
class CacheConfig:
    """Configuration for the caption cache."""
    enabled: bool = True
    max_age: int = 60 * 60 * 24 * 7  # 7 days in seconds
    max_size: int = 100 * 1024 * 1024  # 100 MB
    auto_clean: bool = True
    min_entries: int = 10
    refresh_on_access: bool = False
    format: str = "json"  # 'json' or 'pickle'


class CacheKey:
    """Helper class for generating and parsing cache keys."""
    
    KEY_PATTERN = r"^([^_]+)_([^_]+)_([^_]+)(?:_(.+))?$"
    
    @staticmethod
    def generate(video_id: str, language: str, source: str, **kwargs) -> str:
        """
        Generate a cache key from components.
        
        Args:
            video_id: YouTube video ID
            language: Caption language code
            source: Caption source (e.g., 'manual', 'auto')
            **kwargs: Additional parameters to include in the key
            
        Returns:
            A string key in the format "video_id_language_source_param1=val1_param2=val2"
        """
        base_key = f"{video_id}_{language}_{source}"
        if not kwargs:
            return base_key
            
        params = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        return f"{base_key}_{params}" if params else base_key
    
    @staticmethod
    def parse(key: str) -> Dict[str, str]:
        """
        Parse a cache key into its components.
        
        Args:
            key: Cache key string
            
        Returns:
            Dictionary with 'video_id', 'language', 'source', and any additional parameters
        """
        match = re.match(CacheKey.KEY_PATTERN, key)
        if not match:
            raise ValueError(f"Invalid cache key format: {key}")
            
        video_id, language, source, params_str = match.groups()
        result = {
            "video_id": video_id,
            "language": language,
            "source": source
        }
        
        if params_str:
            for param in params_str.split("_"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    result[k] = v
                    
        return result


class CaptionCache:
    """
    Caching system for YouTube captions.
    
    Provides methods to store, retrieve, and manage cached captions.
    """
    
    def __init__(self, cache_dir: str, config: Optional[CacheConfig] = None, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the caption cache.
        
        Args:
            cache_dir: Directory to store cached captions
            config: Cache configuration (or None for defaults)
            logger: Logger instance (or None to create a new one)
        """
        self.cache_dir = Path(cache_dir) / "caption_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or CacheConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.stores = 0
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(str(self.cache_dir)) and self.config.enabled:
            try:
                os.makedirs(str(self.cache_dir), exist_ok=True)
                self.logger.info(f"Created cache directory: {self.cache_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create cache directory: {e}")
                self.config.enabled = False
        
        # Perform initial cache cleanup if needed
        if self.config.auto_clean:
            self._clean_if_needed()
    
    def get(self, video_id: str, language: str, source: str, 
            **kwargs) -> Optional[Caption]:
        """
        Retrieve a caption from the cache if available.
        
        Args:
            video_id: YouTube video ID
            language: Caption language code
            source: Caption source (e.g., 'manual', 'auto')
            **kwargs: Additional key parameters
            
        Returns:
            Caption object if found and valid, None otherwise
        """
        if not self.config.enabled:
            self.misses += 1
            return None
            
        # Handle "auto_generated" vs "automatic" source type conversion for backward compatibility
        if source == "auto_generated":
            source = "automatic"
            
        key = CacheKey.generate(video_id, language, source, **kwargs)
        filepath = self.cache_dir / f"{key}.{self.config.format}"
        
        if not filepath.exists():
            self.logger.debug(f"Cache miss for key: {key}")
            self.misses += 1
            return None
            
        try:
            # Check if the file is expired
            stats = filepath.stat()
            file_mtime = stats.st_mtime
            file_age = time.time() - file_mtime
            
            if self.config.max_age > 0 and file_age > self.config.max_age:
                self.logger.debug(f"Cache entry expired: {key}")
                self.misses += 1
                return None
                
            # Load the cache entry
            with open(filepath, 'r' if self.config.format == 'json' else 'rb') as f:
                if self.config.format == 'json':
                    data = json.load(f)
                else:
                    data = pickle.load(f)
                    
            # Check explicit expiration if present
            if 'expires_at' in data:
                expires_at = datetime.fromisoformat(data['expires_at'])
                if datetime.now() > expires_at:
                    self.logger.debug(f"Cache entry explicitly expired: {key}")
                    self.misses += 1
                    return None
            
            # Create Caption object
            caption = Caption.from_dict(data)
            
            # Update access time if refresh_on_access is enabled
            if self.config.refresh_on_access:
                os.utime(str(filepath), None)  # Update modification time
                
            self.logger.debug(f"Cache hit for key: {key}")
            self.hits += 1
            return caption
            
        except Exception as e:
            self.logger.warning(f"Error retrieving from cache: {e}")
            self.misses += 1
            return None
    
    def store(self, caption: Caption, source: str = None, 
             expires: Optional[datetime] = None, **kwargs) -> bool:
        """
        Store a caption in the cache.
        
        Args:
            caption: Caption object to store
            source: Caption source (default: from metadata or 'unknown')
            expires: Explicit expiration datetime
            **kwargs: Additional key parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config.enabled:
            return False
            
        # Get source from caption metadata if not provided
        if source is None:
            source = getattr(caption.metadata, 'caption_type', 'unknown')
        
        # Handle "auto_generated" vs "automatic" source type conversion for backward compatibility
        if source == "auto_generated":
            source = "automatic"
        
        # Get video_id and language_code from caption metadata
        video_id = caption.metadata.video_id
        language = caption.metadata.language_code
            
        key = CacheKey.generate(video_id, language, source, **kwargs)
        filepath = self.cache_dir / f"{key}.{self.config.format}"
        
        try:
            # Prepare data for storage
            data = caption.to_dict()
            
            # Add explicit expiration if provided
            if expires is not None:
                data['expires_at'] = expires.isoformat()
                
            # Store the caption
            with open(filepath, 'w' if self.config.format == 'json' else 'wb') as f:
                if self.config.format == 'json':
                    json.dump(data, f, indent=2)
                else:
                    pickle.dump(data, f)
                    
            self.logger.debug(f"Stored in cache: {key}")
            self.stores += 1
            
            # Check and clean cache if needed
            if self.config.auto_clean:
                self._clean_if_needed()
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Error storing in cache: {e}")
            return False
    
    def invalidate(self, video_id: str, language: Optional[str] = None, 
                  source: Optional[str] = None) -> int:
        """
        Remove entries from the cache that match the given criteria.
        
        Args:
            video_id: YouTube video ID to match
            language: Optional language to match
            source: Optional source to match
            
        Returns:
            Number of cache entries removed
        """
        if not self.config.enabled:
            return 0
            
        # Handle "auto_generated" vs "automatic" source type conversion for backward compatibility
        if source == "auto_generated":
            source = "automatic"
            
        pattern = f"{video_id}"
        if language is not None:
            pattern += f"_{language}"
            if source is not None:
                pattern += f"_{source}"
        elif source is not None:
            pattern += f"_*_{source}"
        else:
            pattern += "_*"
            
        pattern = str(self.cache_dir / f"{pattern}*.{self.config.format}")
        files = glob.glob(pattern)
        
        count = 0
        for filepath in files:
            try:
                os.remove(filepath)
                count += 1
            except Exception as e:
                self.logger.warning(f"Error removing cache file {filepath}: {e}")
                
        if count > 0:
            self.logger.info(f"Invalidated {count} cache entries for video {video_id}")
            
        return count
    
    def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.config.enabled:
            return False
            
        try:
            pattern = str(self.cache_dir / f"*.{self.config.format}")
            files = glob.glob(pattern)
            
            for filepath in files:
                try:
                    os.remove(filepath)
                except Exception as e:
                    self.logger.warning(f"Error removing cache file {filepath}: {e}")
            
            self.logger.info(f"Cleared {len(files)} cache entries")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'hits': self.hits,
            'misses': self.misses,
            'stores': self.stores,
            'hit_ratio': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            'enabled': self.config.enabled,
            'config': asdict(self.config)
        }
        
        if not self.config.enabled:
            return stats
            
        try:
            # Calculate cache size
            pattern = str(self.cache_dir / f"*.{self.config.format}")
            files = glob.glob(pattern)
            
            total_size = 0
            for filepath in files:
                total_size += os.path.getsize(filepath)
                
            stats.update({
                'entries': len(files),
                'size_bytes': total_size,
                'size_mb': total_size / (1024 * 1024)
            })
            
        except Exception as e:
            self.logger.warning(f"Error calculating cache stats: {e}")
            
        return stats
    
    def _clean_if_needed(self) -> None:
        """Clean the cache if it exceeds the configured size limit."""
        if not self.config.auto_clean or self.config.max_size <= 0:
            return
            
        try:
            # Calculate current cache size
            pattern = str(self.cache_dir / f"*.{self.config.format}")
            files = []
            total_size = 0
            
            for filepath in glob.glob(pattern):
                try:
                    size = os.path.getsize(filepath)
                    mtime = os.path.getmtime(filepath)
                    files.append((filepath, size, mtime))
                    total_size += size
                except Exception as e:
                    self.logger.warning(f"Error getting file stats for {filepath}: {e}")
                
            # If cache size exceeds limit, remove oldest files
            if total_size > self.config.max_size and len(files) > self.config.min_entries:
                # Sort by modification time (oldest first)
                files.sort(key=lambda x: x[2])
                
                # Keep removing until we're under the limit or reach min_entries
                files_to_remove = files[:-self.config.min_entries] if len(files) > self.config.min_entries else []
                removed_count = 0
                removed_size = 0
                
                for filepath, size, _ in files_to_remove:
                    if total_size - removed_size <= self.config.max_size:
                        break
                        
                    try:
                        os.remove(filepath)
                        removed_size += size
                        removed_count += 1
                    except Exception as e:
                        self.logger.warning(f"Error removing cache file {filepath}: {e}")
                
                if removed_count > 0:
                    self.logger.info(
                        f"Cleaned {removed_count} cache entries ({removed_size / (1024 * 1024):.2f} MB)"
                    )
                    
        except Exception as e:
            self.logger.warning(f"Error during cache cleaning: {e}") 