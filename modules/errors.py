"""
XXXGFPORN API Custom Exceptions
"""


class XXXGFPornError(Exception):
    """Base exception for XXXGFPORN API"""
    pass


class InvalidURL(XXXGFPornError):
    """Raised when URL is invalid or cannot be parsed"""
    pass


class VideoNotFound(XXXGFPornError):
    """Raised when video cannot be found"""
    pass


class VideoDisabled(XXXGFPornError):
    """Raised when video has been disabled or removed"""
    pass


class NetworkError(XXXGFPornError):
    """Raised when network request fails"""
    pass


class ParseError(XXXGFPornError):
    """Raised when HTML parsing fails"""
    pass


class InvalidVideoID(XXXGFPornError):
    """Raised when video ID is invalid"""
    pass


class CategoryNotFound(XXXGFPornError):
    """Raised when category cannot be found"""
    pass


class SearchError(XXXGFPornError):
    """Raised when search fails"""
    pass


class RateLimitError(XXXGFPornError):
    """Raised when rate limited by the server"""
    pass


class ProxyError(XXXGFPornError):
    """Raised when proxy connection fails"""
    pass