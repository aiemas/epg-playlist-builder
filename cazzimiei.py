#!/usr/bin/env python3
from seleniumwire import webdriver
import time

# Range dei canali
CHANNELS = range(1, 100)
PLAYER_PATHS = ["watch", "player"]

OUTPUT_FILE = "cazzimiei.m3u"

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
    except Exception as e:
        print(f"⚠️ Errore su {url}: {e}")
        return []
    finally:
        driver.quit()

def scrape_channel(channel_id):
    all_links = []
    for path in PLAYER_PATHS:
        url = f"https://daddylivestream.com/{path}/stream-{channel_id}.php"
        print(f"🚀 Scraping {url}")
        links = extract_m3u8(url)
        if links:
            print(f"✅ Canale {channel_id} ({path}): trovati {len(links)} link")
            all_links.extend(links)
        else:
            print(f"❌ Canale {channel_id} ({path}): nessun link")
    return all_links

if __name__ == "__main__":
    all_results = []

    for ch in CHANNELS:
        links = scrape_channel(ch)
        for link in links:
            all_results.append(f"#EXTINF:-1,Channel {ch}\n{link}")

    # Scrivi sempre il file, anche se vuoto
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("\n".join(all_results))

    print(f"\n🎯 File {OUTPUT_FILE} creato con {len(all_results)} link totali")
