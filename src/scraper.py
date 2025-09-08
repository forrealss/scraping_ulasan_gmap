import time
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

from models import Review
from writer import ReviewWriter
from utils import safe_get_text, safe_get_attr, extract_rating, get_author_image_url


class GMapReviewScraper:
    """Main class untuk scraping review Google Maps"""
    
    def __init__(self, place_url: str, headless: bool = True, max_reviews: int = 100, output_filename: str = "reviews.csv", auto_scroll: str = "true"):
        self.place_url = place_url
        self.headless = headless
        self.max_reviews = max_reviews
        self.output_filename = output_filename
        self.auto_scroll = auto_scroll.lower().strip()  # "true", "false", or "hybrid"
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    def _init_driver(self) -> None:
        """Initialize Chrome WebDriver"""
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
        """Open reviews panel using multiple strategies"""
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
            lambda: self._try_click_review_button(),
            lambda: self._try_click_rating_stars(),
            lambda: self._try_click_reviews_text(),
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

        # Wait for the reviews list container
        review_container_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',
            'div[role="region"] div[aria-label][jscontroller]',
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
        """Parse reviews from current page"""
        assert self.driver
        reviews: List[Review] = []

        # Try multiple selectors for review cards
        review_selectors = [
            'div.jftiEf.fontBodyMedium',
            'div[data-review-id]',
            'div.bJzME.tTVLSc',
            'div[jscontroller][data-review-id]',
            'div[role="article"]',
            'div[class*="review"]',
            'div[class*="ulasan"]',
            'div[jscontroller]'
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
                                author_name = safe_get_text(elem, [
                                    (By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium'),
                                    (By.CSS_SELECTOR, 'div[class*="d4r55"]'),
                                    (By.CSS_SELECTOR, 'a[href^="/maps/contrib/"]')
                                ])
                                
                                if author_name:
                                    # Find rating
                                    rating_str = safe_get_attr(elem, [
                                        (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                                        (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                                    ], 'aria-label')
                                    rating = extract_rating(rating_str)
                                    
                                    # Find published date
                                    published_at = safe_get_text(elem, [
                                        (By.CSS_SELECTOR, 'span.rsqaWe'),
                                        (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                                    ])
                                    
                                    # Find review text
                                    text = safe_get_text(elem, [
                                        (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                                        (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                                        (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                                        (By.CSS_SELECTOR, 'span[class*="review-text"]')
                                    ])
                                    
                                    # Find author image URL
                                    author_image_url = get_author_image_url(elem)
                                    
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
                    rating_str = safe_get_attr(review_container, [
                        (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                        (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                    ], 'aria-label')
                    rating = extract_rating(rating_str)
                    
                    # Find published date
                    published_at = safe_get_text(review_container, [
                        (By.CSS_SELECTOR, 'span.rsqaWe'),
                        (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                    ])
                    
                    # Find review text
                    text = safe_get_text(review_container, [
                        (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                        (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                        (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                        (By.CSS_SELECTOR, 'span[class*="review-text"]')
                    ])
                    
                    # Find author image URL
                    author_image_url = get_author_image_url(review_container)
                    
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
                # Author name
                author_name = safe_get_text(card, [
                    (By.CSS_SELECTOR, 'div.d4r55.fontTitleMedium'),
                    (By.CSS_SELECTOR, 'div[class*="d4r55"]')
                ])
                
                # Rating
                rating_str = safe_get_attr(card, [
                    (By.CSS_SELECTOR, 'span[role="img"][aria-label*="star"]'),
                    (By.CSS_SELECTOR, 'span.kvMYJc[role="img"]')
                ], 'aria-label')
                rating = extract_rating(rating_str)
                
                # Published date
                published_at = safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span.rsqaWe'),
                    (By.CSS_SELECTOR, 'span[class*="rsqaWe"]')
                ])
                
                # Review text
                text = safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span[class*="wiI7pd"]'),
                    (By.CSS_SELECTOR, 'div[class*="MyEned"] span'),
                    (By.CSS_SELECTOR, 'div[class*="review-snippet"]'),
                    (By.CSS_SELECTOR, 'span[class*="review-text"]')
                ])

                # Find author image URL
                author_image_url = get_author_image_url(card)

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

    def _scroll_and_collect_reviews(self) -> List[Review]:
        """Scroll reviews panel and collect reviews in real-time"""
        assert self.driver and self.wait
        print("Starting to scroll and collect reviews...")
        
        # Try multiple selectors for the scrollable container
        scrollable_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',
            'div[role="region"] div[aria-label][jscontroller]',
            'div[role="region"]',
            'div[aria-label*="reviews" i]',
            'div.bJzME.tTVLSc',
            'div[jscontroller]'
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
        writer = ReviewWriter(output_dir="data", output_filename=self.output_filename)
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
        writer = ReviewWriter(output_dir="data", output_filename=self.output_filename)
        
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

    def _manual_scroll_and_collect_reviews(self) -> List[Review]:
        """Manual scroll mode with interactive menu"""
        assert self.driver and self.wait
        print("\nManual Scroll Mode Activated!")
        print("You can manually scroll the page to load more reviews")
        print("When you're ready to scrape, come back to this terminal\n")
        
        # Try multiple selectors for the scrollable container
        scrollable_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',
            'div[role="region"] div[aria-label][jscontroller]',
            'div[role="region"]',
            'div[aria-label*="reviews" i]',
            'div.bJzME.tTVLSc',
            'div[jscontroller]'
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
            print("Could not find scrollable container, using page scroll instead...")

        # Initialize CSV writer for real-time saving
        writer = ReviewWriter(output_dir="data", output_filename=self.output_filename)
        all_reviews = []
        processed_review_ids = set()
        
        while True:
            print("\n" + "="*60)
            print("MANUAL SCRAPING MENU")
            print("="*60)
            
            # Parse and show current reviews count
            current_reviews = self._parse_reviews_on_page()
            print(f"Reviews currently visible on page: {len(current_reviews)}")
            print(f"Total reviews scraped so far: {len(all_reviews)}")
            print(f"Target max reviews: {self.max_reviews}")
            
            print("\nOptions:")
            print("1. Start scraping current reviews")
            print("2. Exit scraping")
            print("\nTip: Scroll the browser window manually to load more reviews before choosing option 1")
            
            while True:
                try:
                    choice = input("\nEnter your choice (1 or 2): ").strip()
                    if choice in ['1', '2']:
                        break
                    else:
                        print("Invalid choice! Please enter 1 or 2.")
                except KeyboardInterrupt:
                    print("\n\nScraping interrupted by user")
                    return all_reviews
            
            if choice == '2':
                print("Exiting scraping...")
                break
            elif choice == '1':
                print("\nStarting to scrape reviews...")
                
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
                else:
                    print("No new reviews found (all reviews already scraped)")
                
                print(f"Total reviews collected so far: {len(all_reviews)}")
                
                # Check if we've reached the limit
                if len(all_reviews) >= self.max_reviews:
                    print(f"Reached max reviews limit ({self.max_reviews}), stopping...")
                    break
                
                # Ask if user wants to continue
                print("\n" + "-"*40)
                continue_choice = input("Continue scraping? (y/n): ").strip().lower()
                if continue_choice not in ['y', 'yes']:
                    break
        
        return all_reviews

    def _hybrid_scroll_and_collect_reviews(self) -> List[Review]:
        """Hybrid mode: Auto scroll to load reviews, then manual scraping"""
        assert self.driver and self.wait
        print("\nHybrid Mode Activated!")
        print("First, we'll auto-scroll to load all reviews...")
        print("This may take a while depending on the number of reviews\n")
        
        # Try multiple selectors for the scrollable container
        scrollable_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde',
            'div[role="region"] div[aria-label][jscontroller]',
            'div[role="region"]',
            'div[aria-label*="reviews" i]',
            'div.bJzME.tTVLSc',
            'div[jscontroller]'
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
            print("Could not find scrollable container, using page scroll instead...")
            return self._hybrid_scroll_page_and_collect_reviews()

        # Phase 1: Auto-scroll to load all reviews
        print("Phase 1: Auto-scrolling to load all reviews...")
        last_height = 0
        same_height_counter = 0
        scroll_count = 0
        max_scrolls = 1000  # Increase max scrolls significantly for hybrid mode
        last_review_count = 0
        same_review_count_counter = 0
        
        while scroll_count < max_scrolls:
            # Scroll to bottom of the container first
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable)
            time.sleep(3)  # Longer wait for content to load
            
            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable)
            scroll_count += 1
            
            # Only check reviews count every 10 scrolls (or at the end)
            if scroll_count % 10 == 0 or scroll_count == 1:
                current_reviews = self._parse_reviews_on_page()
                current_count = len(current_reviews)
                print(f"Scroll {scroll_count}: Found {current_count} reviews on page")
                
                # Check if review count hasn't increased
                if current_count == last_review_count:
                    same_review_count_counter += 1
                    print(f"Review count unchanged for {same_review_count_counter * 10} scrolls")
                else:
                    same_review_count_counter = 0
                    print(f"Added {current_count - last_review_count} new reviews")
                
                last_review_count = current_count
                
                # Stop if we've reached the target number of reviews
                if current_count >= self.max_reviews:
                    print(f"Reached target of {self.max_reviews} reviews! (Found: {current_count})")
                    break
                    
                # Stop if review count hasn't changed for 30 scrolls (3 checks)
                if same_review_count_counter >= 3:
                    print(f"Review count unchanged for {same_review_count_counter * 10} scrolls. Likely reached the end.")
                    break
            else:
                # Just show scroll progress without counting reviews
                print(f"Scroll {scroll_count}...")
            
            if new_height == last_height:
                same_height_counter += 1
                if scroll_count % 10 == 0:  # Only show height info every 10 scrolls
                    print(f"Height unchanged: {new_height} (count: {same_height_counter})")
            else:
                same_height_counter = 0
                if scroll_count % 10 == 0:
                    print(f"New height: {new_height}")
            
            last_height = new_height

            # Stop if we've reached the end (same height 10 times in a row for more certainty)
            if same_height_counter >= 10:
                # Check final count before stopping
                final_count_reviews = self._parse_reviews_on_page()
                print(f"Reached end of scrollable content (height unchanged for 10 scrolls)")
                print(f"Final count at scroll {scroll_count}: {len(final_count_reviews)} reviews")
                break
        
        # Show final results of scrolling phase
        final_reviews = self._parse_reviews_on_page()
        print("\nScrolling completed!")
        print(f"Total reviews loaded: {len(final_reviews)}")
        print(f"Target was: {self.max_reviews}")
        print(f"Total scrolls performed: {scroll_count}")
        
        # Phase 2: Manual confirmation and scraping
        print("\n" + "="*60)
        print("Phase 2: Ready to scrape!")
        print("="*60)
        
        # Initialize CSV writer for saving
        writer = ReviewWriter(output_dir="data", output_filename=self.output_filename)
        
        while True:
            print(f"Reviews ready to scrape: {len(final_reviews)}")
            print(f"Target max reviews: {self.max_reviews}")
            
            print("\nOptions:")
            print("1. Start scraping all loaded reviews")
            print("2. Exit without scraping")
            
            while True:
                try:
                    choice = input("\nEnter your choice (1 or 2): ").strip()
                    if choice in ['1', '2']:
                        break
                    else:
                        print("Invalid choice! Please enter 1 or 2.")
                except KeyboardInterrupt:
                    print("\n\nScraping interrupted by user")
                    return []
            
            if choice == '2':
                print("Exiting without scraping...")
                return []
            elif choice == '1':
                print("\n🔄 Starting to scrape all reviews...")
                
                # Parse and collect all reviews from current page
                all_reviews = self._parse_reviews_on_page()
                
                # Limit to max_reviews if specified
                if len(all_reviews) > self.max_reviews:
                    all_reviews = all_reviews[:self.max_reviews]
                    print(f"📊 Limited to {self.max_reviews} reviews as specified in MAX_REVIEWS")
                
                # Process and save reviews like manual mode
                processed_reviews = []
                processed_review_ids = set()
                
                for i, review in enumerate(all_reviews, 1):
                    review_id = f"{review.author_name}_{review.published_at}_{review.rating}"
                    if review_id not in processed_review_ids:
                        processed_reviews.append(review)
                        processed_review_ids.add(review_id)
                        print(f"➕ [{i}/{len(all_reviews)}] {review.author_name} - {review.rating} stars - {review.published_at}")
                
                # Save all reviews to CSV using append method like manual mode
                if processed_reviews:
                    writer.append_to_csv(processed_reviews)
                    print(f"💾 Saved {len(processed_reviews)} reviews to CSV")
                
                print(f"✅ Scraping completed! Total: {len(processed_reviews)} reviews")
                return processed_reviews
        
        return []

    def _hybrid_scroll_page_and_collect_reviews(self) -> List[Review]:
        """Hybrid mode fallback: Auto scroll entire page, then manual scraping"""
        print("Hybrid mode: Auto-scrolling entire page...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 1000
        same_height_counter = 0
        last_review_count = 0
        same_review_count_counter = 0
        
        # Phase 1: Auto-scroll the page
        while scroll_count < max_scrolls:
            # Scroll first
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            
            # Only check reviews count every 10 scrolls (or at the first and end)
            if scroll_count % 10 == 0 or scroll_count == 1:
                current_reviews = self._parse_reviews_on_page()
                current_review_count = len(current_reviews)
                print(f"Page scroll {scroll_count}: Found {current_review_count} reviews")
                
                # Check if review count hasn't changed
                if current_review_count == last_review_count:
                    same_review_count_counter += 1
                    print(f"Review count unchanged for {same_review_count_counter * 10} scrolls")
                else:
                    same_review_count_counter = 0
                    print(f"Found {current_review_count - last_review_count} new reviews")
                
                last_review_count = current_review_count
                
                # Stop if we've reached the target number of reviews
                if current_review_count >= self.max_reviews:
                    print(f"Reached target of {self.max_reviews} reviews! (Found: {current_review_count})")
                    break
                    
                # Stop if review count hasn't changed for 30 scrolls (3 checks)
                if same_review_count_counter >= 3:
                    print(f"No new reviews found in last {same_review_count_counter * 10} scrolls, stopping...")
                    break
            else:
                print(f"Page scroll {scroll_count}...")
            
            if new_height == last_height:
                same_height_counter += 1
            else:
                same_height_counter = 0
            
            last_height = new_height
            
            # Stop if we've reached the end (page height unchanged)
            if same_height_counter >= 5:
                # Check final count before stopping
                final_count_reviews = self._parse_reviews_on_page()
                print(f"Reached end of page")
                print(f"Final count at scroll {scroll_count}: {len(final_count_reviews)} reviews")
                break
        
        # Phase 2: Manual confirmation (same as container version)
        final_reviews = self._parse_reviews_on_page()
        print(f"\nScrolling completed!")
        print(f"Total reviews loaded: {len(final_reviews)}")
        
        writer = ReviewWriter(output_dir="data", output_filename=self.output_filename)
        
        while True:
            print(f"\n📋 Reviews ready to scrape: {len(final_reviews)}")
            print("\nOptions:")
            print("1️⃣  Start scraping all loaded reviews")
            print("2️⃣  Exit without scraping")
            
            choice = input("\n🔢 Enter your choice (1 or 2): ").strip()
            
            if choice == '2':
                print("👋 Exiting without scraping...")
                return []
            elif choice == '1':
                print("\n🔄 Starting to scrape all reviews...")
                all_reviews = self._parse_reviews_on_page()
                if len(all_reviews) > self.max_reviews:
                    all_reviews = all_reviews[:self.max_reviews]
                    print(f"📊 Limited to {self.max_reviews} reviews as specified in MAX_REVIEWS")
                
                processed_reviews = []
                processed_review_ids = set()
                
                for i, review in enumerate(all_reviews, 1):
                    review_id = f"{review.author_name}_{review.published_at}_{review.rating}"
                    if review_id not in processed_review_ids:
                        processed_reviews.append(review)
                        processed_review_ids.add(review_id)
                        print(f"➕ [{i}/{len(all_reviews)}] {review.author_name} - {review.rating} stars - {review.published_at}")
                
                if processed_reviews:
                    writer.append_to_csv(processed_reviews)
                    print(f"💾 Saved {len(processed_reviews)} reviews to CSV")
                
                return processed_reviews
        
        return []

    def scrape(self) -> List[Review]:
        """Main method to start scraping"""
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
                
                # Check auto scroll mode
                if self.auto_scroll == "true":
                    print("Auto scroll mode enabled")
                    reviews = self._scroll_and_collect_reviews()
                elif self.auto_scroll == "false":
                    print("Manual scroll mode enabled")
                    reviews = self._manual_scroll_and_collect_reviews()
                elif self.auto_scroll == "hybrid":
                    print("Hybrid scroll mode enabled")
                    reviews = self._hybrid_scroll_and_collect_reviews()
                else:
                    # Default to auto scroll for backward compatibility
                    print("Auto scroll mode enabled (default)")
                    reviews = self._scroll_and_collect_reviews()
                    
            except Exception as e:
                print(f"Could not open reviews panel: {e}")
                if self.auto_scroll == "true" or self.auto_scroll not in ["true", "false", "hybrid"]:
                    print("Trying to scroll the main page instead...")
                    reviews = self._scroll_page_and_collect_reviews()
                elif self.auto_scroll == "false":
                    print("Manual mode: Please scroll the page manually to load more reviews")
                    reviews = self._manual_scroll_and_collect_reviews()
                elif self.auto_scroll == "hybrid":
                    print("Hybrid mode: Auto-scrolling the main page instead...")
                    reviews = self._hybrid_scroll_page_and_collect_reviews()
            
            return reviews
        finally:
            if self.driver:
                self.driver.quit()
