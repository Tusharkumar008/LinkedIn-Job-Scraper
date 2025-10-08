import time
import re
import os
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# -------------------- CONFIGURATION --------------------
# ASK USER FOR INPUTS
print("=" * 60)
print("LinkedIn Company Mention Scraper")
print("=" * 60)

MENTION = input("Enter the company name to search for: ").strip()
if not MENTION:
    print("Error: Company name cannot be empty!")
    exit()

time_filter_input = input("Enter the number of days to filter (e.g., 7 for last 7 days): ").strip()
try:
    TIME_FILTER = int(time_filter_input)
    if TIME_FILTER <= 0:
        print("Error: Number of days must be positive!")
        exit()
except ValueError:
    print("Error: Please enter a valid number for days!")
    exit()

scroll_count_input = input("Enter the number of times to scroll (e.g., 50): ").strip()
try:
    SCROLL_COUNT = int(scroll_count_input)
    if SCROLL_COUNT <= 0:
        print("Error: Scroll count must be positive!")
        exit()
except ValueError:
    print("Error: Please enter a valid number for scroll count!")
    exit()

print(f"\nSearching for mentions of: {MENTION}")
print(f"Time filter: Last {TIME_FILTER} days")
print(f"Scroll count: {SCROLL_COUNT}")
print("=" * 60)

# -------------------- DRIVER SETUP ---------------------
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Automatically download and use the correct ChromeDriver version
print("Setting up ChromeDriver (automatically downloading correct version)...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# ADD THIS FUNCTION TO EXPAND "SEE MORE" SECTIONS
def expand_see_more_sections():
    """Expand all 'See more' sections on the current page"""
    see_more_selectors = [
        "button[aria-label*='see more']",
        "button[aria-label*='See more']",
        "button.feed-shared-inline-show-more-text__see-more-less-toggle",
        "button[data-tracking-control-name='public_post_feed-text-see-more']",
        ".feed-shared-text__see-more",
        "span.feed-shared-text__see-more-link",
        "button:contains('See more')",
        "button:contains('see more')",
        "[aria-expanded='false']"
    ]
    
    expanded_count = 0
    for selector in see_more_selectors:
        try:
            see_more_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in see_more_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].click();", button)
                        expanded_count += 1
                        time.sleep(0.5)  # Small delay between clicks
                except Exception as e:
                    continue
        except Exception as e:
            continue
    
    print(f"Expanded {expanded_count} 'See more' sections")
    return expanded_count

