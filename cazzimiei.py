from seleniumwire import webdriver
import time
from concurrent.futures import ThreadPoolExecutor

CHANNEL_ID = 31
PLAYER_PATHS = ["stream", "cast", "watch", "player"]

def extract_m3u8(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(5)
        m3u8_urls = set()
        for req in driver.requests:
            if req.response and ".m3u8" in req.url:
                m3u8_urls.add(req.url)
        return list(m3u8_urls)
    finally:
        driver.quit()

def scrape_player(path):
    url = f"https://daddylivestream.com/{path}/stream-{CHANNEL_ID}.php"
    print(f"🚀 Scraping {url}")
    links = extract_m3u8(url)
    if links:
        print(f"✅ Trovati {len(links)} link in {path}:")
        for l in links:
            print(f"   {l}")
    else:
        print(f"❌ Nessun link trovato in {path}")
    return links

if __name__ == "__main__":
    all_links = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(scrape_player, PLAYER_PATHS)

    # Raccogli tutti i link
    for r in results:
        all_links.extend(r)

    print(f"\n🎯 Totale link trovati: {len(all_links)}")
