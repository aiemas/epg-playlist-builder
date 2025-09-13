from seleniumwire import webdriver
import time
from concurrent.futures import ThreadPoolExecutor

# 🔹 Player da usare
PLAYER_PATHS = ["watch", "player"]

# 🔹 Canali da 1 a 1000
CHANNEL_IDS = range(1, 1001)

# 🔹 Funzione per estrarre link m3u8 da un embed
def extract_m3u8(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(5)  # Attendi caricamento richieste
        m3u8_urls = set()
        for req in driver.requests:
            if req.response and ".m3u8" in req.url:
                m3u8_urls.add(req.url)
        return list(m3u8_urls)
    finally:
        driver.quit()

# 🔹 Funzione per fare scraping di un singolo player e canale
def scrape_player(channel_id, path):
    url = f"https://daddylivestream.com/{path}/stream-{channel_id}.php"
    print(f"🚀 Scraping {url}")
    links = extract_m3u8(url)
    if links:
        print(f"✅ Trovati {len(links)} link in {path} per canale {channel_id}")
    else:
        print(f"❌ Nessun link trovato in {path} per canale {channel_id}")
    return links

if __name__ == "__main__":
    all_links = []

    # Esegui scraping con ThreadPool per velocizzare
    with ThreadPoolExecutor(max_workers=4) as executor:
        for channel_id in CHANNEL_IDS:
            results = executor.map(lambda path: scrape_player(channel_id, path), PLAYER_PATHS)
            for r in results:
                all_links.extend(r)

    # 🔹 Scrivi file m3u nella root della repo
    with open("cazzimiei.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for link in all_links:
            f.write(f"{link}\n")

    print(f"\n🎯 Totale link trovati: {len(all_links)}")
    print("✅ File creato: cazzimiei.m3u")
