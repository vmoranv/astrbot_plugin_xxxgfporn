"""
XXXGFPORN API Constants
URL patterns, regex patterns, and default values
"""

import re

# Base URLs
ROOT_URL = "https://www.xxxgfporn.com"
VIDEO_URL = f"{ROOT_URL}/video/"
CATEGORY_URL = f"{ROOT_URL}/categories/"
SEARCH_URL = f"{ROOT_URL}/search/"
CHANNEL_URL = f"{ROOT_URL}/channels/"
MEMBER_URL = f"{ROOT_URL}/members/"

# Default Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Regex Patterns for Video Info Extraction
REGEX_VIDEO_ID = re.compile(r"/video/(\d+)/")
REGEX_VIDEO_ID_ALT = re.compile(r"video[_-]?(\d+)")
REGEX_VIDEO_TITLE = re.compile(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>', re.IGNORECASE)
REGEX_VIDEO_TITLE_ALT = re.compile(r'<title>([^<]+)</title>', re.IGNORECASE)
REGEX_VIDEO_DURATION = re.compile(r'<span[^>]*class="[^"]*duration[^"]*"[^>]*>(\d+:\d+(?::\d+)?)</span>', re.IGNORECASE)
REGEX_VIDEO_DURATION_ALT = re.compile(r'"duration"[:\s]*"?(\d+:\d+(?::\d+)?)"?', re.IGNORECASE)
REGEX_VIDEO_VIEWS = re.compile(r'<span[^>]*class="[^"]*views[^"]*"[^>]*>([0-9,]+)</span>', re.IGNORECASE)
REGEX_VIDEO_VIEWS_ALT = re.compile(r'"viewCount"[:\s]*"?([0-9,]+)"?', re.IGNORECASE)
REGEX_VIDEO_RATING = re.compile(r'<span[^>]*class="[^"]*rating[^"]*"[^>]*>([0-9.]+%?)</span>', re.IGNORECASE)
REGEX_VIDEO_LIKES = re.compile(r'<span[^>]*class="[^"]*likes[^"]*"[^>]*>([0-9,]+)</span>', re.IGNORECASE)
REGEX_VIDEO_DISLIKES = re.compile(r'<span[^>]*class="[^"]*dislikes[^"]*"[^>]*>([0-9,]+)</span>', re.IGNORECASE)
REGEX_VIDEO_UPLOADER = re.compile(r'<a[^>]*href="[^"]*members[^"]*"[^>]*>([^<]+)</a>', re.IGNORECASE)
REGEX_VIDEO_UPLOAD_DATE = re.compile(r'<span[^>]*class="[^"]*date[^"]*"[^>]*>([^<]+)</span>', re.IGNORECASE)
REGEX_VIDEO_CATEGORIES = re.compile(r'<a[^>]*href="[^"]*categor[^"]*"[^>]*>([^<]+)</a>', re.IGNORECASE)
REGEX_VIDEO_TAGS = re.compile(r'<a[^>]*href="[^"]*tag[^"]*"[^>]*>([^<]+)</a>', re.IGNORECASE)

# Thumbnail patterns
REGEX_VIDEO_THUMBNAIL = re.compile(r'<img[^>]*class="[^"]*thumb[^"]*"[^>]*src="([^"]+)"', re.IGNORECASE)
REGEX_VIDEO_THUMBNAIL_ALT = re.compile(r'"thumbnailUrl"[:\s]*"([^"]+)"', re.IGNORECASE)
REGEX_VIDEO_PREVIEW = re.compile(r'data-preview="([^"]+)"', re.IGNORECASE)

# Video source patterns
REGEX_VIDEO_SOURCE = re.compile(r'<source[^>]*src="([^"]+)"[^>]*type="video/mp4"', re.IGNORECASE)
REGEX_VIDEO_SOURCE_ALT = re.compile(r'"contentUrl"[:\s]*"([^"]+)"', re.IGNORECASE)
REGEX_VIDEO_EMBED = re.compile(r'<iframe[^>]*src="([^"]+)"[^>]*>', re.IGNORECASE)

# Video list patterns
REGEX_VIDEO_LIST_ITEM = re.compile(
    r'<div[^>]*class="[^"]*video[_-]?item[^"]*"[^>]*>.*?'
    r'<a[^>]*href="([^"]+)"[^>]*>.*?'
    r'<img[^>]*src="([^"]+)"[^>]*>.*?'
    r'<span[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</span>',
    re.IGNORECASE | re.DOTALL
)

# Pagination patterns
REGEX_PAGINATION_LAST = re.compile(r'<a[^>]*href="[^"]*[?&]page=(\d+)"[^>]*>(?:Last|»|>>)</a>', re.IGNORECASE)
REGEX_PAGINATION_NEXT = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>(?:Next|›|>)</a>', re.IGNORECASE)

# JSON-LD patterns
REGEX_JSON_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL)

# Quality options
QUALITY_OPTIONS = ["240", "360", "480", "720", "1080", "1440", "2160"]

# Category enum
class Category:
    AMATEUR = "amateur"
    ANAL = "anal"
    ASIAN = "asian"
    BBW = "bbw"
    BIG_TITS = "big-tits"
    BLONDE = "blonde"
    BLOWJOB = "blowjob"
    BRUNETTE = "brunette"
    CREAMPIE = "creampie"
    CUMSHOT = "cumshot"
    HARDCORE = "hardcore"
    LESBIAN = "lesbian"
    MATURE = "mature"
    MILF = "milf"
    TEEN = "teen"
    THREESOME = "threesome"
    
    @classmethod
    def all(cls) -> list:
        return [
            cls.AMATEUR, cls.ANAL, cls.ASIAN, cls.BBW, cls.BIG_TITS,
            cls.BLONDE, cls.BLOWJOB, cls.BRUNETTE, cls.CREAMPIE,
            cls.CUMSHOT, cls.HARDCORE, cls.LESBIAN, cls.MATURE,
            cls.MILF, cls.TEEN, cls.THREESOME
        ]

# Sorting options
class SortOrder:
    NEWEST = "newest"
    MOST_VIEWED = "most-viewed"
    TOP_RATED = "top-rated"
    LONGEST = "longest"
    RANDOM = "random"
    
    @classmethod
    def all(cls) -> list:
        return [cls.NEWEST, cls.MOST_VIEWED, cls.TOP_RATED, cls.LONGEST, cls.RANDOM]

# Time filter
class TimeFilter:
    ALL_TIME = "all"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    
    @classmethod
    def all(cls) -> list:
        return [cls.ALL_TIME, cls.TODAY, cls.WEEK, cls.MONTH, cls.YEAR]