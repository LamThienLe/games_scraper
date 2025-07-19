import pandas as pd
import time
import os
from datetime import datetime
from steamdb_scraper import scrape_steam_games
from activeplayer_scraper import scrape_activeplayer_games

def combine_data():
    """Combine data from both Steam and ActivePlayer scrapers."""
    print("🎮 Starting comprehensive game player count scraper...")
    print("=" * 60)
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📅 Started at: {timestamp}")
    
    all_data = []
    
    # Scrape Steam games
    print("\n🔥 Starting Steam Charts scraper...")
    try:
        steam_df = scrape_steam_games()
        if not steam_df.empty:
            # Add source column
            steam_df['Source'] = 'Steam Charts'
            steam_df['Scraped At'] = timestamp
            all_data.append(steam_df)
            print(f"✅ Steam data: {len(steam_df)} records")
        else:
            print("❌ No Steam data collected")
    except Exception as e:
        print(f"❌ Steam scraper failed: {e}")
    
    # Wait between scrapers
    print("\n⏳ Waiting 30 seconds before starting ActivePlayer scraper...")
    time.sleep(30)
    
    # Scrape ActivePlayer games
    print("\n🌐 Starting ActivePlayer scraper...")
    try:
        activeplayer_df = scrape_activeplayer_games()
        if not activeplayer_df.empty:
            # Add source column
            activeplayer_df['Source'] = 'ActivePlayer'
            activeplayer_df['Scraped At'] = timestamp
            all_data.append(activeplayer_df)
            print(f"✅ ActivePlayer data: {len(activeplayer_df)} records")
        else:
            print("❌ No ActivePlayer data collected")
    except Exception as e:
        print(f"❌ ActivePlayer scraper failed: {e}")
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Save combined data to data/ directory
        output_file = os.path.join("data", "combined_player_counts.csv")
        combined_df.to_csv(output_file, index=False)
        print(f"\n✅ Combined data saved: {len(combined_df)} total records")
        print(f"📁 File: {output_file}")
        
        # Show summary
        print("\n📊 Data Summary:")
        print(f"Total records: {len(combined_df)}")
        print(f"Unique games: {combined_df['Game'].nunique()}")
        print(f"Sources: {combined_df['Source'].unique()}")
        
        # Show top games by average players (Steam data)
        if 'Avg Players' in combined_df.columns:
            steam_only = combined_df[combined_df['Source'] == 'Steam Charts']
            if not steam_only.empty:
                print("\n🏆 Top Steam Games (by Average Players):")
                top_steam = steam_only.groupby('Game')['Avg Players'].max().sort_values(ascending=False).head(10)
                for i, (game, players) in enumerate(top_steam.items(), 1):
                    print(f"  {i:2d}. {game}: {players:,.0f}")
        
        # Show top games by current players (ActivePlayer data)
        if 'Current Players' in combined_df.columns:
            activeplayer_only = combined_df[combined_df['Source'] == 'ActivePlayer']
            if not activeplayer_only.empty:
                print("\n🏆 Top ActivePlayer Games (by Current Players):")
                top_activeplayer = activeplayer_only.groupby('Game')['Current Players'].max().sort_values(ascending=False).head(10)
                for i, (game, players) in enumerate(top_activeplayer.items(), 1):
                    print(f"  {i:2d}. {game}: {players:,.0f}")
        
        return combined_df
    else:
        print("\n❌ No data was collected from any source")
        return pd.DataFrame()


def run_steam_only():
    """Run only the Steam scraper."""
    print("🔥 Running Steam Charts scraper only...")
    return scrape_steam_games()


def run_activeplayer_only():
    """Run only the ActivePlayer scraper."""
    print("🌐 Running ActivePlayer scraper only...")
    return scrape_activeplayer_games()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "steam":
            run_steam_only()
        elif mode == "activeplayer":
            run_activeplayer_only()
        elif mode == "combined":
            combine_data()
        else:
            print("Usage: python main_scraper.py [steam|activeplayer|combined]")
            print("  steam: Run only Steam Charts scraper")
            print("  activeplayer: Run only ActivePlayer scraper")
            print("  combined: Run both scrapers and combine data (default)")
    else:
        # Default: run combined scraper
        combine_data() 