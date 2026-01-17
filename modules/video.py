"""
XXXGFPORN API Video Class
Handles video information extraction and parsing
"""

import re
import json
import html
from typing import Optional, List, Dict, Any
from functools import cached_property
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .consts import (
    ROOT_URL, VIDEO_URL,
    REGEX_VIDEO_ID, REGEX_VIDEO_ID_ALT,
    REGEX_VIDEO_TITLE, REGEX_VIDEO_TITLE_ALT,
    REGEX_VIDEO_DURATION, REGEX_VIDEO_DURATION_ALT,
    REGEX_VIDEO_VIEWS, REGEX_VIDEO_VIEWS_ALT,
    REGEX_VIDEO_RATING, REGEX_VIDEO_LIKES, REGEX_VIDEO_DISLIKES,
    REGEX_VIDEO_UPLOADER, REGEX_VIDEO_UPLOAD_DATE,
    REGEX_VIDEO_CATEGORIES, REGEX_VIDEO_TAGS,
    REGEX_VIDEO_THUMBNAIL, REGEX_VIDEO_THUMBNAIL_ALT, REGEX_VIDEO_PREVIEW,
    REGEX_VIDEO_SOURCE, REGEX_VIDEO_SOURCE_ALT,
    REGEX_JSON_LD
)
from .errors import (
    InvalidURL, VideoNotFound, VideoDisabled, ParseError, InvalidVideoID
)


