#!/usr/bin/env python3
"""
events.py — live-events playlist builder con header
• Scansiona sorgenti newkso per flussi validi (canali 1-999)
• Aggiunge User-Agent e Referer
• Genera playlist M3U8 con #EXTVLCOPT
"""

import requests
from datetime import datetime
import time

sources = [
    "nfsnew.newkso.ru",
    "windnew.newkso.ru",
    "zekonew.newkso.ru",
    "dokko1new.newkso.ru",
    "ddy6new.newkso.ru"
]

channel_range = range(1, 1000)  # 🔁 Canali da 1 a 999
timeout = 4

user_agent = "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) TV SamsungBrowser/2.1 Safari/537.36"

referers = {
    "nfsnew.newkso.ru": "https://xtreaweb.top",
    "windnew.newkso.ru": "https://xtreaweb.top",
    "zekonew.newkso.ru": "https://thedaddy.click",
    "dokko1new.newkso.ru": "https://xtreamplanet.top",
    "ddy6new.newkso.ru": "https://xtreamplanet.top",
}

def generate_url(source, number):
    return f"https://{source}/nfs/premium{number}/mono.m3u8"

def check_url(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200 and "#EXTM3U" in r.text:
            return True
    except requests.RequestException:
        return False
    return False

def build_playlist():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    playlist = [f"#EXTM3U\n# Generated on {now}\n"]
    for source in sources:
        ref = referers.get(source, "")
        for i in channel_range:
            url = generate_url(source, i)
            headers = {
                "User-Agent": user_agent,
                "Referer": ref
            }
            print(f"🔍 Scanning {url}")
            if check_url(url, headers):
                name = f"{source.split('.')[0].upper()} Channel {i}"
                playlist.append(f'#EXTINF:-1,{name}\n')
                playlist.append(f'#EXTVLCOPT:http-referrer={ref}\n')
                playlist.append(f'#EXTVLCOPT:http-user-agent={user_agent}\n')
                playlist.append(f'{url}\n')
            else:
                print(f"❌ Not valid: {url}")
    return playlist

def save_playlist(playlist, filename="events.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print(f"\n✅ Playlist salvata in: {filename}")

if __name__ == "__main__":
    print(f"Inizio scansione: {datetime.now()}")
    start = time.time()
    playlist = build_playlist()
    save_playlist(playlist)
    print(f"⏱️ Tempo impiegato: {round(time.time() - start, 2)} secondi")
