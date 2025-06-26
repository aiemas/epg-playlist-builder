import requests
from datetime import datetime

# Lista delle sorgenti da testare
sources = [
    "nfsnew.newkso.ru",
    "windnew.newkso.ru",
    "zekonew.newkso.ru",
    "dokko1new.newkso.ru",
    "ddy6new.newkso.ru"
]

# Numero massimo di canali per sorgente
max_channels = 999

# File di output
output_file = "direct_playlist.m3u8"

# Header per simulare uno Smart TV
headers = {
    "User-Agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) TV"
}

print(f"🔍 Inizio scansione: {datetime.now()}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

    for source in sources:
        for i in range(1, max_channels + 1):
            url = f"https://{source}/nfs/premium{i}/mono.m3u8"

            try:
                res = requests.get(url, headers=headers, timeout=5)

                # Controlla che il contenuto contenga una intestazione .m3u8
                if res.status_code == 200 and "#EXTM3U" in res.text:
                    print(f"✅ Valido: {url}")
                    f.write(f"#EXTINF:-1,{source} Channel {i}\n{url}\n")
                else:
                    print(f"❌ Non valido: {url}")

            except Exception as e:
                print(f"⚠️ Errore: {url} -> {e}")

print(f"✅ Fine scansione: {datetime.now()}")
