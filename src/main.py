import os
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

    # Get output filename from environment
    output_filename = os.getenv("OUTPUT_FILENAME", "reviews.csv").strip()
    if not output_filename.endswith('.csv'):
        output_filename += '.csv'

    # Create scraper instance and start scraping
    scraper = GMapReviewScraper(
        place_url=place_url, 
        headless=headless, 
        max_reviews=max_reviews,
        output_filename=output_filename
    )
    
    reviews = scraper.scrape()
    print(f"Scraped {len(reviews)} reviews → data/{output_filename}")


if __name__ == "__main__":
    main()