class Video:
    """
    Video class for parsing and extracting video information from XXXGFPORN
    """
    
    def __init__(self, video_id: str, client: Optional[Any] = None, url: Optional[str] = None):
        """
        Initialize Video object
        
        Args:
            video_id: Video ID (numeric string or slug)
            client: Optional Client instance for HTTP requests
            url: Optional full URL (if provided, used instead of constructing from ID)
        """
        self._video_id = str(video_id).strip()
        self._client = client
        self._html_content: Optional[str] = None
        self._json_ld_data: Optional[Dict] = None
        self._soup: Optional[BeautifulSoup] = None
        self._custom_url = url  # Store custom URL if provided
        
        # Validate video ID - accept both numeric and slug formats
        if not self._video_id:
            raise InvalidVideoID(f"Invalid video ID: {video_id}")
        
        # If video_id looks like a URL, try to extract the ID/slug
        if '/' in self._video_id or 'http' in self._video_id.lower():
            extracted = self._extract_id_from_url(self._video_id)
            if extracted:
                self._video_id = extracted
            else:
                # Use the last path segment as ID
                parts = self._video_id.rstrip('/').split('/')
                self._video_id = parts[-1] if parts else self._video_id
    
    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Extract video ID from URL"""
        match = REGEX_VIDEO_ID.search(url)
        if match:
            return match.group(1)
        match = REGEX_VIDEO_ID_ALT.search(url)
        if match:
            return match.group(1)
        return None
    
    @property
    def video_id(self) -> str:
        """Get video ID (cleaned numeric ID if possible)"""
        vid = self._video_id
        
        # Remove .html suffix if present
        if vid.endswith('.html'):
            vid = vid[:-5]
        
        # If already numeric, return as is
        if vid.isdigit():
            return vid
        
        # Try to extract numeric ID from end of slug (e.g., "some-title-12345" -> "12345")
        match = re.search(r'-(\d+)$', vid)
        if match:
            return match.group(1)
        
        # Return cleaned slug if no numeric ID found
        return vid
    
    @property
    def url(self) -> str:
        """Get full video URL"""
        if self._custom_url:
            return self._custom_url
        # For numeric IDs, use standard format
        if self._video_id.isdigit():
            return f"{VIDEO_URL}{self._video_id}/"
        # For slug-based IDs, construct URL differently
        return f"{ROOT_URL}/{self._video_id}/"
    
    async def fetch(self) -> None:
        """Fetch video page HTML content"""
        if self._client is None:
            raise ValueError("Client is required to fetch video content")
        
        self._html_content = await self._client.fetch(self.url)
        if not self._html_content:
            raise VideoNotFound(f"Video not found: {self._video_id}")
        
        # Check if video is disabled/removed
        if "video has been removed" in self._html_content.lower() or \
           "video not found" in self._html_content.lower() or \
           "404" in self._html_content[:500]:
            raise VideoDisabled(f"Video has been removed: {self._video_id}")
        
        # Parse HTML
        self._html_content = html.unescape(self._html_content)
        self._soup = BeautifulSoup(self._html_content, 'lxml')
        
        # Extract JSON-LD data
        self._extract_json_ld()
    
    def _extract_json_ld(self) -> None:
        """Extract JSON-LD structured data from page"""
        if not self._html_content:
            return
        
        matches = REGEX_JSON_LD.findall(self._html_content)
        for match in matches:
            try:
                data = json.loads(match.strip())
                if isinstance(data, dict):
                    if data.get("@type") == "VideoObject" or "video" in str(data.get("@type", "")).lower():
                        self._json_ld_data = data
                        break
                    # Merge all JSON-LD data
                    if self._json_ld_data is None:
                        self._json_ld_data = {}
                    self._json_ld_data.update(data)
            except json.JSONDecodeError:
                continue
    
    def _search_patterns(self, patterns: List, content: Optional[str] = None) -> Optional[str]:
        """Search multiple regex patterns and return first match"""
        content = content or self._html_content
        if not content:
            return None
        
        for pattern in patterns:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        return None
    
    @cached_property
    def title(self) -> Optional[str]:
        """Get video title"""
        if not self._html_content:
            return None
        
        result = None
        
        # Try JSON-LD first
        if self._json_ld_data and "name" in self._json_ld_data:
            result = self._json_ld_data["name"]
        
        # Try regex patterns
        if not result:
            result = self._search_patterns([REGEX_VIDEO_TITLE, REGEX_VIDEO_TITLE_ALT])
        
        if result:
            # Clean up title - remove website suffix
            result = re.sub(r'\s*[-|–—]\s*(Free\s+)?(Porn\s+)?(Video\s+)?(at\s+)?XXXGFPORN.*$', '', result, flags=re.IGNORECASE)
            result = result.strip()
        
        return result
    
    @cached_property
    def duration(self) -> Optional[str]:
        """Get video duration (format: MM:SS or HH:MM:SS)"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data and "duration" in self._json_ld_data:
            duration = self._json_ld_data["duration"]
            # Convert ISO 8601 duration to HH:MM:SS
            if duration.startswith("PT"):
                duration = duration[2:]
                hours = minutes = seconds = 0
                if "H" in duration:
                    hours, duration = duration.split("H")
                    hours = int(hours)
                if "M" in duration:
                    minutes, duration = duration.split("M")
                    minutes = int(minutes)
                if "S" in duration:
                    seconds = duration.replace("S", "")
                    seconds = int(float(seconds))
                if hours > 0:
                    return f"{hours}:{minutes:02d}:{seconds:02d}"
                return f"{minutes}:{seconds:02d}"
        
        return self._search_patterns([REGEX_VIDEO_DURATION, REGEX_VIDEO_DURATION_ALT])
    
    @cached_property
    def duration_seconds(self) -> Optional[int]:
        """Get video duration in seconds"""
        duration = self.duration
        if not duration:
            return None
        
        parts = duration.split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None
        return None
    
    @cached_property
    def views(self) -> Optional[str]:
        """Get view count as string"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            views = self._json_ld_data.get("interactionCount") or \
                    self._json_ld_data.get("interactionStatistic", {}).get("userInteractionCount")
            if views:
                return str(views)
        
        return self._search_patterns([REGEX_VIDEO_VIEWS, REGEX_VIDEO_VIEWS_ALT])
    
    @cached_property
    def views_count(self) -> Optional[int]:
        """Get view count as integer"""
        views = self.views
        if not views:
            return None
        try:
            return int(views.replace(",", "").replace(" ", ""))
        except ValueError:
            return None
    
    @cached_property
    def rating(self) -> Optional[str]:
        """Get video rating percentage"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            rating = self._json_ld_data.get("aggregateRating", {}).get("ratingValue")
            if rating:
                return f"{rating}%"
        
        return self._search_patterns([REGEX_VIDEO_RATING])
    
    @cached_property
    def likes(self) -> Optional[str]:
        """Get like count"""
        return self._search_patterns([REGEX_VIDEO_LIKES])
    
    @cached_property
    def dislikes(self) -> Optional[str]:
        """Get dislike count"""
        return self._search_patterns([REGEX_VIDEO_DISLIKES])
    
    @cached_property
    def uploader(self) -> Optional[str]:
        """Get uploader name"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            author = self._json_ld_data.get("author")
            if isinstance(author, dict):
                return author.get("name")
            elif isinstance(author, str):
                return author
        
        return self._search_patterns([REGEX_VIDEO_UPLOADER])
    
    @cached_property
    def upload_date(self) -> Optional[str]:
        """Get upload date"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            date = self._json_ld_data.get("uploadDate") or self._json_ld_data.get("datePublished")
            if date:
                return date
        
        return self._search_patterns([REGEX_VIDEO_UPLOAD_DATE])
    
    @cached_property
    def thumbnail(self) -> Optional[str]:
        """Get thumbnail URL"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            thumb = self._json_ld_data.get("thumbnailUrl")
            if isinstance(thumb, list) and thumb:
                return thumb[0]
            elif isinstance(thumb, str):
                return thumb
        
        # Try regex patterns
        result = self._search_patterns([REGEX_VIDEO_THUMBNAIL, REGEX_VIDEO_THUMBNAIL_ALT])
        if result:
            if not result.startswith("http"):
                result = urljoin(ROOT_URL, result)
            return result
        
        # Try og:image meta tag (common fallback)
        if self._soup:
            og_image = self._soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image.get("content")
            
            # Try twitter:image meta tag
            twitter_image = self._soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                return twitter_image.get("content")
            
            # Try video poster attribute
            video_tag = self._soup.find("video")
            if video_tag and video_tag.get("poster"):
                poster = video_tag.get("poster")
                if not poster.startswith("http"):
                    poster = urljoin(ROOT_URL, poster)
                return poster
            
            # Try finding image in player area
            player_div = self._soup.find("div", class_=re.compile(r"player|video-container|video-wrapper", re.I))
            if player_div:
                img = player_div.find("img")
                if img:
                    src = img.get("data-src") or img.get("src")
                    if src and not src.startswith("data:"):
                        if not src.startswith("http"):
                            src = urljoin(ROOT_URL, src)
                        return src
            
            # Try finding any large image (likely thumbnail)
            for img in self._soup.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if not src or src.startswith("data:"):
                    continue
                # Skip small icons and logos
                classes = img.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes)
                else:
                    classes_str = str(classes)
                if any(x in classes_str.lower() for x in ["icon", "logo", "avatar", "ad"]):
                    continue
                # Check for common thumbnail indicators
                if any(x in src.lower() for x in ["thumb", "poster", "preview", "player"]):
                    if not src.startswith("http"):
                        src = urljoin(ROOT_URL, src)
                    return src
        
        return None
    
    @cached_property
    def preview(self) -> Optional[str]:
        """Get video preview URL (animated/gif)"""
        result = self._search_patterns([REGEX_VIDEO_PREVIEW])
        if result and not result.startswith("http"):
            result = urljoin(ROOT_URL, result)
        return result
    
    @cached_property
    def categories(self) -> List[str]:
        """Get video categories"""
        if not self._html_content:
            return []
        
        matches = REGEX_VIDEO_CATEGORIES.findall(self._html_content)
        return list(set(cat.strip() for cat in matches if cat.strip()))
    
    @cached_property
    def tags(self) -> List[str]:
        """Get video tags"""
        if not self._html_content:
            return []
        
        # Try JSON-LD first
        if self._json_ld_data:
            keywords = self._json_ld_data.get("keywords")
            if isinstance(keywords, str):
                return [tag.strip() for tag in keywords.split(",")]
            elif isinstance(keywords, list):
                return keywords
        
        matches = REGEX_VIDEO_TAGS.findall(self._html_content)
        return list(set(tag.strip() for tag in matches if tag.strip()))
    
    @cached_property
    def source_url(self) -> Optional[str]:
        """Get direct video source URL"""
        if not self._html_content:
            return None
        
        # Try JSON-LD first
        if self._json_ld_data:
            content_url = self._json_ld_data.get("contentUrl")
            if content_url:
                return content_url
        
        result = self._search_patterns([REGEX_VIDEO_SOURCE, REGEX_VIDEO_SOURCE_ALT])
        if result and not result.startswith("http"):
            result = urljoin(ROOT_URL, result)
        return result
    
    @cached_property
    def description(self) -> Optional[str]:
        """Get video description"""
        if self._json_ld_data:
            return self._json_ld_data.get("description")
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert video info to dictionary"""
        return {
            "video_id": self.video_id,
            "url": self.url,
            "title": self.title,
            "duration": self.duration,
            "duration_seconds": self.duration_seconds,
            "views": self.views,
            "views_count": self.views_count,
            "rating": self.rating,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "uploader": self.uploader,
            "upload_date": self.upload_date,
            "thumbnail": self.thumbnail,
            "preview": self.preview,
            "categories": self.categories,
            "tags": self.tags,
            "source_url": self.source_url,
            "description": self.description,
        }
    
    def __repr__(self) -> str:
        return f"Video(id={self.video_id}, title={self.title})"
    
    def __str__(self) -> str:
        return f"{self.title or 'Unknown'} ({self.video_id})"