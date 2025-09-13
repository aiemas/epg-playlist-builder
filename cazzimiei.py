from seleniumwire import webdriver
import time
from concurrent.futures import ThreadPoolExecutor

PLAYER_PATHS = ["watch", "player"]
CHANNEL_RANGE = range(1, 101)  # da 1 a 1000

# Scrive l'intestazione iniziale del file M3U
with open("cazzimiei.m3u", "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

def extract_m3u8(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")

    seleniumwire_options = {
        'connection_timeout': None,
        'verify_ssl': False,
        'mitm_http2': False,
        'exclude_hosts': ['fonts.googleapis.com', 'google.com', 'gstatic.com']
    }

    driver = webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
    try:
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(5)

        m3u8_urls = set()
        for req in driver.requests:
            if req.response and ".m3u8" in req.url:
                m3u8_urls.add(req.url)

        return list(m3u8_urls)
    except Exception as e:
        print(f"⚠️ Errore su {url}: {e}")
        return []
    finally:
        driver.quit()

def scrape_player(channel_id, path):
    url = f"https://daddylivestream.com/{path}/stream-{channel_id}.php"
    print(f"🚀 Scraping {url}")
    links = extract_m3u8(url)

    if links:
        print(f"✅ {len(links)} link trovati in {path} per canale {channel_id}")
        with open("cazzimiei.m3u", "a", encoding="utf-8") as f:
            for l in links:
                f.write(f'#EXTINF:-1 group-title="Channel {channel_id}",Channel {channel_id}\n')
                f.write(l + "\n")
    else:
        print(f"❌ Nessun link trovato in {path} per canale {channel_id}")

if __name__ == "__main__":
    for channel_id in CHANNEL_RANGE:
        print(f"\n🔎 Canale {channel_id}")
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(lambda path: scrape_player(channel_id, path), PLAYER_PATHS)

    print("\n🎯 Scraping completato, file salvato: cazzimiei.m3u")
