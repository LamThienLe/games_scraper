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
from config import get_steam_games, get_scraping_config, get_browser_config

# Get configuration from environment
scraping_config = get_scraping_config()
browser_config = get_browser_config()

# Constants
REQUEST_DELAY_MIN = scraping_config['REQUEST_DELAY_MIN']
REQUEST_DELAY_MAX = scraping_config['REQUEST_DELAY_MAX']
PAGE_LOAD_TIMEOUT = scraping_config['PAGE_LOAD_TIMEOUT']
MAX_RETRIES = scraping_config['MAX_RETRIES']

# Get games from configuration
steam_games = {game: int(app_id) for game, app_id in get_steam_games().items()}


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
    
    # Remove CSS/JS disabling as it might cause issues
    # chrome_options.add_argument("--disable-images")
    # chrome_options.add_argument("--disable-css")
    
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
    """Parse a number that may contain commas and percentage signs."""
    if not text or text.strip() == '':
        return 0.0
    
    # Remove commas and any percentage signs
    cleaned = text.replace(',', '').replace('%', '').strip()
    
    # Handle percentage changes (like +872.4, -17128.7)
    if cleaned.startswith('+') or cleaned.startswith('-'):
        # This is a percentage change, not an absolute number
        return 0.0
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def scrape_steamcharts(driver: webdriver.Chrome, app_id: int, game_name: str) -> List[List]:
    """Scrape Steam Charts data for a given game using Selenium.
    
    Args:
        driver: Chrome WebDriver instance
        app_id: Steam App ID for the game
        game_name: Name of the game
        
    Returns:
        List of lists containing [month, game_name, avg_players, peak_players]
    """
    url = f"https://steamcharts.com/app/{app_id}#All"
    data = []
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Loading {game_name} page... (attempt {attempt + 1}/{MAX_RETRIES})")
            driver.get(url)
            
            # Wait a bit for page to load
            time.sleep(8)  # Increased wait time
            
            # Try different table selectors
            table_selectors = [
                "table.common-table",
                "table",
                ".common-table",
                "#app-charts table",
                ".app-charts table"
            ]
            
            table = None
            for selector in table_selectors:
                try:
                    wait = WebDriverWait(driver, 15)  # Increased timeout
                    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"    Found table with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not table:
                print(f"    ❌ No table found. Page title: {driver.title}")
                if attempt < MAX_RETRIES - 1:
                    print(f"    🔄 Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                return []
            
            # Find all rows in the table
            rows = table.find_elements(By.TAG_NAME, "tr")
            print(f"    📋 Found {len(rows)} rows in table")
            
            # First, let's examine the header to understand the column structure
            if rows:
                header_row = rows[0]
                header_cells = header_row.find_elements(By.TAG_NAME, "th")
                if not header_cells:
                    header_cells = header_row.find_elements(By.TAG_NAME, "td")
                
                print(f"    📊 Table headers: {[cell.text.strip() for cell in header_cells]}")
            
            # Look for the correct columns - we need to find columns with actual player counts
            # Steam Charts typically has: Month, Avg. Players, Peak Players, Gain, % Gain
            avg_col_idx = None
            peak_col_idx = None
            
            if len(header_cells) >= 3:
                for i, header in enumerate(header_cells):
                    header_text = header.text.strip().lower()
                    if 'avg' in header_text and 'player' in header_text:
                        avg_col_idx = i
                    elif 'peak' in header_text and 'player' in header_text:
                        peak_col_idx = i
                
                # If we couldn't find the specific columns, try common positions
                if avg_col_idx is None and len(header_cells) >= 2:
                    avg_col_idx = 1  # Usually second column
                if peak_col_idx is None and len(header_cells) >= 3:
                    peak_col_idx = 2  # Usually third column
            
            print(f"    🎯 Using columns: Avg={avg_col_idx}, Peak={peak_col_idx}")
            
            # Skip header row and process data rows
            for i, row in enumerate(rows[1:], 1):
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 3:
                        month = cols[0].text.strip()
                        
                        # Get player counts from the identified columns
                        avg_players = cols[avg_col_idx].text.strip() if avg_col_idx is not None else "0"
                        peak_players = cols[peak_col_idx].text.strip() if peak_col_idx is not None else "0"
                        
                        # Debug: Print raw values for first few rows
                        if i <= 3:
                            print(f"      Row {i}: Month='{month}', Avg='{avg_players}', Peak='{peak_players}'")
                        
                        # Parse the numbers
                        avg_players_num = parse_number_with_commas(avg_players)
                        peak_players_num = parse_number_with_commas(peak_players)
                        
                        # Only add if we have valid numbers
                        if avg_players_num > 0 or peak_players_num > 0:
                            data.append([month, game_name, avg_players_num, peak_players_num])
                        elif i <= 5:  # Debug info for first few rows
                            print(f"      ⚠️  Skipping row {i} - no valid player counts")
                            
                except Exception as e:
                    print(f"    Error processing row {i} for {game_name}: {e}")
                    continue
            
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


def scrape_steam_games() -> pd.DataFrame:
    """Main function to scrape all Steam games and return DataFrame."""
    print("🚀 Starting Steam Charts scraper with Selenium...")
    
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
        total_games = len(steam_games)
        successful_games = 0
        
        for i, (game, app_id) in enumerate(steam_games.items(), 1):
            print(f"\n[{i}/{total_games}] Scraping {game}...")
            
            game_data = scrape_steamcharts(driver, app_id, game)
            if game_data:
                all_data.extend(game_data)
                successful_games += 1
            
            # Add random delay between requests (except for the last game)
            if i < total_games:
                random_delay()
        
        # Convert to DataFrame and save
        if all_data:
            df = pd.DataFrame(all_data, columns=["Month", "Game", "Avg Players", "Peak Players"])
            output_file = os.path.join("data", "steam_monthly_player_counts.csv")
            df.to_csv(output_file, index=False)
            print(f"\n✅ Successfully scraped {len(all_data)} records from {successful_games}/{total_games} games")
            print(f"📁 Data saved to {output_file}")
            
            # Show some sample data
            print("\n📊 Sample of scraped data:")
            print(df.head(10))
            
            # Show summary by game
            print("\n📈 Summary by game:")
            game_summary = df.groupby('Game')['Avg Players'].max().sort_values(ascending=False)
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
    scrape_steam_games() 