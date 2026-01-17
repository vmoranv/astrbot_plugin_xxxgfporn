"""
XXXGFPORN API Image Utilities
Handles image downloading, caching and optional mosaic/blur
"""

import os
import hashlib
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageFilter
from io import BytesIO


class ImageProcessor:
    """
    Image processor for downloading and processing images
    Supports caching and optional mosaic/blur effects
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        mosaic_level: int = 0,
        proxy: Optional[str] = None
    ):
        """
        Initialize ImageProcessor
        
        Args:
            cache_dir: Directory for caching images
            mosaic_level: Mosaic/blur intensity (0=none, 1=light, 2=medium, 3=heavy)
            proxy: Optional proxy URL
        """
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._mosaic_level = mosaic_level
        self._proxy = proxy
        
        # Create cache directory if needed
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def cache_dir(self) -> Optional[Path]:
        return self._cache_dir
    
    @cache_dir.setter
    def cache_dir(self, value: str) -> None:
        self._cache_dir = Path(value)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def mosaic_level(self) -> int:
        return self._mosaic_level
    
    @mosaic_level.setter
    def mosaic_level(self, value: int) -> None:
        self._mosaic_level = max(0, min(3, value))
    
    def _get_cache_path(self, url: str) -> Optional[Path]:
        """Get cache file path for URL"""
        if not self._cache_dir:
            return None
        
        # Generate hash from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self._cache_dir / f"{url_hash}.jpg"
    
    def _check_cache(self, url: str) -> Optional[str]:
        """Check if image is cached and return path"""
        cache_path = self._get_cache_path(url)
        if cache_path and cache_path.exists():
            return str(cache_path)
        return None
    
    async def download_image(
        self,
        url: str,
        timeout: int = 30
    ) -> Optional[bytes]:
        """
        Download image from URL
        
        Args:
            url: Image URL
            timeout: Request timeout
            
        Returns:
            Image bytes or None
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.xxxgfporn.com/",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    proxy=self._proxy,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    allow_redirects=True
                ) as response:
                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        if "image" in content_type or not content_type:
                            return await response.read()
        except aiohttp.ClientError:
            pass
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass
        return None
    
    def apply_mosaic(
        self,
        image_bytes: bytes,
        level: Optional[int] = None
    ) -> bytes:
        """
        Apply mosaic/blur effect to image
        
        Args:
            image_bytes: Original image bytes
            level: Mosaic level (overrides instance setting)
            
        Returns:
            Processed image bytes
        """
        level = level if level is not None else self._mosaic_level
        
        if level <= 0:
            return image_bytes
        
        try:
            # Open image
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate blur radius based on level
            # Level 1: light (radius 5)
            # Level 2: medium (radius 15)
            # Level 3: heavy (radius 30)
            blur_radius = {1: 5, 2: 15, 3: 30}.get(level, 10)
            
            # Apply Gaussian blur
            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            # For level 3, also apply pixelation
            if level >= 3:
                # Reduce size and scale back up for pixelation effect
                original_size = img.size
                small_size = (max(1, original_size[0] // 20), max(1, original_size[1] // 20))
                img = img.resize(small_size, Image.Resampling.NEAREST)
                img = img.resize(original_size, Image.Resampling.NEAREST)
            
            # Save to bytes
            output = BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception:
            # Return original if processing fails
            return image_bytes
    
    async def get_image(
        self,
        url: str,
        use_cache: bool = True,
        apply_mosaic: bool = True
    ) -> Tuple[Optional[str], bool]:
        """
        Get image, download if needed, apply mosaic, cache result
        
        Args:
            url: Image URL
            use_cache: Whether to use cache
            apply_mosaic: Whether to apply mosaic effect
            
        Returns:
            Tuple of (file_path, is_from_cache)
        """
        # Check cache first
        if use_cache:
            cached_path = self._check_cache(url)
            if cached_path:
                return cached_path, True
        
        # Download image
        image_bytes = await self.download_image(url)
        if not image_bytes:
            return None, False
        
        # Apply mosaic if enabled
        if apply_mosaic and self._mosaic_level > 0:
            image_bytes = self.apply_mosaic(image_bytes)
        
        # Save to cache
        if self._cache_dir:
            cache_path = self._get_cache_path(url)
            if cache_path:
                with open(cache_path, 'wb') as f:
                    f.write(image_bytes)
                return str(cache_path), False
        
        # Save to temp file if no cache dir
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(image_bytes)
            return f.name, False
    
    def cleanup_cache(self, max_files: int = 100) -> int:
        """
        Clean up old cached files
        
        Args:
            max_files: Maximum number of files to keep
            
        Returns:
            Number of files deleted
        """
        if not self._cache_dir or not self._cache_dir.exists():
            return 0
        
        # Get all cache files sorted by modification time
        files = list(self._cache_dir.glob("*.jpg"))
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Delete old files
        deleted = 0
        for file in files[max_files:]:
            try:
                file.unlink()
                deleted += 1
            except Exception:
                pass
        
        return deleted
    
    def clear_cache(self) -> int:
        """
        Clear all cached files
        
        Returns:
            Number of files deleted
        """
        if not self._cache_dir or not self._cache_dir.exists():
            return 0
        
        deleted = 0
        for file in self._cache_dir.glob("*.jpg"):
            try:
                file.unlink()
                deleted += 1
            except Exception:
                pass
        
        return deleted