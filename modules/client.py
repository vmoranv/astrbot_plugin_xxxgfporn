"""
XXXGFPORN API Client
Handles HTTP requests and session management
"""

import re
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any, AsyncGenerator
from urllib.parse import urljoin, urlencode
from bs4 import BeautifulSoup

from .consts import (
    ROOT_URL, VIDEO_URL, CATEGORY_URL, SEARCH_URL,
    DEFAULT_HEADERS,
    REGEX_VIDEO_LIST_ITEM, REGEX_PAGINATION_LAST, REGEX_PAGINATION_NEXT,
    Category, SortOrder, TimeFilter
)
from .errors import (
    NetworkError, ParseError, SearchError, RateLimitError, ProxyError
)
from .video import Video


class Client:
    """
    Async HTTP Client for XXXGFPORN API
    Handles all network requests and video listing
    """
    
    def __init__(
        self,
        proxy: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Client
        
        Args:
            proxy: Optional proxy URL (e.g., "http://127.0.0.1:7890")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            headers: Optional custom headers
        """
        self._proxy = proxy
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
                headers=self._headers,
                trust_env=True
            )
        return self._session
    
    async def close(self) -> None:
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        allow_redirects: bool = True
    ) -> str:
        """
        Fetch URL content
        
        Args:
            url: URL to fetch
            method: HTTP method
            data: Optional POST data
            allow_redirects: Allow redirects
            
        Returns:
            Response text content
        """
        session = await self._ensure_session()
        
        for attempt in range(self._max_retries):
            try:
                async with session.request(
                    method,
                    url,
                    data=data,
                    proxy=self._proxy,
                    allow_redirects=allow_redirects
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("Rate limited by server")
                    if response.status == 404:
                        return ""
                    response.raise_for_status()
                    return await response.text()
                    
            except aiohttp.ClientProxyConnectionError as e:
                raise ProxyError(f"Proxy connection failed: {e}")
            except aiohttp.ClientError as e:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise NetworkError(f"Network request failed: {e}")
            except asyncio.TimeoutError:
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise NetworkError(f"Request timeout for {url}")
        
        raise NetworkError(f"Max retries exceeded for {url}")
    
    async def get_video(self, video_id_or_url: str) -> Video:
        """
        Get video information by ID or URL
        
        Args:
            video_id_or_url: Video ID (numeric string) or full URL
            
        Returns:
            Video object with parsed information
        """
        # If it's a full URL, pass it directly
        if video_id_or_url.startswith('http'):
            video = Video(video_id_or_url, client=self, url=video_id_or_url)
        else:
            video = Video(video_id_or_url, client=self)
        await video.fetch()
        return video
    
    async def search(
        self,
        query: str,
        page: int = 1,
        sort: str = SortOrder.NEWEST,
        time_filter: str = TimeFilter.ALL_TIME
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Search for videos
        
        Args:
            query: Search query
            page: Page number
            sort: Sort order
            time_filter: Time filter
            
        Yields:
            Video info dictionaries
        """
        # Build search URL - try path-based format first
        # Format: /search/keyword/ or /search/keyword/page/
        from urllib.parse import quote
        encoded_query = quote(query.strip())
        
        if page > 1:
            url = f"{SEARCH_URL}{encoded_query}/{page}/"
        else:
            url = f"{SEARCH_URL}{encoded_query}/"
        
        # Add sort/time params if needed
        params = {}
        if sort != SortOrder.NEWEST:
            params["sort"] = sort
        if time_filter != TimeFilter.ALL_TIME:
            params["time"] = time_filter
        if params:
            url = f"{url}?{urlencode(params)}"
        
        html_content = await self.fetch(url)
        if not html_content:
            # Fallback: try query parameter format
            params = {
                "q": query,
                "page": page,
                "sort": sort,
                "time": time_filter
            }
            url = f"{SEARCH_URL}?{urlencode(params)}"
            html_content = await self.fetch(url)
            if not html_content:
                return
        
        # Parse video list
        async for video_info in self._parse_video_list(html_content):
            yield video_info
    
    async def get_category_videos(
        self,
        category: str,
        page: int = 1,
        sort: str = SortOrder.NEWEST
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get videos from a category (uses search as fallback since category pages may not exist)
        
        Args:
            category: Category name/slug
            page: Page number
            sort: Sort order
            
        Yields:
            Video info dictionaries
        """
        # First try category URL
        url = f"{CATEGORY_URL}{category}/"
        if page > 1:
            url = f"{url}{page}/"
        if sort != SortOrder.NEWEST:
            url = f"{url}?sort={sort}"
        
        html_content = await self.fetch(url)
        
        # If category page doesn't exist (404), fall back to search
        if not html_content:
            # Use search as fallback - category pages may return 404
            from urllib.parse import quote
            encoded_category = quote(category.strip())
            
            if page > 1:
                url = f"{SEARCH_URL}{encoded_category}/{page}/"
            else:
                url = f"{SEARCH_URL}{encoded_category}/"
            
            if sort != SortOrder.NEWEST:
                url = f"{url}?sort={sort}"
            
            html_content = await self.fetch(url)
            if not html_content:
                return
        
        async for video_info in self._parse_video_list(html_content):
            yield video_info
    
    async def get_latest_videos(
        self,
        page: int = 1
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get latest videos from homepage
        
        Args:
            page: Page number
            
        Yields:
            Video info dictionaries
        """
        url = ROOT_URL
        if page > 1:
            url = f"{ROOT_URL}/latest/{page}/"
        
        html_content = await self.fetch(url)
        if not html_content:
            return
        
        async for video_info in self._parse_video_list(html_content):
            yield video_info
    
    async def get_popular_videos(
        self,
        page: int = 1,
        time_filter: str = TimeFilter.ALL_TIME
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get popular/most viewed videos
        
        Args:
            page: Page number
            time_filter: Time filter
            
        Yields:
            Video info dictionaries
        """
        url = f"{ROOT_URL}/most-viewed/"
        if page > 1:
            url = f"{url}{page}/"
        if time_filter != TimeFilter.ALL_TIME:
            url = f"{url}?time={time_filter}"
        
        html_content = await self.fetch(url)
        if not html_content:
            return
        
        async for video_info in self._parse_video_list(html_content):
            yield video_info
    
    async def get_top_rated_videos(
        self,
        page: int = 1,
        time_filter: str = TimeFilter.ALL_TIME
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get top rated videos
        
        Args:
            page: Page number
            time_filter: Time filter
            
        Yields:
            Video info dictionaries
        """
        url = f"{ROOT_URL}/top-rated/"
        if page > 1:
            url = f"{url}{page}/"
        if time_filter != TimeFilter.ALL_TIME:
            url = f"{url}?time={time_filter}"
        
        html_content = await self.fetch(url)
        if not html_content:
            return
        
        async for video_info in self._parse_video_list(html_content):
            yield video_info
    
    async def get_random_video(self) -> Optional[Video]:
        """
        Get a random video by fetching from different sources and randomly selecting one.
        
        This method collects videos from various pages and uses Python's random module
        to ensure true randomness, as the website's /random/ page may be cached.
        
        Returns:
            Random Video object or None
        """
        import random
        
        # Collect videos from different sources for better randomness
        all_videos = []
        
        # Choose a random source and page
        sources = [
            (ROOT_URL, "homepage"),
            (f"{ROOT_URL}/most-viewed/", "popular"),
            (f"{ROOT_URL}/top-rated/", "top-rated"),
        ]
        
        # Add random page numbers to sources
        random_page = random.randint(1, 10)
        sources.extend([
            (f"{ROOT_URL}/latest/{random_page}/", f"latest-page-{random_page}"),
            (f"{ROOT_URL}/most-viewed/{random.randint(1, 10)}/", "popular-random-page"),
        ])
        
        # Shuffle sources and try to get videos
        random.shuffle(sources)
        
        for url, source_name in sources[:3]:  # Try up to 3 sources
            try:
                html_content = await self.fetch(url)
                if not html_content:
                    continue
                
                async for video_info in self._parse_video_list(html_content):
                    if video_info.get("video_id") or video_info.get("url"):
                        all_videos.append(video_info)
                        # Stop after collecting 30 videos for performance
                        if len(all_videos) >= 30:
                            break
                
                # If we have enough videos, stop fetching more sources
                if len(all_videos) >= 15:
                    break
                    
            except Exception:
                continue
        
        if not all_videos:
            return None
        
        # Randomly select a video from collected list
        selected = random.choice(all_videos)
        
        # Use URL if available, otherwise fall back to ID
        video_url = selected.get("url")
        if video_url:
            return await self.get_video(video_url)
        elif selected.get("video_id"):
            return await self.get_video(selected["video_id"])
        
        return None
    
    async def get_categories(self) -> List[Dict[str, str]]:
        """
        Get list of all categories
        
        Returns:
            List of category dictionaries with name and url
        """
        html_content = await self.fetch(f"{ROOT_URL}/categories/")
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        categories = []
        
        # Find category links
        for a_tag in soup.find_all('a', href=re.compile(r'/categor[yi]')):
            href = a_tag.get('href', '')
            name = a_tag.get_text(strip=True)
            if name and href:
                # Extract category slug
                slug_match = re.search(r'/categor[yi]/([^/]+)', href)
                if slug_match:
                    categories.append({
                        "name": name,
                        "slug": slug_match.group(1),
                        "url": urljoin(ROOT_URL, href)
                    })
        
        return categories
    
    async def _parse_video_list(
        self,
        html_content: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Parse video list from HTML content
        
        Args:
            html_content: HTML page content
            
        Yields:
            Video info dictionaries
        """
        soup = BeautifulSoup(html_content, 'lxml')
        found_videos = False
        
        # Known category/tag slugs to exclude globally
        excluded_slugs = {
            'amateur', 'anal', 'asian', 'bbw', 'big-tits', 'blonde', 'blowjob',
            'brunette', 'creampie', 'cumshot', 'hardcore', 'lesbian', 'mature',
            'milf', 'teen', 'threesome', 'categories', 'tags', 'channels',
            'pornstars', 'popular', 'latest', 'top-rated', 'most-viewed',
            'random', 'search', 'login', 'register', 'contact', 'privacy',
            'terms', 'dmca', '2257', 'about', 'girlfriend', 'homemade', 'pov',
            'interracial', 'redhead', 'ebony', 'latina', 'category', 'tag'
        }
        
        seen_video_ids = set()
        
        # Strategy 1: Find video containers with common class patterns
        video_containers = (
            soup.find_all('div', class_=re.compile(r'video[_-]?item|thumb|vid-item|video-block|item', re.I)) or
            soup.find_all('article', class_=re.compile(r'video|thumb|item', re.I)) or
            soup.find_all('li', class_=re.compile(r'video|thumb|item', re.I)) or
            soup.find_all('div', class_=re.compile(r'col-|grid-item|card', re.I))
        )
        
        for container in video_containers:
            try:
                video_info = self._extract_video_info_from_container(container)
                if video_info and video_info.get("video_id"):
                    vid = video_info["video_id"]
                    # Skip duplicates and excluded slugs
                    if vid in seen_video_ids or vid.lower() in excluded_slugs:
                        continue
                    seen_video_ids.add(vid)
                    found_videos = True
                    yield video_info
            except Exception:
                continue
        
        # Strategy 2: Find all links that match video URL patterns (various formats)
        if not found_videos:
            # Try multiple video URL patterns
            video_patterns = [
                r'/video/\d+',           # /video/12345/
                r'/videos/[^/]+',        # /videos/slug-name/
                r'/watch/[^/]+',         # /watch/slug-name/
                r'/v/[^/]+',             # /v/slug/
            ]
            
            video_links = []
            for pattern in video_patterns:
                video_links = soup.find_all('a', href=re.compile(pattern))
                if video_links:
                    break
            
            # If still not found, try finding links in video containers
            if not video_links:
                containers = soup.find_all(['div', 'article', 'li'],
                                           class_=re.compile(r'video|thumb|item|post', re.I))
                for container in containers:
                    links = container.find_all('a', href=True)
                    video_links.extend(links)
            
            for link in video_links:
                try:
                    href = link.get('href', '')
                    if not href or href in ['#', '/']:
                        continue
                    
                    # Skip navigation/category links
                    if any(x in href.lower() for x in ['/category', '/tag', '/search',
                                                        '/page/', 'javascript:',
                                                        '/login', '/register', '/categories/',
                                                        '/tags/', '/pornstars/', '/channels/']):
                        continue
                    
                    full_url = urljoin(ROOT_URL, href)
                    
                    # Extract video ID from URL
                    video_id = None
                    
                    # Try numeric ID first: /video/12345/
                    id_match = re.search(r'/video/(\d+)/?$', href)
                    if id_match:
                        video_id = id_match.group(1)
                    else:
                        # Try slug format: /video/slug-name-12345.html
                        slug_match = re.search(r'/video/([^/]+?)(?:\.html)?/?$', href)
                        if slug_match:
                            slug = slug_match.group(1)
                            # Extract numeric ID from end of slug if present
                            num_match = re.search(r'-(\d+)$', slug)
                            if num_match:
                                video_id = num_match.group(1)
                            elif slug.lower() not in excluded_slugs:
                                # Use full slug as ID if no numeric ID
                                video_id = slug
                    
                    if not video_id:
                        continue
                    
                    # Skip if ID looks like a category slug or already seen
                    if video_id.lower() in excluded_slugs or video_id in seen_video_ids:
                        continue
                    seen_video_ids.add(video_id)
                    
                    video_info = {
                        "video_id": video_id,
                        "url": full_url
                    }
                    
                    # Try to find thumbnail and title in parent
                    parent = link.find_parent(['div', 'article', 'li', 'section'])
                    if parent:
                        img = parent.find('img')
                        if img:
                            src = img.get('data-src') or img.get('src') or img.get('data-lazy-src')
                            if src and not src.startswith('data:'):
                                video_info['thumbnail'] = urljoin(ROOT_URL, src)
                        
                        # Try to find title
                        title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'span', 'p'],
                                                 class_=re.compile(r'title|name', re.I))
                        if title_elem:
                            video_info['title'] = title_elem.get_text(strip=True)
                        elif link.get('title'):
                            video_info['title'] = link.get('title')
                        elif link.get_text(strip=True):
                            video_info['title'] = link.get_text(strip=True)
                    
                    found_videos = True
                    yield video_info
                except Exception:
                    continue
        
        # Strategy 3: Fallback to regex pattern
        if not found_videos:
            matches = REGEX_VIDEO_LIST_ITEM.findall(html_content)
            for match in matches:
                try:
                    url, thumbnail, title = match
                    video_id_match = re.search(r'/video/(\d+)', url)
                    if video_id_match:
                        yield {
                            "video_id": video_id_match.group(1),
                            "url": urljoin(ROOT_URL, url),
                            "thumbnail": urljoin(ROOT_URL, thumbnail) if thumbnail else None,
                            "title": title.strip() if title else None
                        }
                        found_videos = True
                except Exception:
                    continue
        
        # Strategy 4: Try to find any video ID patterns in the HTML
        if not found_videos:
            # Look for video IDs in any href or data attributes
            all_video_ids = re.findall(r'/video/(\d+)', html_content)
            seen_ids = set()
            for video_id in all_video_ids:
                if video_id not in seen_ids:
                    seen_ids.add(video_id)
                    yield {
                        "video_id": video_id,
                        "url": f"{VIDEO_URL}{video_id}/"
                    }
    
    def _extract_video_info_from_container(
        self,
        container: BeautifulSoup
    ) -> Optional[Dict[str, Any]]:
        """
        Extract video info from a container element
        
        Args:
            container: BeautifulSoup element
            
        Returns:
            Video info dictionary or None
        """
        video_info = {}
        
        # Find link
        link = container.find('a', href=re.compile(r'/video/'))
        if link:
            href = link.get('href', '')
            video_info['url'] = urljoin(ROOT_URL, href)
            
            # Extract video ID from various URL formats
            # Format 1: /video/12345/
            # Format 2: /video/slug-name-12345.html
            id_match = re.search(r'/video/(\d+)/?$', href)
            if id_match:
                video_info['video_id'] = id_match.group(1)
            else:
                # Try slug format: /video/slug-name-12345.html
                slug_match = re.search(r'/video/([^/]+?)(?:\.html)?/?$', href)
                if slug_match:
                    slug = slug_match.group(1)
                    # Extract numeric ID from end of slug if present
                    num_match = re.search(r'-(\d+)$', slug)
                    if num_match:
                        video_info['video_id'] = num_match.group(1)
                    else:
                        # Use full slug as ID
                        video_info['video_id'] = slug
        
        if not video_info.get('video_id'):
            return None
        
        # Find thumbnail
        img = container.find('img')
        if img:
            src = img.get('data-src') or img.get('src') or img.get('data-lazy-src')
            if src:
                video_info['thumbnail'] = urljoin(ROOT_URL, src)
            
            # Try to get preview
            preview = img.get('data-preview') or img.get('data-gif')
            if preview:
                video_info['preview'] = urljoin(ROOT_URL, preview)
        
        # Find title
        title_elem = (
            container.find(class_=re.compile(r'title', re.I)) or
            container.find(['h1', 'h2', 'h3', 'h4', 'span'], class_=re.compile(r'name|title', re.I)) or
            link
        )
        if title_elem:
            video_info['title'] = title_elem.get_text(strip=True)
        
        # Find duration
        duration_elem = container.find(class_=re.compile(r'duration|time|length', re.I))
        if duration_elem:
            video_info['duration'] = duration_elem.get_text(strip=True)
        
        # Find views
        views_elem = container.find(class_=re.compile(r'views|view-count', re.I))
        if views_elem:
            video_info['views'] = views_elem.get_text(strip=True)
        
        # Find rating
        rating_elem = container.find(class_=re.compile(r'rating|percent', re.I))
        if rating_elem:
            video_info['rating'] = rating_elem.get_text(strip=True)
        
        return video_info
    
    async def get_total_pages(self, html_content: str) -> int:
        """
        Get total pages from pagination
        
        Args:
            html_content: HTML page content
            
        Returns:
            Total number of pages
        """
        match = REGEX_PAGINATION_LAST.search(html_content)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return 1