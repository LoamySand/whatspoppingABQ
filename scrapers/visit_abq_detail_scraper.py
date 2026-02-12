# scrapers/visit_abq_detail_scraper.py
"""
Enhanced scraper that clicks into event detail pages.
Extracts comprehensive event information including times, costs, sponsors.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging
import time
from datetime import datetime
import re
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def truncate_field(value: str, max_length: int) -> str:
    """
    Truncate a string field to max length.
    
    Args:
        value: String to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string
    """
    if not value:
        return value
    
    if len(value) > max_length:
        logger.warning(f"Truncating field from {len(value)} to {max_length} chars")
        return value[:max_length]
    
    return value

def scrape_events_with_details(max_pages: int = 3) -> List[Dict]:
    """
    Scrape events by clicking into detail pages for complete information.
    """
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        driver.get("https://www.visitabq.org/events/")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "listing-item"))
        )
        
        all_events = []
        
        for page_num in range(max_pages):
            logger.info(f"Scraping page {page_num + 1}")
            
            # Get all event links on current page
            try:
                event_links = driver.find_elements(By.CSS_SELECTOR, "a.title")
            except Exception:
                event_links = []
            
            if not event_links:
                logger.info("No event links found")
                break
            
            # Store URLs before clicking (to avoid stale element references)
            event_urls = []
            for link in event_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        event_urls.append(href)
                except Exception:
                    continue
            
            logger.info(f"Found {len(event_urls)} events on page {page_num + 1}")
            
            # Click into each event detail page and scrape
            for event_url in event_urls:
                try:
                    event_detail = scrape_event_detail(driver, event_url)
                    if event_detail:
                        is_valid, msg = validate_event(event_detail)
                        if is_valid:
                            all_events.append(event_detail)
                        else:
                            logger.warning(f"Invalid event: {msg}")
                except Exception as e:
                    logger.error(f"Error scraping event {event_url}: {e}")
                    continue
            
            # Return to listing page
            try:
                driver.get("https://www.visitabq.org/events/")
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "listing-item"))
                )
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Error returning to listing: {e}")
                break
            
            # Handle pagination
            if page_num < max_pages - 1:
                try:
                    # Keep this simple: try a concise set of CSS selectors and click the first match.
                    selectors = [
                        "a.pagination-next",
                        "a.next",
                        "li.next a",
                        ".pagination-next",
                        "a[rel='next']",
                        "a[aria-label='Next']"
                    ]

                    next_button = None
                    for sel in selectors:
                        try:
                            elems = driver.find_elements(By.CSS_SELECTOR, sel)
                            if elems:
                                next_button = elems[0]
                                logger.info(f"Found next button with selector: {sel}")
                                break
                        except Exception:
                            continue

                    if not next_button:
                        logger.info("Could not find next button, stopping pagination")
                        break

                    # Click and wait for listing items to be present again
                    driver.execute_script("arguments[0].click();", next_button)
                    try:
                        WebDriverWait(driver, 12).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "listing-item"))
                        )
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for events on page {page_num + 1}")
                        break

                    # brief stabilizing pause
                    time.sleep(1)

                except Exception as e:
                    logger.warning(f"Error clicking next button: {e}")
                    break
        
        logger.info(f"Total events scraped: {len(all_events)}")
        
        # Deduplicate
        seen = set()
        unique_events = []
        for event in all_events:
            key = (event.get('event_name'), event.get('event_start_date'), event.get('venue_name'))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        if len(unique_events) < len(all_events):
            logger.info(f"Removed {len(all_events) - len(unique_events)} duplicates")
        
        return unique_events
        
    finally:
        driver.quit()
        logger.info("Browser closed")


def scrape_event_detail(driver, url: str) -> Optional[Dict]:
    """
    Scrape detailed information from an event detail page.
    
    Args:
        driver: Selenium WebDriver
        url: Event detail page URL
        
    Returns:
        Event dictionary with detailed information
    """
    try:
        driver.get(url)
        
        # Wait for detail page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "detail-info"))
        )
        
        time.sleep(1)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Event name (from h1 or title)
        title_elem = soup.find('h1')
        event_name = title_elem.get_text(strip=True) if title_elem else None
        
        # Find detail info list
        detail_list = soup.find('ul', class_='detail-info')
        
        if not detail_list:
            logger.warning(f"No detail-info found for {url}")
            return None
        
        # Extract category from data-gtm-vars
        category = extract_category(detail_list)
        
        # Extract all fields
        fields = {}
        for li in detail_list.find_all('li'):
            data_name = li.get('data-name')
            if data_name:
                value_span = li.find('span', class_='info-list-value')
                if value_span:
                    fields[data_name] = value_span.get_text(strip=True)
        
        # Parse dates
        dates_str = fields.get('dates', '')
        event_start_date, event_end_date, is_multi_day = parse_dates(dates_str)
        
        # Parse times
        time_str = fields.get('time', '')
        event_start_time, event_end_time = parse_time_range(time_str)
        
        # Parse location/venue
        venue_name = fields.get('location', '')
        address = fields.get('address', '')
        
        # Parse sponsor
        sponsor = fields.get('host', '')
        
        # Parse cost
        price_str = fields.get('price', '')
        cost_min, cost_max, cost_description = parse_cost(price_str)
        
        # Contact info
        phone = fields.get('phone', '')
        email = fields.get('email', '')
        
        # URLs
        ticket_url = None
        website_url = None
        
        for li in detail_list.find_all('li', class_='website'):
            link = li.find('a')
            if link:
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                if 'ticket' in link_text.lower() or 'get tickets' in link_text.lower():
                    ticket_url = href
                elif 'website' in link_text.lower():
                    website_url = href
        
# Build event dictionary
        event = {
            'event_name': truncate_field(event_name, 255),
            'venue_name': truncate_field(venue_name, 255),
            'address': truncate_field(address, 500),
            'event_start_date': event_start_date,
            'event_end_date': event_end_date,
            'event_start_time': event_start_time,
            'event_end_time': event_end_time,
            'is_multi_day': is_multi_day,
            'category': truncate_field(category or 'General', 100),
            'sponsor': truncate_field(sponsor, 500),
            'cost_min': cost_min,
            'cost_max': cost_max,
            'cost_description': truncate_field(cost_description, 255),
            'phone': truncate_field(clean_phone(phone), 20),
            'email': truncate_field(clean_email(email), 255),
            'ticket_url': truncate_field(ticket_url, 1000),
            'website_url': truncate_field(website_url, 1000),
            'source_url': truncate_field(url, 1000),
            'latitude': None,
            'longitude': None,
            'expected_attendance': None
        }
        
        return event
        
    except Exception as e:
        logger.error(f"Error scraping detail page {url}: {e}")
        return None


def extract_category(detail_list) -> Optional[str]:
    """Extract category from data-gtm-vars attribute."""
    gtm_vars = detail_list.get('data-gtm-vars', '')
    
    # Look for crmCatSubcat in the JSON-like string
    match = re.search(r'"crmCatSubcat":\s*"([^"]+)"', gtm_vars)
    if match:
        category = match.group(1)
        # URL decode
        import urllib.parse
        category = urllib.parse.unquote(category)
        return category
    
    return None

def parse_dates(dates_str: str) -> tuple:
    """
    Parse date string into start/end dates.
    
    Examples:
        "February 13, 2026" -> (2026-02-13, 2026-02-13, False)
        "February 13, 2026, February 14, 2026" -> (2026-02-13, 2026-02-14, True)
        "Feb 11 - Mar 3" -> (2026-02-11, 2026-03-03, True)
    """
    if not dates_str:
        return None, None, False
    
    # Try to detect format and parse accordingly
    
    # Pattern 1: "Month Day, Year, Month Day, Year"
    # Example: "February 13, 2026, February 14, 2026"
    pattern1 = r'([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    matches = re.findall(pattern1, dates_str)
    
    if len(matches) >= 2:
        # Multi-day with full dates
        start_date = parse_single_date(matches[0])
        end_date = parse_single_date(matches[-1])
        is_multi_day = (end_date != start_date) if (start_date and end_date) else False
        return start_date, end_date, is_multi_day
    
    elif len(matches) == 1:
        # Single day with full date
        start_date = parse_single_date(matches[0])
        return start_date, start_date, False
    
    # Pattern 2: "Month Day - Month Day" (no year)
    # Example: "Feb 11 - Mar 3"
    pattern2 = r'([A-Za-z]+\s+\d{1,2})\s*-\s*([A-Za-z]+\s+\d{1,2})'
    match = re.match(pattern2, dates_str)
    
    if match:
        start_date = parse_single_date(match.group(1))
        end_date = parse_single_date(match.group(2))
        is_multi_day = (end_date != start_date) if (start_date and end_date) else False
        return start_date, end_date, is_multi_day
    
    # Pattern 3: Single date without year
    # Example: "February 13"
    pattern3 = r'([A-Za-z]+\s+\d{1,2})'
    match = re.match(pattern3, dates_str)
    
    if match:
        start_date = parse_single_date(match.group(1))
        return start_date, start_date, False
    
    # Fallback: try to parse the whole string
    start_date = parse_single_date(dates_str)
    return start_date, start_date, False

def parse_single_date(date_str: str) -> Optional[str]:
    """Parse a single date string to YYYY-MM-DD format."""
    if not date_str:
        return None
    
    current_year = datetime.now().year
    
    formats = [
        '%B %d, %Y',   # February 13, 2026
        '%b %d, %Y',   # Feb 13, 2026
        '%B %d',       # February 13
        '%b %d',       # Feb 13
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            
            # Add year if not in format
            if '%Y' not in fmt:
                dt = dt.replace(year=current_year)
                # If date is in past, assume next year
                if dt < datetime.now():
                    dt = dt.replace(year=current_year + 1)
            
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


def parse_time_range(time_str: str) -> tuple:
    """
    Parse time range string.
    
    Example: "7:00 PM to 9:30 PM" -> ("19:00:00", "21:30:00")
    """
    if not time_str:
        return None, None
    
    # Split on "to" or "-"
    parts = re.split(r'\s+to\s+|\s*-\s*', time_str, flags=re.IGNORECASE)
    
    start_time = parse_single_time(parts[0]) if len(parts) > 0 else None
    end_time = parse_single_time(parts[1]) if len(parts) > 1 else None
    
    return start_time, end_time


def parse_single_time(time_str: str) -> Optional[str]:
    """Parse single time string to HH:MM:SS format."""
    if not time_str:
        return None
    
    time_str = time_str.strip()
    
    # Match patterns like "7:00 PM" or "7 PM"
    match = re.match(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)', time_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3).upper()
        
        # Convert to 24-hour
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute:02d}:00"
    
    return None


def parse_cost(price_str: str) -> tuple:
    """
    Parse cost string.
    
    Examples:
        "$149.95" -> (149.95, 149.95, "$149.95")
        "Free" -> (0, 0, "Free")
        "$50-$100" -> (50, 100, "$50-$100")
    """
    if not price_str:
        return None, None, None
    
    price_str = price_str.strip()
    
    # Check for free
    if re.search(r'\bfree\b', price_str, re.IGNORECASE):
        return 0.0, 0.0, "Free"
    
    # Extract numbers
    amounts = re.findall(r'\$?\s*(\d+(?:\.\d{2})?)', price_str)
    
    if not amounts:
        return None, None, price_str
    
    amounts = [float(a) for a in amounts]
    
    cost_min = min(amounts)
    cost_max = max(amounts)
    
    return cost_min, cost_max, price_str


def clean_phone(phone_str: str) -> Optional[str]:
    """Extract and clean phone number."""
    if not phone_str:
        return None
    
    # Extract digits
    digits = re.findall(r'\d', phone_str)
    
    if len(digits) >= 10:
        return ''.join(digits[-10:])  # Last 10 digits
    
    return phone_str.strip() if phone_str.strip() else None


def clean_email(email_str: str) -> Optional[str]:
    """Extract and clean email."""
    if not email_str:
        return None
    
    # Find email pattern
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_str)
    if match:
        return match.group(0)
    
    return email_str.strip() if email_str.strip() else None


def validate_event(event: Dict) -> tuple:
    """Validate event has required fields."""
    if not event.get('event_name'):
        return False, "Missing event_name"
    
    if not event.get('event_start_date'):
        return False, "Missing event_start_date"
    
    return True, "Valid"


if __name__ == "__main__":
    """
    Test the enhanced scraper
    """
    print("=" * 70)
    print("Enhanced Event Scraper - Test Run")
    print("=" * 70)
    print()
    
    print("This will scrape 1 page with detailed event information")
    print("Estimated time: 2-3 minutes")
    print()
    
    events = scrape_events_with_details(max_pages=1)
    
    print(f"\n✓ Scraped {len(events)} events with details")
    print()
    
    if events:
        print("Sample event (full details):")
        print("-" * 70)
        for key, value in events[0].items():
            if value:
                print(f"  {key}: {value}")
        print()
        
        # Validation
        valid = sum(1 for e in events if validate_event(e)[0])
        print(f"Valid events: {valid}/{len(events)}")
        
        # Statistics
        multi_day = sum(1 for e in events if e.get('is_multi_day'))
        with_cost = sum(1 for e in events if e.get('cost_description'))
        with_sponsor = sum(1 for e in events if e.get('sponsor'))
        with_times = sum(1 for e in events if e.get('event_start_time'))
        
        print()
        print("Data Quality:")
        print(f"  Multi-day events: {multi_day}")
        print(f"  With cost info: {with_cost}")
        print(f"  With sponsor: {with_sponsor}")
        print(f"  With start time: {with_times}")
    
    print()
    print("=" * 70)