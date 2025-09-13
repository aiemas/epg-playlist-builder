import datetime
import json

# File locale con il calendario
LOCAL_FILE = "schedule-generated.php"

# 🔹 Campionati da includere
IMPORTANT_PREFIXES = [
    "England - Premier League : ",
    "Spain - La Liga : ",
    "Bundesliga : ",
    "Italy - Serie A : ",
    "France - Ligue 1 : "
]

PLAYER_PATHS = ["stream", "cast", "watch", "player"]

def day_suffix(day):
    if 11 <= day <= 13:
        return "th"
    last_digit = day % 10
    if last_digit == 1:
        return "st"
    elif last_digit == 2:
        return "nd"
    elif last_digit == 3:
        return "rd"
    else:
        return "th"

def get_today_date_string():
    now = datetime.datetime.utcnow()
    day = now.day
    suffix = day_suffix(day)
    day_str = f"{day}{suffix}"
    date_str = now.strftime(f"%A {day_str} %B %Y - Schedule Time UK GMT")
    return date_str

def add_two_hours(time_str):
    try:
        dt = datetime.datetime.strptime(time_str, "%H:%M")
        dt_plus2 = dt + datetime.timedelta(hours=2)
        return dt_plus2.strftime("%H:%M")
    except Exception:
        return time_str

def is_important(event_name):
    for prefix in IMPORTANT_PREFIXES:
        if event_name.startswith(prefix):
            # Esclude Bundesliga 2
            if prefix.startswith("Bundesliga") and "2" in event_name:
                return False
            return True
    return False

def get_soccer_events_for_date(target_date):
    with open(LOCAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if target_date not in data:
        print(f"⚠️ Attenzione: data {target_date} non trovata nel file locale.")
        return []

    soccer_events = data[target_date].get("All Soccer Events", [])
    return [e for e in soccer_events if is_important(e.get("event", ""))]

def save_m3u_with_groups(all_links, filename="gruppata.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        grouped = {}
        for group_title, channel_name, url in all_links:
            grouped.setdefault(group_title, []).append((channel_name, url))
        for group_title, channels in grouped.items():
            for channel_name, url in channels:
                f.write(f'#EXTINF:-1 group-title="{group_title}",{channel_name}\n')
                f.write("#EXTVLCOPT:http-referrer=https://jxoplay.xyz/\n")
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/2.1 TV Safari/537.36\n")
                f.write(url + "\n")

def main():
    today_str = get_today_date_string()
    print(f"📅 Estrazione eventi importanti Soccer per la data: {today_str}\n")

    events = get_soccer_events_for_date(today_str)
    all_links = []

    print(f"Trovati {len(events)} eventi Soccer importanti da processare\n")

    for event in events:
        event_name = event.get("event", "Unknown Event")
        time_ev = event.get("time", "")
        time_plus2 = add_two_hours(time_ev)

        all_channels = event.get("channels", []) + event.get("channels2", [])

        for channel in all_channels:
            if isinstance(channel, dict):
                channel_name = channel.get("channel_name", "Unknown Channel")
                channel_id = channel.get("channel_id")

                for path in PLAYER_PATHS:
                    php_url = f"https://daddylivestream.com/{path}/stream-{channel_id}.php"
                    print(f"🕒 {time_ev} | 🏟 {event_name}")
                    print(f"   📺 Canale: {channel_name} (ID: {channel_id})")
                    print(f"   🔗 Link diretto: {php_url}")

                    all_links.append((f"[{time_plus2}] {event_name}", channel_name, php_url))
            else:
                print(f"⚠️ Formato imprevisto per channel: {channel}")

    save_m3u_with_groups(all_links, filename="televizoeve.m3u")
    print(f"\n✅ Playlist creata: gruppata.m3u")

if __name__ == "__main__":
    main()
