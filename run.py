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

    # Get auto_scroll setting from environment
    auto_scroll_env = os.getenv("AUTO_SCROLL", "true").strip().lower()
    # Validate auto_scroll value
    if auto_scroll_env not in ["true", "false", "hybrid"]:
        print(f"Warning: Invalid AUTO_SCROLL value '{auto_scroll_env}'. Using 'true' as default.")
        auto_scroll_env = "true"
    
    auto_scroll = auto_scroll_env

    # Get output filename from environment
    output_filename = os.getenv("OUTPUT_FILENAME", "reviews").strip()
    if not output_filename.endswith('.csv'):
        output_filename += '.csv'

    # Show menu if auto_scroll is not true (i.e., false or hybrid)
    if auto_scroll != "true":
        show_manual_menu(auto_scroll)

    # Create scraper instance and start scraping
    scraper = GMapReviewScraper(
        place_url=place_url,
        headless=headless,
        max_reviews=max_reviews,
        output_filename=output_filename,
        auto_scroll=auto_scroll
    )

    reviews = scraper.scrape()
    print(f"Scraped {len(reviews)} reviews → data/{output_filename}")


def show_manual_menu(auto_scroll_mode: str) -> None:
    """Show manual mode menu"""
    print("\n" + "="*60)
    print(" GOOGLE MAPS REVIEW SCRAPER")
    print("="*60)
    print("Configuration:")
    print(f"   URL: {os.getenv('GMAP_PLACE_URL', 'Not set')[:60]}...")
    print(f"   Max Reviews: {os.getenv('MAX_REVIEWS', '1000')}")
    print(f"   Headless: {os.getenv('HEADLESS', 'true')}")
    print(f"   Output: {os.getenv('OUTPUT_FILENAME', 'reviews.csv')}")
    print(f"   Auto Scroll: {auto_scroll_mode}")
    
    mode_title = ""
    mode_description = ""
    
    if auto_scroll_mode == "false":
        mode_title = "MANUAL SCROLL MODE"
        mode_description = ("Manual mode: You have full control over scrolling and scraping.\n"
                            "The browser will open and you can manually scroll to load more reviews.\n"
                            "After scrolling, come back to the terminal to scrape the visible reviews.")
    elif auto_scroll_mode == "hybrid":
        mode_title = "HYBRID SCROLL MODE"
        mode_description = ("Hybrid mode: Auto-scroll first, then manual scraping control.\n"
                            "The system will automatically scroll to load all reviews up to your limit.\n"
                            "Then you'll be prompted to confirm before starting the scraping process.")
    
    print("\n" + "="*60)
    print(mode_title)
    print("="*60)
    print(mode_description)
    
    print("\nOptions:")
    print("1. Start scraping (opens browser)")
    print("2. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1 or 2): ").strip()
            if choice == '1':
                if auto_scroll_mode == "hybrid":
                    print("\nStarting scraper in hybrid mode...")
                    print("Phase 1: Auto-scrolling will start automatically")
                    print("Phase 2: You'll be prompted when ready to scrape")
                else:
                    print("\nStarting scraper in manual mode...")
                break
            elif choice == '2':
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice! Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()