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

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        driver.set_page_load_timeout(60)
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)

    def _open_reviews_panel(self) -> None:
        assert self.driver and self.wait
        self.driver.get(self.place_url)

        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="main"]')))
        except TimeoutException:
            raise RuntimeError("Failed to load Google Maps place page")

        # Try to click the total reviews link/button to open the reviews panel
        candidates = [
            (By.CSS_SELECTOR, 'button[jsaction*="pane.reviewChart.moreReviews"]'),
            (By.CSS_SELECTOR, 'button[aria-label*="reviews" i]'),
            (By.XPATH, "//button[contains(., 'reviews') or contains(., 'ulasan')]")
        ]

        for by, selector in candidates:
            try:
                elem = self.wait.until(EC.element_to_be_clickable((by, selector)))
                elem.click()
                break
            except TimeoutException:
                continue
            except Exception:
                continue
        else:
            # Fallback: attempt to click the rating block that often opens reviews
            try:
                rating_block = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label*="stars" i]')))
                rating_block.click()
            except Exception as exc:
                raise RuntimeError("Could not open reviews panel") from exc

        # Wait for the reviews list container
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="region"] div[aria-label][jscontroller]')))

    def _scroll_reviews(self) -> None:
        assert self.driver and self.wait
        # Google Maps reviews are inside a scrollable div
        scrollable_selectors = [
            'div[role="region"] div[aria-label][jscontroller]'
        ]
        scrollable = None
        for selector in scrollable_selectors:
            try:
                scrollable = self.driver.find_element(By.CSS_SELECTOR, selector)
                break
            except NoSuchElementException:
                continue
        if scrollable is None:
            raise RuntimeError("Scrollable reviews container not found")

        last_height = 0
        same_height_counter = 0
        while True:
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable)
            time.sleep(1.2)

            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable)
            if new_height == last_height:
                same_height_counter += 1
            else:
                same_height_counter = 0
            last_height = new_height

            if same_height_counter >= 3:
                break

    def _parse_reviews_on_page(self) -> List[Review]:
        assert self.driver
        reviews: List[Review] = []

        review_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div[jscontroller][data-review-id]')
        for card in review_cards:
            try:
                author_name = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'div[class*="d4r55"], a[href^="/maps/contrib/"]')
                ])
                rating_str = self._safe_get_attr(card, [
                    (By.CSS_SELECTOR, 'span[aria-label*="stars" i]'),
                ], 'aria-label')
                rating = self._extract_rating(rating_str)
                published_at = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span[class*="rsqaWe"], span[class*="UJg1Bb"]')
                ])
                text = self._safe_get_text(card, [
                    (By.CSS_SELECTOR, 'span[class*="wiI7pd"], div[class*="MyEned"] span')
                ])

                reviews.append(Review(
                    author_name=author_name,
                    rating=rating,
                    published_at=published_at,
                    text=text,
                ))
                if len(reviews) >= self.max_reviews:
                    break
            except StaleElementReferenceException:
                continue
            except Exception:
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

    def scrape(self) -> List[Review]:
        self._init_driver()
        try:
            self._open_reviews_panel()
            self._scroll_reviews()
            reviews = self._parse_reviews_on_page()
            return reviews
        finally:
            if self.driver:
                self.driver.quit()


class ReviewWriter:
    def __init__(self, output_dir: str = "data", output_filename: str = "reviews.csv"):
        self.output_dir = output_dir
        self.output_filename = output_filename

    def write_csv(self, reviews: List[Review]) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, self.output_filename)
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["author_name", "rating", "published_at", "text"])
            writer.writeheader()
            for review in reviews:
                writer.writerow(asdict(review))
        return output_path


def main() -> None:
    load_dotenv()
    place_url = os.getenv("GMAP_PLACE_URL", "").strip()
    if not place_url:
        raise SystemExit("Please set GMAP_PLACE_URL in your .env file")

    max_reviews_env = os.getenv("MAX_REVIEWS", "100").strip()
    try:
        max_reviews = int(max_reviews_env)
    except ValueError:
        max_reviews = 100

    headless_env = os.getenv("HEADLESS", "true").strip().lower()
    headless = headless_env not in {"false", "0", "no"}

    scraper = GMapReviewScraper(place_url=place_url, headless=headless, max_reviews=max_reviews)
    reviews = scraper.scrape()

    writer = ReviewWriter(output_dir="data", output_filename="reviews.csv")
    output_path = writer.write_csv(reviews)

    print(f"Scraped {len(reviews)} reviews → {output_path}")


if __name__ == "__main__":
    main()
