import pandas as pd
import time
import random
import os
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from config import get_activeplayer_games, get_scraping_config, get_browser_config

# Get configuration from environment
scraping_config = get_scraping_config()
browser_config = get_browser_config()

# Constants
REQUEST_DELAY_MIN = scraping_config['REQUEST_DELAY_MIN']
REQUEST_DELAY_MAX = scraping_config['REQUEST_DELAY_MAX']
PAGE_LOAD_TIMEOUT = scraping_config['PAGE_LOAD_TIMEOUT']
MAX_RETRIES = scraping_config['MAX_RETRIES']

# Get games from configuration
activeplayer_games = get_activeplayer_games()


def setup_driver() -> webdriver.Chrome:
    """Set up Chrome driver with anti-detection measures.
    
    Returns:
        Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    
    # Anti-detection measures
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set user agent from configuration
    chrome_options.add_argument(f"--user-agent={browser_config['USER_AGENT']}")
    
    # Set window size from configuration
    chrome_options.add_argument(f"--window-size={browser_config['WINDOW_SIZE']}")
    
    # Add headless mode if configured
    if browser_config['HEADLESS_MODE']:
        chrome_options.add_argument("--headless")
    
    # Additional anti-detection
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    # Add more realistic browser behavior
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    # Initialize driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Set page load timeout
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    return driver


def parse_number_with_commas(text: str) -> float:
    """Parse a number that may contain commas, K, M, B suffixes."""
    if not text or text.strip() == '':
        return 0.0
    
    # Remove commas and any percentage signs
    cleaned = text.replace(',', '').replace('%', '').strip().lower()
    
    # Handle K, M, B suffixes
    multiplier = 1
    if cleaned.endswith('k'):
        multiplier = 1000
        cleaned = cleaned[:-1]
    elif cleaned.endswith('m'):
        multiplier = 1000000
        cleaned = cleaned[:-1]
    elif cleaned.endswith('b'):
        multiplier = 1000000000
        cleaned = cleaned[:-1]
    
    try:
        return float(cleaned) * multiplier
    except ValueError:
        return 0.0


def scrape_activeplayer(driver: webdriver.Chrome, game_slug: str, game_name: str) -> List[List]:
    """Scrape ActivePlayer data for a given game using Selenium.
    
    Args:
        driver: Chrome WebDriver instance
        game_slug: ActivePlayer slug for the game
        game_name: Name of the game
        
    Returns:
        List of lists containing [date, game_name, current_players, peak_players]
    """
    url = f"https://activeplayer.io/{game_slug}/"
    data = []
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Loading {game_name} page... (attempt {attempt + 1}/{MAX_RETRIES})")
            driver.get(url)
            
            # Wait a bit for page to load
            time.sleep(8)
            
            # Look for player count elements
            player_selectors = [
                ".player-count",
                ".current-players",
                ".live-players",
                "[data-testid='player-count']",
                ".stats .number",
                ".metric .value",
                ".player-stats .count",
                ".game-stats .players",
                ".live-stats .current",
                ".dashboard .players"
            ]
            
            current_players = 0
            peak_players = 0
            
            # Try to find current player count
            for selector in player_selectors:
                try:
                    wait = WebDriverWait(driver, 10)
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    current_players = parse_number_with_commas(element.text)
                    print(f"    Found current players with selector: {selector} = {current_players}")
                    break
                except TimeoutException:
                    continue
            
            # Look for peak players or daily/monthly stats
            peak_selectors = [
                ".peak-players",
                ".daily-peak",
                ".monthly-peak",
                ".highest-players",
                ".max-players",
                ".stats .peak",
                ".metric .peak",
                ".player-stats .peak",
                ".game-stats .peak",
                ".live-stats .peak"
            ]
            
            for selector in peak_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    peak_players = parse_number_with_commas(element.text)
                    print(f"    Found peak players with selector: {selector} = {peak_players}")
                    break
                except NoSuchElementException:
                    continue
            
            # If we found any data, add it
            if current_players > 0 or peak_players > 0:
                # Get current date
                from datetime import datetime
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                data.append([current_date, game_name, current_players, peak_players])
                print(f"    ✅ Added data: Date={current_date}, Current={current_players}, Peak={peak_players}")
            else:
                print(f"    ⚠️  No player data found for {game_name}")
                
                # Debug: Let's see what's on the page
                if attempt == 0:  # Only on first attempt
                    print(f"    🔍 Page title: {driver.title}")
                    # Look for any numbers on the page
                    all_elements = driver.find_elements(By.XPATH, "//*[contains(text(), ',') or contains(text(), 'K') or contains(text(), 'M')]")
                    print(f"    📊 Found {len(all_elements)} elements with numbers")
                    for i, elem in enumerate(all_elements[:5]):  # Show first 5
                        print(f"      Element {i+1}: {elem.text}")
            
            # If we got here successfully, break out of retry loop
            break
                    
        except TimeoutException:
            print(f"  ⚠️  Timeout loading {game_name} page (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                print(f"  🔄 Retrying in 15 seconds...")
                time.sleep(15)
            else:
                print(f"  ❌ Failed to load {game_name} after {MAX_RETRIES} attempts")
                return []
        except Exception as e:
            print(f"  ❌ Error scraping {game_name} (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"  🔄 Retrying in 10 seconds...")
                time.sleep(10)
            else:
                return []
    
    print(f"  ✅ Successfully scraped {len(data)} records for {game_name}")
    return data


def random_delay() -> None:
    """Add random delay between requests to avoid detection."""
    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    print(f"  Waiting {delay:.1f} seconds...")
    time.sleep(delay)


def scrape_activeplayer_games() -> pd.DataFrame:
    """Main function to scrape all ActivePlayer games and return DataFrame."""
    print("🚀 Starting ActivePlayer scraper with Selenium...")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    driver = None
    try:
        # Set up the driver
        print("📱 Setting up Chrome driver...")
        driver = setup_driver()
        
        # Add initial delay to avoid immediate rate limiting
        print("⏳ Waiting 10 seconds before starting...")
        time.sleep(10)
        
        # Scrape all games
        all_data = []
        total_games = len(activeplayer_games)
        successful_games = 0
        
        for i, (game, game_slug) in enumerate(activeplayer_games.items(), 1):
            print(f"\n[{i}/{total_games}] Scraping {game}...")
            
            game_data = scrape_activeplayer(driver, game_slug, game)
            if game_data:
                all_data.extend(game_data)
                successful_games += 1
            
            # Add random delay between requests (except for the last game)
            if i < total_games:
                random_delay()
        
        # Convert to DataFrame and save
        if all_data:
            df = pd.DataFrame(all_data, columns=["Month", "Game", "Current Players", "Peak Players"])
            output_file = os.path.join("data", "activeplayer_current_counts.csv")
            df.to_csv(output_file, index=False)
            print(f"\n✅ Successfully scraped {len(all_data)} records from {successful_games}/{total_games} games")
            print(f"📁 Data saved to {output_file}")
            
            # Show some sample data
            print("\n📊 Sample of scraped data:")
            print(df.head(10))
            
            # Show summary by game
            print("\n📈 Summary by game (Current Players):")
            game_summary = df.groupby('Game')['Current Players'].max().sort_values(ascending=False)
            print(game_summary.head(15))
            
            return df
        else:
            print("\n❌ No data was scraped successfully")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return pd.DataFrame()
    finally:
        # Always close the driver
        if driver:
            print("\n🔒 Closing browser...")
            driver.quit()


if __name__ == "__main__":
    scrape_activeplayer_games() 