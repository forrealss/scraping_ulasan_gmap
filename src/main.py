import os
import time
import csv
from dataclasses import dataclass, asdict
from typing import List, Optional

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class Review:
    author_name: str
    rating: Optional[float]
    published_at: str
    text: str
    author_image_url: str = ""


class GMapReviewScraper:
    def __init__(self, place_url: str, headless: bool = True, max_reviews: int = 100):
        self.place_url = place_url
        self.headless = headless
        self.max_reviews = max_reviews
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _init_driver(self) -> None:
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,1024")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)

    def _open_reviews_panel(self) -> None:
        assert self.driver and self.wait
        print(f"Loading URL: {self.place_url}")
        self.driver.get(self.place_url)

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="main"]')))
            print("Page loaded successfully")
        except TimeoutException:
            raise RuntimeError("Failed to load Google Maps place page")

        # Wait a bit for the page to fully render
        time.sleep(3)
        
        # Try multiple strategies to open reviews panel
        strategies = [
            # Strategy 1: Look for review count button
            lambda: self._try_click_review_button(),
            # Strategy 2: Look for rating stars
            lambda: self._try_click_rating_stars(),
            # Strategy 3: Look for "Reviews" text
            lambda: self._try_click_reviews_text(),
            # Strategy 4: Look for any clickable element with review-related text
            lambda: self._try_click_any_review_element(),
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"Trying strategy {i}...")
                if strategy():
                    print(f"Strategy {i} succeeded!")
                    break
            except Exception as e:
                print(f"Strategy {i} failed: {e}")
                continue
        else:
            raise RuntimeError("All strategies failed to open reviews panel")

        # Wait for the reviews list container with multiple possible selectors
        review_container_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',  # Based on your HTML structure
            'div[role="region"] div[aria-label][jscontroller]',
            'div[jscontroller][data-review-id]',
            'div[role="region"]',
            'div[aria-label*="reviews" i]'
        ]
        
        for selector in review_container_selectors:
            try:
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"Found reviews container with selector: {selector}")
                break
            except TimeoutException:
                continue
        else:
            print("Warning: Could not find reviews container, continuing anyway...")

    def _try_click_review_button(self) -> bool:
        """Try to click review count button"""
        selectors = [
            'button[jsaction*="pane.reviewChart.moreReviews"]',
            'button[aria-label*="reviews" i]',
            'button[aria-label*="ulasan" i]',
            'a[href*="reviews"]',
            'a[href*="ulasan"]'
        ]
        
        for selector in selectors:
            try:
                # Use shorter timeout for each attempt
                elem = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                elem.click()
                return True
            except TimeoutException:
                continue
        return False

    def _try_click_rating_stars(self) -> bool:
        """Try to click on rating stars"""
        selectors = [
            'div[aria-label*="stars" i]',
            'span[aria-label*="stars" i]',
            'div[role="img"][aria-label*="stars" i]'
        ]
        
        for selector in selectors:
            try:
                elem = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                elem.click()
                return True
            except TimeoutException:
                continue
        return False

    def _try_click_reviews_text(self) -> bool:
        """Try to click on text containing 'reviews' or 'ulasan'"""
        xpath_selectors = [
            "//button[contains(., 'reviews') or contains(., 'Reviews')]",
            "//button[contains(., 'ulasan') or contains(., 'Ulasan')]",
            "//a[contains(., 'reviews') or contains(., 'Reviews')]",
            "//a[contains(., 'ulasan') or contains(., 'Ulasan')]",
            "//span[contains(., 'reviews') or contains(., 'Reviews')]",
            "//span[contains(., 'ulasan') or contains(., 'Ulasan')]"
        ]
        
        for xpath in xpath_selectors:
            try:
                elem = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                elem.click()
                return True
            except TimeoutException:
                continue
        return False

    def _try_click_any_review_element(self) -> bool:
        """Try to click any element that might be related to reviews"""
        # Look for elements with review-related attributes or text
        selectors = [
            'div[data-review-id]',
            'div[jscontroller*="review"]',
            'div[class*="review"]',
            'div[class*="ulasan"]'
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        if elem.is_displayed() and elem.is_enabled():
                            elem.click()
                            return True
                    except:
                        continue
            except:
                continue
        return False



    def _parse_reviews_on_page(self) -> List[Review]:
        assert self.driver
        reviews: List[Review] = []

        # Try multiple selectors for review cards
        review_selectors = [
            'div.jftiEf.fontBodyMedium',  # Based on your HTML structure - the actual review cards
            'div[data-review-id]',  # Any div with review ID
            'div.bJzME.tTVLSc',  # Fallback
            'div[jscontroller][data-review-id]',
            'div[role="article"]',
            'div[class*="review"]',
            'div[class*="ulasan"]',
            'div[jscontroller]'  # More general
        ]
        
        review_cards = []
        for selector in review_selectors:
            cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                review_cards = cards
                print(f"Found {len(cards)} review cards with selector: {selector}")
                break
        
        if not review_cards:
            print("No review cards found, trying to find individual review elements...")
            # Try to find reviews by looking for author names
            author_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium')
            print(f"Found {len(author_elements)} author elements")
            
            # If still no reviews found, try alternative approach
            if not author_elements:
                print("No author elements found, trying alternative selectors...")
                # Try to find any elements that might contain reviews
                alternative_selectors = [
                    'div[jscontroller]',
                    'div[data-review-id]',
                    'div[role="article"]',
                    'div[class*="review"]'
                ]
                
                for selector in alternative_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"Found {len(elements)} elements with selector: {selector}")
                        # Try to parse these as review containers
                        for i, elem in enumerate(elements):
                            try:
                                # Look for author name within this element
                                author_name = self._safe_get_text(elem, [
                                    (By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium'),
                                    (By.CSS_SELECTOR, 'div[class*="d4r55"]'),
                                    (By.CSS_SELECTOR, 'a[href^="/maps/contrib/"]')
                                ])
                                
                                if author_name:
                                    # Find rating
                                    rating_str = self._safe_get_attr(elem, [
                                        (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                                        (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                                    ], 'aria-label')
                                    rating = self._extract_rating(rating_str)
                                    
                                    # Find published date
                                    published_at = self._safe_get_text(elem, [
                                        (By.CSS_SELECTOR, 'span.rsqaWe'),
                                        (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                                    ])
                                    
                                    # Find review text
                                    text = self._safe_get_text(elem, [
                                        (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                                        (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                                        (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                                        (By.CSS_SELECTOR, 'span[class*="review-text"]')
                                    ])
                                    
                                    # Find author image URL
                                    author_image_url = self._get_author_image_url(elem)
                                    
                                    reviews.append(Review(
                                        author_name=author_name,
                                        rating=rating,
                                        published_at=published_at,
                                        text=text,
                                        author_image_url=author_image_url,
                                    ))

                                
                                if len(reviews) >= self.max_reviews:
                                    break
                                    
                            except Exception as e:
                                print(f"Error parsing element {i+1}: {e}")
                                continue
                        break
            
            for i, author_elem in enumerate(author_elements):
                try:
                    # Get the parent container that contains the review
                    review_container = author_elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'bJzME') or contains(@class, 'review') or @jscontroller]")
                    
                    author_name = author_elem.text.strip()
                    
                    # Find rating in the same container
                    rating_str = self._safe_get_attr(review_container, [
                        (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                        (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                    ], 'aria-label')
                    rating = self._extract_rating(rating_str)
                    
                    # Find published date
                    published_at = self._safe_get_text(review_container, [
                        (By.CSS_SELECTOR, 'span.rsqaWe'),
                        (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                    ])
                    
                    # Find review text
                    text = self._safe_get_text(review_container, [
                        (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                        (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                        (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                        (By.CSS_SELECTOR, 'span[class*="review-text"]')
                    ])
                    
                    # Find author image URL
                    author_image_url = self._get_author_image_url(review_container)
                    
                    if author_name:
                        reviews.append(Review(
                            author_name=author_name,
                            rating=rating,
                            published_at=published_at,
                            text=text,
                            author_image_url=author_image_url,
                        ))
                    
                    if len(reviews) >= self.max_reviews:
                        break
                        
                except Exception as e:
                    print(f"Error parsing review {i+1}: {e}")
                    continue
            
            return reviews
        
        # Parse review cards normally
        for i, card in enumerate(review_cards):
            try:
                # Author name - using the exact class from your HTML
                author_name = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium'),
                    (By.CSS_SELECTOR, 'div[class*="d4r55"]')
                ])
                
                # Rating - using the exact structure from your HTML
                rating_str = self._safe_get_attr(card, [
                    (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                    (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                ], 'aria-label')
                rating = self._extract_rating(rating_str)
                
                # Published date - using the exact class from your HTML
                published_at = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span.rsqaWe'),
                    (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                ])
                
                # Review text - need to find the actual text content
                text = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                    (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                    (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                    (By.CSS_SELECTOR, 'span[class*="review-text"]')
                ])

                # Find author image URL
                author_image_url = self._get_author_image_url(card)

                # Only add if we have at least author name
                if author_name:
                    reviews.append(Review(
                        author_name=author_name,
                        rating=rating,
                        published_at=published_at,
                        text=text,
                        author_image_url=author_image_url,
                    ))
                
                if len(reviews) >= self.max_reviews:
                    print(f"Reached max reviews limit ({self.max_reviews}) during parsing, stopping...")
                    break
            except StaleElementReferenceException:
                print(f"Stale element for review {i+1}, skipping...")
                continue
            except Exception as e:
                print(f"Error parsing review {i+1}: {e}")
                continue
        return reviews
        for i, card in enumerate(review_cards):
            try:
                # Author name - using the exact class from your HTML
                author_name = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium'),
                    (By.CSS_SELECTOR, 'div[class*="d4r55"]')
                ])
                
                # Rating - using the exact structure from your HTML
                rating_str = self._safe_get_attr(card, [
                    (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                    (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                ], 'aria-label')
                rating = self._extract_rating(rating_str)
                
                # Published date - using the exact class from your HTML
                published_at = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span.rsqaWe'),
                    (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                ])
                
                # Review text - need to find the actual text content
                text = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                    (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                    (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                    (By.CSS_SELECTOR, 'span[class*="review-text"]')
                ])

                # Only add if we have at least author name
                if author_name:
                    reviews.append(Review(
                        author_name=author_name,
                        rating=rating,
                        published_at=published_at,
                        text=text,
                    ))
                
                if len(reviews) >= self.max_reviews:
                    print(f"Reached max reviews limit ({self.max_reviews}) during parsing, stopping...")
                    break
            except StaleElementReferenceException:
                print(f"Stale element for review {i+1}, skipping...")
                continue
            except Exception as e:
                print(f"Error parsing review {i+1}: {e}")
                continue
        return reviews

    def _safe_get_text(self, root, locator_candidates) -> str:
        for by, selector in locator_candidates:
            try:
                elem = root.find_element(by, selector)
                text = elem.text.strip()
                if text:
                    return text
            except Exception:
                continue
        return ""

    def _safe_get_attr(self, root, locator_candidates, attr: str) -> str:
        for by, selector in locator_candidates:
            try:
                elem = root.find_element(by, selector)
                value = elem.get_attribute(attr) or ""
                value = value.strip()
                if value:
                    return value
            except Exception:
                continue
        return ""

    def _extract_rating(self, aria_label: str) -> Optional[float]:
        if not aria_label:
            return None
        # Examples: "5.0 stars", "Rated 4.5 out of 5"
        for token in aria_label.split():
            try:
                return float(token.replace(',', '.'))
            except ValueError:
                continue
        return None

    def _get_author_image_url(self, container) -> str:
        """Extract author image URL from review container"""
        # Try multiple selectors for author image
        selectors = [
            'img.NBa7we',
            'img[class*="NBa7we"]',
            'img[alt=""]',
            'img[src*="googleusercontent"]',
            'img[src*="lh3.googleusercontent"]'
        ]
        
        for selector in selectors:
            try:
                img_elem = container.find_element(By.CSS_SELECTOR, selector)
                image_url = img_elem.get_attribute('src')
                if image_url and 'googleusercontent' in image_url:
                    return image_url
            except Exception:
                continue
        
        return ""

    def scrape(self) -> List[Review]:
        self._init_driver()
        try:
            # Load the page and wait for it to load
            print(f"Loading URL: {self.place_url}")
            self.driver.get(self.place_url)
            
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="main"]')))
                print("Page loaded successfully")
            except TimeoutException:
                raise RuntimeError("Failed to load Google Maps place page")
            
            # Wait a bit for the page to fully render
            time.sleep(3)
            
            # Try to parse reviews directly from the page first
            print("Trying to parse reviews directly from the page...")
            reviews = self._parse_reviews_on_page()
            
            # Try to open reviews panel to get more reviews
            print("Trying to open reviews panel for more reviews...")
            try:
                self._open_reviews_panel()
                print("Reviews panel opened successfully!")
                reviews = self._scroll_and_collect_reviews()
            except Exception as e:
                print(f"Could not open reviews panel: {e}")
                print("Trying to scroll the main page instead...")
                reviews = self._scroll_page_and_collect_reviews()
            
            return reviews
        finally:
            if self.driver:
                self.driver.quit()

    def _scroll_and_collect_reviews(self) -> List[Review]:
        """Scroll reviews panel and collect reviews in real-time"""
        assert self.driver and self.wait
        print("Starting to scroll and collect reviews...")
        
        # Try multiple selectors for the scrollable container
        scrollable_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',  # Based on your HTML structure
            'div[role="region"] div[aria-label][jscontroller]',
            'div[role="region"]',
            'div[aria-label*="reviews" i]',
            'div.bJzME.tTVLSc',
            'div[jscontroller]'  # Fallback
        ]
        
        scrollable = None
        for selector in scrollable_selectors:
            try:
                scrollable = self.driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Found scrollable container with selector: {selector}")
                break
            except NoSuchElementException:
                continue
        
        if scrollable is None:
            print("Warning: Could not find scrollable container, trying to scroll the page instead...")
            return self._scroll_page_and_collect_reviews()

        # Initialize CSV writer for real-time saving
        writer = ReviewWriter(output_dir="data", output_filename="reviews.csv")
        all_reviews = []
        processed_review_ids = set()
        last_height = 0
        same_height_counter = 0
        scroll_count = 0
        
        while True:
            # Parse and collect new reviews from current page
            new_reviews = self._parse_reviews_on_page()
            
            # Add only new reviews that haven't been processed
            new_reviews_added = []
            for review in new_reviews:
                review_id = f"{review.author_name}_{review.published_at}_{review.rating}"
                if review_id not in processed_review_ids:
                    all_reviews.append(review)
                    new_reviews_added.append(review)
                    processed_review_ids.add(review_id)
                    print(f"Added new review: {review.author_name} - {review.rating} stars - {review.published_at}")
            
            # Save new reviews to CSV immediately
            if new_reviews_added:
                writer.append_to_csv(new_reviews_added)
                print(f"Saved {len(new_reviews_added)} new reviews to CSV")
            
            print(f"Total reviews collected so far: {len(all_reviews)}")
            
            # Scroll to bottom of the container
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable)
            time.sleep(2)  # Wait for content to load
            
            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable)
            scroll_count += 1
            print(f"Scroll {scroll_count}: height {new_height}")
            
            if new_height == last_height:
                same_height_counter += 1
            else:
                same_height_counter = 0
            last_height = new_height

            # Stop if we've reached the end, hit max scrolls, or reached max reviews
            if same_height_counter >= 3 or scroll_count >= 50 or len(all_reviews) >= self.max_reviews:
                if len(all_reviews) >= self.max_reviews:
                    print(f"Reached max reviews limit ({self.max_reviews}), stopping...")
                else:
                    print(f"Stopping scroll after {scroll_count} attempts")
                break
        
        return all_reviews

    def _scroll_page_and_collect_reviews(self) -> List[Review]:
        """Fallback: scroll the entire page and collect reviews in real-time"""
        print("Scrolling entire page and collecting reviews...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        all_reviews = []
        processed_review_ids = set()
        
        # Initialize CSV writer for real-time saving
        writer = ReviewWriter(output_dir="data", output_filename="reviews.csv")
        
        while scroll_count < 50:  # Max 50 page scrolls
            # Parse and collect new reviews from current page
            new_reviews = self._parse_reviews_on_page()
            
            # Add only new reviews that haven't been processed
            new_reviews_added = []
            for review in new_reviews:
                review_id = f"{review.author_name}_{review.published_at}_{review.rating}"
                if review_id not in processed_review_ids:
                    all_reviews.append(review)
                    new_reviews_added.append(review)
                    processed_review_ids.add(review_id)
                    print(f"Added new review: {review.author_name} - {review.rating} stars - {review.published_at}")
            
            # Save new reviews to CSV immediately
            if new_reviews_added:
                writer.append_to_csv(new_reviews_added)
                print(f"Saved {len(new_reviews_added)} new reviews to CSV")
            
            print(f"Total reviews collected so far: {len(all_reviews)}")
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"Page scroll {scroll_count}: height {new_height}")
            
            # Stop if we've reached the end or reached max reviews
            if new_height == last_height or len(all_reviews) >= self.max_reviews:
                if len(all_reviews) >= self.max_reviews:
                    print(f"Reached max reviews limit ({self.max_reviews}), stopping...")
                break
            last_height = new_height
        
        return all_reviews


class ReviewWriter:
    def __init__(self, output_dir: str = "data", output_filename: str = "reviews.csv"):
        self.output_dir = output_dir
        self.output_filename = output_filename
        self.output_path = os.path.join(self.output_dir, self.output_filename)
        self.header_written = False

    def write_csv(self, reviews: List[Review]) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["author_name", "rating", "published_at", "text", "author_image_url"])
            writer.writeheader()
            for review in reviews:
                writer.writerow(asdict(review))
        self.header_written = True
        return self.output_path

    def append_to_csv(self, reviews: List[Review]) -> str:
        """Append new reviews to existing CSV file"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if file exists and has header
        file_exists = os.path.exists(self.output_path)
        
        with open(self.output_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["author_name", "rating", "published_at", "text", "author_image_url"])
            
            # Write header only if file doesn't exist or header not written yet
            if not file_exists or not self.header_written:
                writer.writeheader()
                self.header_written = True
            
            # Write the new reviews
            for review in reviews:
                writer.writerow(asdict(review))
        
        return self.output_path


def main() -> None:
    load_dotenv()
    place_url = os.getenv("GMAP_PLACE_URL", "").strip()
    if not place_url:
        raise SystemExit("Please set GMAP_PLACE_URL in your .env file")

    max_reviews_env = os.getenv("MAX_REVIEWS", "1000").strip()  # Increased default to 1000
    try:
        max_reviews = int(max_reviews_env)
    except ValueError:
        max_reviews = 1000

    headless_env = os.getenv("HEADLESS", "true").strip().lower()
    headless = headless_env not in {"false", "0", "no"}

    scraper = GMapReviewScraper(place_url=place_url, headless=headless, max_reviews=max_reviews)
    reviews = scraper.scrape()

    print(f"Scraped {len(reviews)} reviews → data/reviews.csv")


if __name__ == "__main__":
    main()
