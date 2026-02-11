import logging
import sys
from app.scrapers.sunedu import SuneduScraper

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_integration():
    scraper = SuneduScraper()
    dni = "12345678" # Dummy DNI
    print(f"Testing SuneduScraper with DNI {dni}...")
    try:
        result = scraper.procesar_dni(None, dni)
        print("Result:", result)
    except Exception as e:
        print("Scraper raised exception:", e)

if __name__ == "__main__":
    test_integration()
