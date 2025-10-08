import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class LinkedInScraper:
    def __init__(self, mention, time_filter, scroll_count):
        """
        Initialize the scraper with parameters
        
        Args:
            mention (str): Company name to search for
            time_filter (int): Number of days to filter posts
            scroll_count (int): Number of times to scroll the page
        """
        self.mention = mention
        self.time_filter = time_filter
        self.scroll_count = scroll_count
        self.driver = None
        self.posts_data = []
        
    def setup_driver(self):
        """Set up the Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def expand_see_more_sections(self):
        """Expand all 'See more' sections on the current page"""
        see_more_selectors = [
            "button[aria-label*='see more']",
            "button[aria-label*='See more']",
            "button.feed-shared-inline-show-more-text__see-more-less-toggle",
            "button[data-tracking-control-name='public_post_feed-text-see-more']",
            ".feed-shared-text__see-more",
            "span.feed-shared-text__see-more-link",
            "[aria-expanded='false']"
        ]
        
        expanded_count = 0
        for selector in see_more_selectors:
            try:
                see_more_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for button in see_more_buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            self.driver.execute_script("arguments[0].click();", button)
                            expanded_count += 1
                            time.sleep(0.5)
                    except:
                        continue
            except:
                continue
        
        print(f"Expanded {expanded_count} 'See more' sections")
        return expanded_count
    
    def login(self):
        """Open LinkedIn login page and wait for manual login"""
        print("\nOpening LinkedIn login page...")
        self.driver.get("https://www.linkedin.com/login")
        
        # Wait for user to login manually
        print("Waiting for login... (checking every 5 seconds)")
        logged_in = False
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while not logged_in and (time.time() - start_time) < max_wait_time:
            time.sleep(5)
            
            # Check if user is logged in by looking for feed or home URL
            current_url = self.driver.current_url
            if 'feed' in current_url or 'mynetwork' in current_url or 'jobs' in current_url:
                logged_in = True
                print("Login detected!")
                break
            
            # Also check for feed elements
            try:
                self.driver.find_element(By.CSS_SELECTOR, '.global-nav')
                logged_in = True
                print("Login detected!")
                break
            except:
                pass
        
        if not logged_in:
            raise Exception("Login timeout - please login within 5 minutes")
    
    def search_mentions(self):
        """Search for company mentions on LinkedIn"""
        print(f"\nSearching for mentions: @{self.mention}")
        
        search_urls = [
            f"https://www.linkedin.com/search/results/content/?keywords=%22%40{self.mention}%22&origin=SWITCH_SEARCH_VERTICAL",
            f"https://www.linkedin.com/search/results/content/?keywords=%40{self.mention}&searchId=&origin=SWITCH_SEARCH_VERTICAL",
            f"https://www.linkedin.com/search/results/all/?keywords=%40{self.mention}&origin=GLOBAL_SEARCH_HEADER"
        ]
        
        success = False
        for search_url in search_urls:
            try:
                self.driver.get(search_url)
                time.sleep(3)
                
                if "No results" not in self.driver.page_source and "0 results" not in self.driver.page_source:
                    print(f"Successfully found results")
                    success = True
                    break
            except:
                continue
        
        if not success:
            print("Warning: May not have found optimal search results. Proceeding...")
        
        # Try to click on "Posts" filter
        try:
            posts_filter = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Posts') or contains(text(), 'posts')]")
            if posts_filter:
                posts_filter.click()
                time.sleep(2)
        except:
            pass
    
    def scroll_and_load(self):
        """Scroll the page to load more posts"""
        print(f"\nScrolling to load posts ({self.scroll_count} times)...")
        
        for i in range(self.scroll_count):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"Scroll {i+1}/{self.scroll_count}")
            
            self.expand_see_more_sections()
            time.sleep(5)
        
        # Final expansion
        print("\nFinal expansion of all 'See more' sections...")
        self.expand_see_more_sections()
        time.sleep(3)
    
    def extract_posts(self):
        """Extract post data from the page"""
        print("\nExtracting posts data...")
        
        post_selectors = [
            '[data-urn*="urn:li:activity"]',
            '.feed-shared-update-v2',
            '.update-components-actor',
            'article'
        ]
        
        posts = []
        for selector in post_selectors:
            posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if posts:
                print(f"Found {len(posts)} posts using selector: {selector}")
                break
        
        if not posts:
            print("No posts found with any selector")
            return []
        
        print(f"Processing {len(posts)} posts...")
        
        for i, post in enumerate(posts):
            try:
                # Expand see more in individual posts
                try:
                    see_more_in_post = post.find_elements(By.CSS_SELECTOR, 
                        "button[aria-label*='see more'], .feed-shared-text__see-more, button.feed-shared-inline-show-more-text__see-more-less-toggle")
                    for btn in see_more_in_post:
                        if btn.is_displayed() and btn.is_enabled():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.5)
                except:
                    pass
                
                # Extract post text
                post_text = ""
                text_selectors = [
                    ".feed-shared-text__text-view",
                    ".feed-shared-update-v2__description",
                    ".update-components-text",
                    ".feed-shared-text",
                    "[data-test-id='main-feed-activity-card'] .break-words"
                ]
                
                for text_selector in text_selectors:
                    try:
                        text_element = post.find_element(By.CSS_SELECTOR, text_selector)
                        post_text = text_element.text.strip()
                        if post_text:
                            break
                    except:
                        continue
                
                # Extract time text
                time_text = ""
                try:
                    time_elem = post.find_element(By.XPATH, ".//span[contains(text(),'ago')]")
                    time_text = time_elem.text.lower().strip()
                except:
                    for t in post.find_elements(By.CSS_SELECTOR, "time, .visually-hidden"):
                        if t.text and any(k in t.text.lower() for k in ["ago", "h", "d", "w", "week", "day"]):
                            time_text = t.text.lower().strip()
                            break
                
                if not time_text:
                    continue
                
                # Parse date
                post_date = self.parse_date(time_text)
                if not post_date:
                    continue
                
                # Filter by time window
                if datetime.today() - post_date > timedelta(days=self.time_filter):
                    continue
                
                # Extract post URL
                post_urn = post.get_attribute("data-urn")
                if post_urn:
                    post_link = f"https://www.linkedin.com/feed/update/{post_urn.split(':')[-1]}"
                else:
                    post_link = ""
                    for link in post.find_elements(By.CSS_SELECTOR, "a"):
                        href = link.get_attribute("href")
                        if href and 'activity' in href:
                            post_link = href
                            break
                
                if not post_link:
                    continue
                
                # Extract emails
                found_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", post_text)
                emails_str = ", ".join(found_emails) if found_emails else ""
                
                # Add to results
                self.posts_data.append({
                    "Post Date": post_date.strftime('%Y-%m-%d'),
                    "Post Link": post_link,
                    "Time Text": time_text,
                    "Post Text": post_text[:500] + "..." if len(post_text) > 500 else post_text,
                    "Emails Found": emails_str
                })
                
                print(f"Found post {len(self.posts_data)}: {post_date.strftime('%Y-%m-%d')} — {post_link}")
                
            except Exception as e:
                print(f"Error processing post {i+1}: {str(e)}")
                continue
        
        return self.posts_data
    
    def parse_date(self, time_text):
        """Parse date from time text"""
        try:
            if "minute" in time_text or "hour" in time_text:
                return datetime.today()
            elif "day" in time_text:
                days = int(time_text.split("day")[0].strip())
                return datetime.today() - timedelta(days=days)
            elif "week" in time_text:
                weeks = int(time_text.split("week")[0].strip())
                return datetime.today() - timedelta(weeks=weeks)
            elif "d" in time_text:
                days = int(''.join(filter(str.isdigit, time_text)))
                return datetime.today() - timedelta(days=days)
            elif "w" in time_text:
                weeks = int(''.join(filter(str.isdigit, time_text)))
                return datetime.today() - timedelta(weeks=weeks)
        except:
            pass
        return None
    
    def run(self):
        """Main execution method"""
        try:
            self.setup_driver()
            self.login()
            self.search_mentions()
            self.scroll_and_load()
            results = self.extract_posts()
            
            print(f"\nScraping complete! Found {len(results)} posts")
            return results
            
        except Exception as e:
            print(f"\nError during scraping: {e}")
            raise
        finally:
            if self.driver:
                print("\nClosing browser...")
                self.driver.quit()