try:
    # LOGIN FIRST
    print("\nPlease login to LinkedIn manually in the opened browser...")
    driver.get("https://www.linkedin.com/login")
    input("Press Enter after you have logged in and are ready to continue...")

    # SEARCH FOR MENTIONS (NOT HASHTAGS) - Alternative approach
    print(f"\nSearching for mentions: @{MENTION}")
    
    # Try different search approaches for mentions
    search_urls = [
        f"https://www.linkedin.com/search/results/content/?keywords=%22%40{MENTION}%22&origin=SWITCH_SEARCH_VERTICAL",  # Quoted mention
        f"https://www.linkedin.com/search/results/content/?keywords=%40{MENTION}&searchId=&origin=SWITCH_SEARCH_VERTICAL",  # Standard mention
        f"https://www.linkedin.com/search/results/all/?keywords=%40{MENTION}&origin=GLOBAL_SEARCH_HEADER"  # Global search
    ]
    
    success = False
    for search_url in search_urls:
        try:
            driver.get(search_url)
            time.sleep(3)
            
            # Check if we got results
            if "No results" not in driver.page_source and "0 results" not in driver.page_source:
                print(f"Successfully found results with URL: {search_url}")
                success = True
                break
        except:
            continue
    
    if not success:
        print("Warning: May not have found optimal search results. Proceeding with last attempt...")
    
    # ADDITIONAL FILTERING: Click on "Posts" filter if available
    try:
        posts_filter = driver.find_element(By.XPATH, "//button[contains(text(), 'Posts') or contains(text(), 'posts')]")
        if posts_filter:
            posts_filter.click()
            time.sleep(2)
    except:
        pass
    
    # SCROLL TO LOAD POSTS WITH SEE MORE EXPANSION
    print(f"\nScrolling to load posts ({SCROLL_COUNT} times)...")
    for i in range(SCROLL_COUNT):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"Scroll {i+1}/{SCROLL_COUNT}")
        
        # EXPAND "SEE MORE" SECTIONS AFTER EACH SCROLL
        expand_see_more_sections()
        
        # INCREASED WAIT TIME FOR BETTER POST READING
        time.sleep(5)  # Increased from 3 to 5 seconds

    # FINAL EXPANSION OF ALL "SEE MORE" SECTIONS
    print("\nFinal expansion of all 'See more' sections...")
    expand_see_more_sections()
    
    # ADDITIONAL WAIT TO ENSURE ALL CONTENT IS LOADED
    time.sleep(3)

    # EXTRACT POSTS
    print("\nExtracting posts data...")
    posts_data = []
    
    # Try to find posts with different selectors
    post_selectors = [
        '[data-urn*="urn:li:activity"]',
        '.feed-shared-update-v2',
        '.update-components-actor',
        'article'
    ]

    posts = []
    for selector in post_selectors:
        posts = driver.find_elements(By.CSS_SELECTOR, selector)
        if posts:
            print(f"Found {len(posts)} posts using selector: {selector}")
            break
    
    if not posts:
        print("No posts found with any selector")
        print("Current page title:", driver.title)
        print("Current URL:", driver.current_url)
    
    print(f"Processing {len(posts)} posts...")

    for i, post in enumerate(posts):
        try:
            # EXPAND "SEE MORE" IN INDIVIDUAL POSTS IF MISSED
            try:
                see_more_in_post = post.find_elements(By.CSS_SELECTOR, 
                    "button[aria-label*='see more'], .feed-shared-text__see-more, button.feed-shared-inline-show-more-text__see-more-less-toggle")
                for btn in see_more_in_post:
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
            except:
                pass

            # EXTRACT POST TEXT WITH BETTER SELECTORS
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

            # Try to get relative time text (e.g. "2w", "3 days ago")
            time_text = ""
            try:
                time_elem = post.find_element(By.XPATH, ".//span[contains(text(),'ago')]")
                time_text = time_elem.text.lower().strip()
            except:
                # fallback: sometimes it's in .visually-hidden or time tag
                for t in post.find_elements(By.CSS_SELECTOR, "time, .visually-hidden"):
                    if t.text and any(k in t.text.lower() for k in ["ago", "h", "d", "w", "week", "day"]):
                        time_text = t.text.lower().strip()
                        break

            if not time_text:
                continue

            # Parse date
            post_date = None
            if "minute" in time_text or "hour" in time_text:
                post_date = datetime.today()
            elif "day" in time_text:
                days = int(time_text.split("day")[0].strip())
                post_date = datetime.today() - timedelta(days=days)
            elif "week" in time_text:
                weeks = int(time_text.split("week")[0].strip())
                post_date = datetime.today() - timedelta(weeks=weeks)
            elif "d" in time_text:
                days = int(''.join(filter(str.isdigit, time_text)))
                post_date = datetime.today() - timedelta(days=days)
            elif "w" in time_text:
                weeks = int(''.join(filter(str.isdigit, time_text)))
                post_date = datetime.today() - timedelta(weeks=weeks)
            else:
                continue
                
            # Filter by your time window
            if datetime.today() - post_date > timedelta(days=TIME_FILTER):
                continue

            # Extract post URL — build it manually from data-urn if needed
            post_urn = post.get_attribute("data-urn")
            if post_urn:
                post_link = f"https://www.linkedin.com/feed/update/{post_urn.split(':')[-1]}"
            else:
                # fallback if data-urn doesn't exist
                post_link = ""
                for link in post.find_elements(By.CSS_SELECTOR, "a"):
                    href = link.get_attribute("href")
                    if href and 'activity' in href:
                        post_link = href
                        break

            if not post_link:
                continue

            # EXTRACT EMAILS FROM POST TEXT (after validation)
            found_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", post_text)
            emails_str = ", ".join(found_emails) if found_emails else ""

            # Add post to result with expanded content
            posts_data.append({
                "Post Date": post_date.strftime('%Y-%m-%d'),
                "Post Link": post_link,
                "Time Text": time_text,
                "Post Text": post_text[:500] + "..." if len(post_text) > 500 else post_text,  # Limit text length
                "Emails Found": emails_str
            })
            print(f" Found post {len(posts_data)}: {post_date.strftime('%Y-%m-%d')} — {post_link}")

        except Exception as e:
            print(f" Error processing post {i+1}: {str(e)}")
            continue

    # SAVE TO EXCEL
    if posts_data:
        df = pd.DataFrame(posts_data)
        filename = f"linkedin_{MENTION}_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False)
        print(f"\n{'='*60}")
        print(f"Scraping complete! {len(df)} posts saved to {filename}")
        print(f"File location: {os.path.abspath(filename)}")
        print(f"{'='*60}")
        
        # Try to open the file
        try:
            os.startfile(filename)
            print("Opening Excel file...")
        except Exception as e:
            print(f"Could not auto-open file: {e}")
    else:
        print("\nNo posts found matching the criteria")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\nClosing browser...")
    driver.quit()