# 🎮 Game Player Count Scraper

A comprehensive web scraping system for collecting video game player count data from multiple sources including Steam Charts and ActivePlayer.io.

## 📊 Features

- **Multi-Source Data Collection**: Scrapes from Steam Charts (historical monthly data) and ActivePlayer.io (current player counts)
- **60+ Games Supported**: Covers popular games across different genres and platforms
- **Anti-Detection Measures**: Advanced techniques to avoid being blocked by websites
- **Retry Logic**: Handles timeouts and failures gracefully
- **Flexible Data Parsing**: Supports various number formats (1K, 1M, commas, etc.)
- **Comprehensive Logging**: Detailed progress tracking and debugging information
- **Modular Design**: Separate scrapers for different data sources

## 🗂️ File Structure

```
├── scraper.py                 # Interactive launcher with menu
├── steamdb_scraper.py         # Steam Charts scraper (historical data)
├── activeplayer_scraper.py    # ActivePlayer.io scraper (current data)
├── main_scraper.py           # Combined scraper orchestrator
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🎯 Supported Games

### Steam Games (60+ games)
- **Battle Royale**: PUBG, Apex Legends, Rust, ARK, DayZ
- **FPS**: Counter-Strike 2, Team Fortress 2, Rainbow Six Siege, Payday 2
- **RPG**: Elden Ring, Cyberpunk 2077, Baldur's Gate 3, The Witcher 3
- **MMO**: Lost Ark, Monster Hunter: World, Destiny 2, Warframe
- **Indie**: Among Us, Hades, Stardew Valley, Terraria
- **Strategy**: Civilization VI, Garry's Mod
- **Survival**: The Forest, Subnautica, No Man's Sky, Valheim

### ActivePlayer Games (60+ games)
- **Battle Royale**: Fortnite, PUBG, Apex Legends, Call of Duty Warzone
- **MOBA**: League of Legends, Dota 2, Heroes of the Storm
- **FPS**: Valorant, Overwatch 2, Counter-Strike 2
- **MMO**: World of Warcraft, Final Fantasy XIV, Black Desert Online
- **Plus all Steam games above**

## 🚀 Installation

1. **Clone or download the project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage

### Interactive Menu (Recommended)
```bash
python scraper.py
```
Then choose from the interactive menu:
- Steam Charts scraper
- ActivePlayer scraper  
- Combined scraper (both sources)

### Direct Scraper Execution

#### Steam Charts Only (Historical Monthly Data)
```bash
python steamdb_scraper.py
```

#### ActivePlayer Only (Current Player Counts)
```bash
python activeplayer_scraper.py
```

#### Combined Scraper (Both Sources)
```bash
python main_scraper.py
```

### Command-Line Arguments
```bash
# Run specific scraper
python main_scraper.py steam
python main_scraper.py activeplayer
python main_scraper.py combined
```

## 📁 Output Files

The scrapers generate the following CSV files:

- **`steam_monthly_player_counts.csv`** - Historical monthly average and peak player counts from Steam
- **`activeplayer_current_counts.csv`** - Current player counts from ActivePlayer.io
- **`combined_player_counts.csv`** - Combined dataset from both sources with source tracking

### Data Format

#### Steam Data
| Month | Game | Avg Players | Peak Players | Source | Scraped At |
|-------|------|-------------|--------------|--------|------------|
| June 2025 | Rust | 100,433.5 | 187,345 | Steam Charts | 2025-01-15 14:30:00 |

#### ActivePlayer Data
| Date | Game | Current Players | Peak Players | Source | Scraped At |
|------|------|----------------|--------------|--------|------------|
| 2025-01-15 | Fortnite | 2,500,000 | 3,200,000 | ActivePlayer | 2025-01-15 14:30:00 |

## ⚙️ Configuration

### Timing Settings
You can adjust timing parameters in each scraper file:

```python
REQUEST_DELAY_MIN = 5    # Minimum seconds between requests
REQUEST_DELAY_MAX = 10   # Maximum seconds between requests
PAGE_LOAD_TIMEOUT = 20   # Page load timeout in seconds
MAX_RETRIES = 3          # Maximum retry attempts
```

### Adding New Games
To add new games, edit the game dictionaries in the respective scraper files:

- **Steam games**: Add to `steam_games` in `steamdb_scraper.py`
- **ActivePlayer games**: Add to `activeplayer_games` in `activeplayer_scraper.py`

## 🔧 Technical Details

### Anti-Detection Features
- Realistic user agent strings
- Random delays between requests
- WebDriver property masking
- Browser fingerprint randomization
- Retry logic with exponential backoff

### Data Parsing
- Handles comma-separated numbers (1,234,567)
- Supports K/M/B suffixes (1K, 1M, 1B)
- Ignores percentage changes
- Validates numeric data before saving

### Error Handling
- Graceful timeout handling
- Automatic retries for failed requests
- Detailed error logging
- Continues processing other games if one fails

## 📈 Example Output

```
🚀 Starting Steam Charts scraper with Selenium...
📱 Setting up Chrome driver...
⏳ Waiting 10 seconds before starting...

[1/60] Scraping Dota 2...
  Loading Dota 2 page... (attempt 1/3)
    Found table with selector: table.common-table
    📋 Found 158 rows in table
    📊 Table headers: ['Month', 'Avg. Players', 'Gain', '% Gain', 'Peak Players']
    🎯 Using columns: Avg=1, Peak=4
      Row 1: Month='Last 30 Days', Avg='456,789.0', Peak='789,123'
  ✅ Successfully scraped 157 records for Dota 2

✅ Successfully scraped 3,240 records from 58/60 games
📁 Data saved to steam_monthly_player_counts.csv

📈 Summary by game:
  1. Dota 2: 456,789
  2. Counter-Strike 2: 234,567
  3. PUBG: 123,456
  ...
```

## ⚠️ Important Notes

- **Rate Limiting**: The scrapers include delays to respect website rate limits
- **Browser Required**: Uses Selenium with Chrome WebDriver
- **Internet Connection**: Requires stable internet connection
- **Legal Compliance**: Only scrapes publicly available data
- **Data Accuracy**: Data accuracy depends on the source websites

## 🐛 Troubleshooting

### Common Issues

1. **ChromeDriver not found**: Install with `pip install webdriver-manager`
2. **Timeout errors**: Increase `PAGE_LOAD_TIMEOUT` in scraper files
3. **No data found**: Check if game slugs/IDs are correct
4. **Rate limiting**: Increase delay times between requests

### Debug Mode
Enable debug output by uncommenting headless mode in scraper files:
```python
# chrome_options.add_argument("--headless")
```

## 📄 License

This project is for educational and research purposes. Please respect the terms of service of the websites being scraped.

## 🤝 Contributing

Feel free to:
- Add more games to the supported lists
- Improve error handling and reliability
- Add support for additional data sources
- Optimize performance and timing

---

**Happy Scraping! 🎮📊** 