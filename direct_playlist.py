#!/usr/bin/env python3

import requests

OUTPUT_FILE = "direct_playlist.m3u8"

URL_TEMPLATES = [
    "https://nfsnew.newkso.ru/nfs/premium{num}/mono.m3u8",
    "https://windnew.newkso.ru/wind/premium{num}/mono.m3u8",
    "https://zekonew.newkso.ru/zeko/premium{num}/mono.m3u8",
    "https://dokko1new.newkso.ru/dokko1/premium{num}/mono.m3u8",
    "https://ddy6new.newkso.ru/ddy6/premium{num}/mono.m3u8",
]

USER_AGENT = "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) TV SamsungBrowser/2.1 Safari/537.36"
REFERER = "https://xtreaweb.top/"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": REFERER
}

def validate_url(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False

def generate_playlist():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for template in URL_TEMPLATES:
            for i in range(1, 1000):
                url = template.format(num=i)
                if validate_url(url):
                    name = url.split("/")[2].split(".")[0].upper() + " Channel " + str(i)
                    f.write(f"#EXTINF:-1,{name}\n")
                    f.write(f"#EXTVLCOPT:http-user-agent={USER_AGENT}\n")
                    f.write(f"#EXTVLCOPT:http-referrer={REFERER}\n")
                    f.write(f"{url}\n")
                    print(f"✅ Aggiunto: {name}")
                else:
                    print(f"⛔ Non valido: {url}")

    print(f"\n✅ Playlist salvata in: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_playlist()
