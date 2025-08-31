#!/usr/bin/env python3
"""
Google Maps Review Scraper - Main Entry Point

Run this file to start the scraper:
python run.py
"""

import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from scraper import GMapReviewScraper


def main() -> None:
    """Main entry point for the Google Maps review scraper"""
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    place_url = os.getenv("GMAP_PLACE_URL", "").strip()
    if not place_url:
        raise SystemExit("Please set GMAP_PLACE_URL in your .env file")

    max_reviews_env = os.getenv("MAX_REVIEWS", "1000").strip()
    try:
        max_reviews = int(max_reviews_env)
    except ValueError:
        max_reviews = 1000

    headless_env = os.getenv("HEADLESS", "true").strip().lower()
    headless = headless_env not in {"false", "0", "no"}

    # Create scraper instance and start scraping
    scraper = GMapReviewScraper(
        place_url=place_url, 
        headless=headless, 
        max_reviews=max_reviews
    )
    
    reviews = scraper.scrape()
    print(f"Scraped {len(reviews)} reviews → data/reviews.csv")


if __name__ == "__main__":
    main() 