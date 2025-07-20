import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import os
from config import get_activeplayer_games, OUTPUT_DIR, ACTIVEPLAYER_OUTPUT_FILE
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def parse_number_with_commas(text: str) -> float:
    if not text or text.strip() == '':
        return 0.0
    cleaned = text.replace(',', '').replace('%', '').strip().lower()
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

def create_robust_session():
    """Create a requests session with retry strategy and proper headers"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set headers to mimic a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    return session

def make_request_with_retry(session, url: str, max_retries: int = 3, base_delay: float = 2.0):
    """Make HTTP request with retry logic and exponential backoff"""
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=25)  # Increased timeout
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff + jitter
                print(f"    ⏳ Timeout on attempt {attempt + 1}/{max_retries}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"    ⏳ Request failed on attempt {attempt + 1}/{max_retries}: {e}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise
    return None

def scrape_activeplayer(game_slug: str, game_name: str):
    url = f"https://activeplayer.io/{game_slug}/"
    print(f"Scraping: {url}")
    data = []
    
    # Create a robust session for this game
    session = create_robust_session()
    
    # Track pages we've already scraped to avoid duplicates
    scraped_pages = set()
    page_num = 1
    
    while True:
        # Construct URL for current page
        if page_num == 1:
            current_url = url
        else:
            current_url = f"{url}?ms_page={page_num}"
        
        print(f"    📄 Scraping page {page_num}...")
        
        try:
            response = make_request_with_retry(session, current_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try different table structures in order of preference
            table = None
            
            # 1. Try table_2 first (most common)
            table = soup.find("table", id="table_2")
            if table:
                print(f"    📊 Found table_2 for {game_name}")
            
            # 2. Try table_3 as another option
            if not table:
                table = soup.find("table", id="table_3")
                if table:
                    print(f"    📊 Found table_3 for {game_name}")
            
            # 3. Try steam-stats-table as fallback
            if not table:
                table = soup.find("table", class_="steam-stats-table")
                if table:
                    print(f"    📊 Found steam-stats-table for {game_name}")
            
            # 4. Try asdrm-monthly-stats-table for mobile games
            if not table:
                table = soup.find("table", class_="asdrm-monthly-stats-table")
                if table:
                    print(f"    📊 Found asdrm-monthly-stats-table for {game_name}")
            
            # 5. Try gst-data-table for some games
            if not table:
                table = soup.find("table", class_="gst-data-table")
                if table:
                    print(f"    📊 Found gst-data-table for {game_name}")
            
            # 6. Try wgs-stats-table as another fallback
            if not table:
                table = soup.find("table", class_="wgs-stats-table")
                if table:
                    print(f"    📊 Found wgs-stats-table for {game_name}")
            
            # 7. Try table table-striped for games like Don't Starve Together
            if not table:
                table = soup.find("table", class_="table table-striped")
                if table:
                    print(f"    📊 Found table table-striped for {game_name}")
            
            if not table:
                if page_num == 1:
                    print(f"  ⚠️  No suitable table found for {game_name}")
                else:
                    print(f"    ✅ No more pages found for {game_name}")
                break
            
            # Find header and map columns
            header = table.find("thead")
            if not header:
                print(f"  ⚠️  No header found in table for {game_name}")
                break
            
            header_cells = [th.get_text(strip=True).lower() for th in header.find_all("th")]
            if page_num == 1:
                print(f"    📋 Table columns: {header_cells}")
            
            # Find indices for average/daily and peak
            avg_idx = None
            peak_idx = None
            
            # Handle different column naming patterns
            for i, header_text in enumerate(header_cells):
                # For peak columns - check this FIRST to avoid conflicts
                if any(keyword in header_text for keyword in ["peak", "max player", "max concurrent"]):
                    peak_idx = i
                # For average/daily columns - check this second
                elif any(keyword in header_text for keyword in ["average daily", "daily avg", "daily average", "daily average users"]):
                    avg_idx = i
                # For estimated players (mobile games)
                elif "estimated players" in header_text:
                    avg_idx = i
                # For monthly average users
                elif "monthly average users" in header_text:
                    avg_idx = i
                # For wgs-stats-table format: "players" column (only if no peak found)
                elif "players" in header_text and peak_idx is None:
                    avg_idx = i
                # For table_3 format: "average daily players" column
                elif "average daily players" in header_text:
                    avg_idx = i
                # For table-striped format: "daily average" column
                elif "daily average" in header_text:
                    avg_idx = i
            
            # Special handling for asdrm-monthly-stats-table format (has "Estimated Players" but no peak)
            if "asdrm-monthly-stats-table" in table.get("class", []):
                if avg_idx is not None:
                    # For asdrm table, we'll use the "Estimated Players" for both avg and peak
                    # since there's no separate peak column
                    peak_idx = avg_idx
                    if page_num == 1:
                        print(f"    📊 Using 'Estimated Players' column for both avg and peak (index {avg_idx})")
            
            # Special handling for table_3 format (has "Average Daily Players" but no peak)
            elif table.get("id") == "table_3":
                if avg_idx is not None:
                    # For table_3, we'll use the "Average Daily Players" for both avg and peak
                    # since there's no separate peak column
                    peak_idx = avg_idx
                    if page_num == 1:
                        print(f"    📊 Using 'Average Daily Players' column for both avg and peak (index {avg_idx})")
            
            # Special handling for wgs-stats-table format (only has "Players" column)
            elif "wgs-stats-table" in table.get("class", []):
                if avg_idx is not None:
                    # Use the same column for both average and peak since there's no separate peak
                    peak_idx = avg_idx
                    if page_num == 1:
                        print(f"    📊 Using single 'Players' column for both avg and peak (index {avg_idx})")
            
            # Special handling for gst-data-table format (has "Daily Average Users" but no peak)
            elif "gst-data-table" in table.get("class", []):
                if avg_idx is not None:
                    # For gst table, we'll use the "Daily Average Users" for both avg and peak
                    # since there's no separate peak column
                    peak_idx = avg_idx
                    if page_num == 1:
                        print(f"    📊 Using 'Daily Average Users' column for both avg and peak (index {avg_idx})")
            
            # Special handling for table table-striped format (has "Daily Average" and "Peak Players")
            elif "table-striped" in table.get("class", []):
                if avg_idx is not None and peak_idx is not None:
                    if page_num == 1:
                        print(f"    📊 Using 'Daily Average' (index {avg_idx}) and 'Peak Players' (index {peak_idx}) columns")
                else:
                    print(f"  ⚠️  Could not find required columns for table-striped format")
                    print(f"    Expected: Daily Average and Peak Players columns")
                    print(f"    Found: {header_cells}")
                    break
            
            if avg_idx is None:
                print(f"  ⚠️  Could not find required columns for {game_name}")
                print(f"    Expected: average/daily/players column")
                print(f"    Found: {header_cells}")
                break
            
            if peak_idx is None:
                print(f"  ⚠️  Could not find peak column for {game_name}")
                print(f"    Expected: peak/max player/max concurrent column")
                print(f"    Found: {header_cells}")
                print(f"    Looking for keywords: peak, max player, max concurrent")
                break
            
            if page_num == 1:
                print(f"    📊 Using columns: Avg Daily (index {avg_idx}), Peak (index {peak_idx})")
            
            # Collect ALL data rows from this page
            rows = table.find_all("tr")
            page_data_count = 0
            
            for row in rows:
                cols = row.find_all("td")
                if len(cols) > max(avg_idx, peak_idx):
                    month = cols[0].get_text(strip=True)
                    avg_daily = parse_number_with_commas(cols[avg_idx].get_text(strip=True))
                    peak = parse_number_with_commas(cols[peak_idx].get_text(strip=True))
                    
                    # Skip rows with invalid data (0 or empty values)
                    if avg_daily > 0 and peak > 0:
                        data.append([month, game_name, avg_daily, peak])
                        page_data_count += 1
            
            print(f"    ✅ Page {page_num}: Collected {page_data_count} data points")
            
            # Check if there are more pages by looking for pagination links
            pagination = soup.find("div", class_="ms-pagination")
            if pagination:
                next_links = pagination.find_all("a", href=True)
                has_next = False
                for link in next_links:
                    if "Next" in link.get_text() or f"ms_page={page_num + 1}" in link.get("href", ""):
                        has_next = True
                        break
                
                if not has_next:
                    print(f"    ✅ No more pages found for {game_name}")
                    break
            else:
                # No pagination found, assume only one page
                break
            
            page_num += 1
            
            # Small delay between pages to be respectful
            if page_num > 1:
                time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            print(f"  ❌ Error scraping {game_name} page {page_num}: {e}")
            break
    
    # Close the session
    session.close()
    
    if data:
        print(f"    ✅ {game_name}: Collected {len(data)} total monthly data points")
    else:
        print(f"    ⚠️  No valid data rows found for {game_name}")
    
    return data

def scrape_activeplayer_games():
    activeplayer_games = get_activeplayer_games()
    all_data = []
    for i, (game, slug) in enumerate(activeplayer_games.items(), 1):
        print(f"[{i}/{len(activeplayer_games)}] Scraping {game}...")
        game_data = scrape_activeplayer(slug, game)
        if game_data:
            all_data.extend(game_data)
        if i < len(activeplayer_games):
            # Removed random_delay()
            pass
    if all_data:
        df = pd.DataFrame(all_data, columns=["Month", "Game", "Avg Players", "Peak Players"])
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, ACTIVEPLAYER_OUTPUT_FILE)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Data saved to {output_file}")
        print(f"📊 Total records: {len(df)}")
        print(f"🎮 Games scraped: {df['Game'].nunique()}")
    else:
        print("\n❌ No data was scraped successfully")

if __name__ == "__main__":
    scrape_activeplayer_games() 