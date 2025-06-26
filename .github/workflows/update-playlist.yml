import requests
from datetime import datetime

sources = [
    "nfsnew.newkso.ru",
    "windnew.newkso.ru",
    "zekonew.newkso.ru",
    "dokko1new.newkso.ru",
    "ddy6new.newkso.ru"
]

max_channels = 999
output_file = "direct_playlist.m3u8"
log_file = "scan_errors.log"

headers = {
    "User-Agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) TV"
}

valid_count = 0
print(f"🔍 Inizio scansione: {datetime.now()}")

with open(output_file, "w", encoding="utf-8") as f_out, open(log_file, "w", encoding="utf-8") as f_log:
    f_out.write("#EXTM3U\n")

    for source in sources:
        for i in range(1, max_channels + 1):
            url = f"https://{source}/nfs/premium{i}/mono.m3u8"

            try:
                res = requests.get(url, headers=headers, timeout=12)

                if res.status_code == 200 and "#EXTM3U" in res.text:
                    print(f"✅ Valido: {url}")
                    f_out.write(f"#EXTINF:-1,{source} Channel {i}\n{url}\n")
                    valid_count += 1
                else:
                    print(f"❌ Non valido: {url}")
                    f_log.write(f"❌ Non valido: {url}\n")

            except Exception as e:
                print(f"⚠️ Errore: {url} -> {e}")
                f_log.write(f"⚠️ Errore: {url} -> {e}\n")

print(f"\n✅ Fine scansione: {datetime.now()} — Canali validi: {valid_count}")
