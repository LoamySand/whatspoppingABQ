# scrapers/visit_abq_selenium_scraper.py
"""
Selenium-based scraper for Visit Albuquerque (handles JavaScript)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging
import time
from datetime import datetime
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_events_selenium(url: str = None, max_pages: int = 3, max_wait: int = 10) -> List[Dict]:
    """
    Scrape events using Selenium (handles JavaScript rendering)
    
    Args:
        url: URL to scrape (default: search-calendar)
        max_pages: Maximum number of pages to scrape (default 3)
        max_wait: Maximum seconds to wait for page load
        
    Returns:
        List of event dictionaries
    """
    if url is None:
        url = "https://www.visitalbuquerque.org/abq365/events/search-calendar/"
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--headless')  # Run without opening browser window
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    logger.info("Starting Chrome browser...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    all_events = []
    
    try:
        for page_num in range(1, max_pages + 1):
            # Construct page URL
            if page_num == 1:
                page_url = url
            else:
                # Check URL structure for pagination
                separator = '&' if '?' in url else '?'
                page_url = f"{url}{separator}page={page_num}"
            
            logger.info(f"Loading page {page_num}: {page_url}")
            driver.get(page_url)
            
            # Wait for page to load
            logger.info(f"Waiting for events to load on page {page_num}...")
            
            try:
                WebDriverWait(driver, max_wait).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "listing-item"))
                )
            except:
                try:
                    WebDriverWait(driver, max_wait).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "title"))
                    )
                except:
                    logger.warning(f"Timeout waiting for elements on page {page_num}")
                    break
            
            # Let page fully render
            time.sleep(2)
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try to find events
            event_elements = soup.find_all('li', class_='listing-item')
            
            if not event_elements:
                event_elements = soup.find_all('li', class_='list-item')
            
            if not event_elements:
                logger.info(f"No events found on page {page_num}, stopping pagination")
                break
            
            logger.info(f"Found {len(event_elements)} events on page {page_num}")
            
            # Parse events from this page
            page_events = []
            for element in event_elements:
                try:
                    event = parse_selenium_event(element)
                    if event:
                        page_events.append(event)
                except Exception as e:
                    logger.warning(f"Error parsing event: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(page_events)} events from page {page_num}")
            all_events.extend(page_events)
            
            # Check if there's a next page button
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "a.next, li.next a, .pagination-next")
                if not next_button or 'disabled' in next_button.get_attribute('class'):
                    logger.info("No more pages available")
                    break
            except:
                logger.info("Could not find next page button, stopping pagination")
                break
        
        logger.info(f"Total events scraped across all pages: {len(all_events)}")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        
    finally:
        driver.quit()
        logger.info("Browser closed")
    
    return all_events


def parse_selenium_event(element) -> Dict:
    """Parse event from Selenium-rendered HTML"""
    
    # Event name
    title_elem = element.find('a', class_='title')
    if not title_elem:
        title_elem = element.find('div', class_='title')
    event_name = title_elem.get_text(strip=True) if title_elem else None
    
    # Event URL
    event_url = title_elem.get('href') if title_elem and title_elem.name == 'a' else None
    if event_url and not event_url.startswith('http'):
        event_url = 'https://www.visitalbuquerque.org' + event_url
    
    # Venue
    venue_elem = element.find('a', class_='markerLink')
    if not venue_elem:
        venue_elem = element.find('div', class_='address')
    venue_name = venue_elem.get_text(strip=True) if venue_elem else None
    if venue_name:
        venue_name = venue_name.replace('', '').strip()
    
    # Date
    date_block = element.find('div', class_='image-date-block')
    if not date_block:
        date_block = element.find('span', class_='date')
    
    date_str = None
    if date_block:
        date_span = date_block.find('span')
        if date_span:
            date_str = date_span.get_text(strip=True)
        else:
            date_str = date_block.get_text(strip=True)
    
    # Parse date
    event_date = parse_date_simple(date_str) if date_str else None
    
    # Category
    category = categorize_event_simple(event_name) if event_name else 'General'
    
    return {
        'event_name': event_name,
        'venue_name': venue_name,
        'event_date': event_date,
        'event_time': None,
        'category': category,
        'latitude': None,
        'longitude': None,
        'source_url': event_url,
        'expected_attendance': None
    }


def parse_date_simple(date_str: str) -> str:
    """Simple date parser for Selenium output"""
    if not date_str:
        return None
    
    # Handle ranges
    if ' - ' in date_str:
        date_str = date_str.split(' - ')[0].strip()
    
    current_year = datetime.now().year
    
    # Try "Feb 11" format
    try:
        dt = datetime.strptime(date_str.strip(), '%b %d')
        dt = dt.replace(year=current_year)
        if dt < datetime.now():
            dt = dt.replace(year=current_year + 1)
        return dt.strftime('%Y-%m-%d')
    except:
        pass
    
    return None


def categorize_event_simple(event_name: str) -> str:
    """Simple categorization"""
    if not event_name:
        return 'General'
    
    name_lower = event_name.lower()
    
    if 'basketball' in name_lower or 'baseball' in name_lower or 'sports' in name_lower:
        return 'Sports'
    elif 'concert' in name_lower or 'music' in name_lower:
        return 'Music'
    elif 'festival' in name_lower or 'fiesta' in name_lower:
        return 'Festival'
    else:
        return 'General'


def validate_event(event: Dict) -> Tuple[bool, str]:
    """Validate event has required fields"""
    if not event.get('event_name'):
        return False, "Missing event_name"
    if not event.get('event_date'):
        return False, "Missing event_date"
    return True, "Valid"


if __name__ == "__main__":
    print("=" * 60)
    print("Selenium Scraper Test")
    print("=" * 60)
    print()
    
    # Scrape multiple pages (default 3)
    print("Scraping up to 3 pages of events...")
    events = scrape_events_selenium(max_pages=3)
    
    print(f"\nTotal events scraped: {len(events)}")
    print()
    
    if events:
        print("First 5 events:")
        print("-" * 60)
        for i, event in enumerate(events[:5], 1):
            print(f"{i}. {event['event_name']}")
            print(f"   Date: {event['event_date']}")
            print(f"   Venue: {event['venue_name']}")
            print(f"   Category: {event['category']}")
            print()
        
        # Show breakdown by category
        from collections import Counter
        categories = Counter(e['category'] for e in events)
        print("Events by category:")
        print("-" * 60)
        for category, count in categories.most_common():
            print(f"  {category}: {count}")
        print()
        
        # Validate
        valid = sum(1 for e in events if validate_event(e)[0])
        invalid = len(events) - valid
        
        print(f"Validation Results:")
        print(f"  Valid: {valid}")
        print(f"  Invalid: {invalid}")
        
        if invalid > 0:
            print("\nInvalid events:")
            for event in events:
                is_valid, msg = validate_event(event)
                if not is_valid:
                    print(f"  - {event.get('event_name', 'Unknown')}: {msg}")
    else:
        print("No events found.")
    
    print()
    print("=" * 60)