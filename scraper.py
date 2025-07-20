#!/usr/bin/env python3
"""
Game Player Count Scraper - Main Launcher

This script has been refactored into a modular system with separate scrapers for different platforms.

Available scrapers:
- steamdb_scraper.py: Scrapes Steam Charts for historical monthly data
- activeplayer_scraper.py: Scrapes ActivePlayer.io for current player counts
- main_scraper.py: Combines data from both sources

Usage:
    python scraper.py                    # Shows this help message
    python steamdb_scraper.py            # Run Steam scraper only
    python activeplayer_scraper.py       # Run ActivePlayer scraper only
    python main_scraper.py               # Run both and combine data
    python main_scraper.py steam         # Run Steam scraper only
    python main_scraper.py activeplayer  # Run ActivePlayer scraper only
    python main_scraper.py combined      # Run both scrapers and combine data
"""

import sys
import subprocess

def main():
    print("🎮 Game Player Count Scraper")
    print("=" * 40)
    print()
    print("This script has been refactored into a modular system!")
    print()
    print("Available options:")
    print("  🔥 Steam Charts (historical monthly data):")
    print("    python steamdb_scraper.py")
    print()
    print("  🌐 ActivePlayer (current player counts):")
    print("    python activeplayer_scraper.py")
    print()
    print("  🎯 Combined (both sources):")
    print("    python main_scraper.py")
    print()
    print("  📊 Individual modes:")
    print("    python main_scraper.py steam")
    print("    python main_scraper.py activeplayer")
    print("    python main_scraper.py combined")
    print()
    
    # Ask user what they want to run
    print("What would you like to run?")
    print("1. Steam Charts scraper")
    print("2. ActivePlayer scraper")
    print("3. Combined scraper (both)")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n🚀 Starting Steam Charts scraper...")
            subprocess.run([sys.executable, "steamdb_scraper.py"])
        elif choice == "2":
            print("\n🚀 Starting ActivePlayer scraper...")
            subprocess.run([sys.executable, "activeplayer_scraper.py"])
        elif choice == "3":
            print("\n🚀 Starting combined scraper...")
            subprocess.run([sys.executable, "main_scraper.py"])
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice. Please run one of the specific scrapers directly.")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
