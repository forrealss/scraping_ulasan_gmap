from typing import List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


def safe_get_text(root: WebElement, locator_candidates: List[Tuple[By, str]]) -> str:
    """Safely extract text from element using multiple locator candidates"""
    for by, selector in locator_candidates:
        try:
            elem = root.find_element(by, selector)
            text = elem.text.strip()
            if text:
                return text
        except Exception:
            continue
    return ""


def safe_get_attr(root: WebElement, locator_candidates: List[Tuple[By, str]], attr: str) -> str:
    """Safely extract attribute from element using multiple locator candidates"""
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


def extract_rating(aria_label: str) -> Optional[float]:
    """Extract rating value from aria-label string"""
    if not aria_label:
        return None
    
    # Examples: "5.0 stars", "Rated 4.5 out of 5"
    for token in aria_label.split():
        try:
            return float(token.replace(',', '.'))
        except ValueError:
            continue
    return None


def get_author_image_url(container: WebElement) -> str:
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