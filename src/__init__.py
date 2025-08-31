"""
Google Maps Review Scraper Package

A Python package for scraping Google Maps reviews with OOP approach.
"""

from .models import Review
from .scraper import GMapReviewScraper
from .writer import ReviewWriter

__version__ = "1.0.0"
__author__ = "Your Name"

__all__ = ["Review", "GMapReviewScraper", "ReviewWriter"] 