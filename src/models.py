from dataclasses import dataclass
from typing import Optional


@dataclass
class Review:
    """Data class untuk menyimpan data review dari Google Maps"""
    author_name: str
    rating: Optional[float]
    published_at: str
    text: str
    author_image_url: str = "" 