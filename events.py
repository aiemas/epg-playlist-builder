#!/usr/bin/env python3

"""
events.py — live-events playlist builder with ENHANCED EPG/LOGO MATCHING

• validates DaddyLive streams
• assigns channel logos using improved brand detection
• maps the **correct** tvg-id from epgshare01 with fixed country preference
• prevents incorrect fallbacks that map unrelated channels
• enhanced verbose logging for debugging and progress tracking

USAGE EXAMPLES:
===============

# Basic run (minimal output)
python events.py

# Verbose mode with progress bars
python events.py -v

# Debug mode (very detailed output)
python events.py -vv

# Quiet mode (errors only)
python events.py --quiet

# Custom worker count with verbose output
python events.py -v --workers 50

FEATURES:
=========
- Enhanced country detection from channel names (e.g., "Sky Sports Racing UK")
- Improved EPG matching with proper country priority (UK > IE > US > etc.)
- Better logo matching using direct API channel names
- Prevents incorrect fallbacks to unrelated channels
- Comprehensive logging with emoji indicators for easy debugging
- Progress bars for long-running operations
- Configurable worker threads for stream validation
- Statistics tracking for EPG and logo match success rates
"""

from __future__ import annotations

import argparse
import base64
import difflib
import logging
import re
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from tqdm import tqdm

# ═════════════════════════════ constants ═══════════════════════════════════

SCHEDULE_URL = "https://daddylive.dad/schedule/schedule-generated.php"
PROXY_PREFIX = "https://aiemas-dproxy.hf.space/watch/"
OUTPUT_FILE = "schedule_playlist.m3u8"
EPG_IDS_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.txt"
EPG_XML_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
TVLOGO_RAW = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/"
TVLOGO_API = "https://api.github.com/repos/tv-logo/tv-logos/contents/countries"

URL_TEMPLATES = [
    "https://nfsnew.newkso.ru/nfs/premium{num}/mono.m3u8",
    "https://windnew.newkso.ru/wind/premium{num}/mono.m3u8",
    "https://zekonew.newkso.ru/zeko/premium{num}/mono.m3u8",
    "https://dokko1new.newkso.ru/dokko1/premium{num}/mono.m3u8",
    "https://ddy6new.newkso.ru/ddy6/premium{num}/mono.m3u8",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    ),
    "Referer": "https://daddylive.dad/24-7-channels.php",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

VLC_HEADERS = [
    "#EXTVLCOPT:http-origin=https://lefttoplay.xyz",
    "#EXTVLCOPT:http-referrer=https://lefttoplay.xyz/",
    "#EXTVLCOPT:http-user-agent="
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
    "Mobile/15E148 Safari/604.1",
]

# ═════ ENHANCED country helper with better detection ═══════════════════════

COUNTRY_CODES = {
    'usa': 'us', 'united states': 'us', 'america': 'us',
    'uk': 'uk', 'united kingdom': 'uk', 'britain': 'uk', 'england': 'uk',
    'canada': 'ca', 'can': 'ca',
    'australia': 'au', 'aus': 'au',
    'new zealand': 'nz', 'newzealand': 'nz',
    'germany': 'de', 'deutschland': 'de', 'german': 'de',
    'france': 'fr', 'french': 'fr',
    'spain': 'es', 'españa': 'es', 'spanish': 'es',
    'italy': 'it', 'italia': 'it', 'italian': 'it',
    'croatia': 'hr', 'serbia': 'rs', 'netherlands': 'nl', 'holland': 'nl',
    'portugal': 'pt', 'poland': 'pl', 'greece': 'gr', 'bulgaria': 'bg',
    'israel': 'il', 'malaysia': 'my', 'ireland': 'ie', 'slovakia': 'sk',
}

# Country priority order - UK gets highest priority, followed by other English-speaking countries
COUNTRY_PRIORITY = ['uk', 'gb', 'us', 'ca', 'au', 'nz', 'ie', 'de', 'fr', 'es', 'it', 'nl', 'pt', 'pl', 'sk']

# ═════ ENHANCED abbreviation map used both ways ═══════════════════════════

ABBR_MAP = {
    "sp": "sports",
    "sp1": "sports1",
    "sp2": "sports2",
    "sn": "sportsnetwork",
    "soc": "soccer",
    "mn": "mainevent",
    "nw": "network",
}

# ═════════════════════════════ ENHANCED Channel Info Extraction ═══════════════════════════

def extract_channel_info(name: str) -> tuple[str, str]:
    """
    ENHANCED channel name parsing with better country detection
    Return (brand, ISO-2 country) from strings like
    "Sky Sports Racing UK", "JOJ Sport Slovakia HD", "BBC Two (UK)", etc.
    """
    name = name.strip()
    logging.debug(f"📍 Parsing channel: '{name}'")

    # Handle parenthetical country codes first
    m = re.search(r'^(.*?)\s*\(([^)]+)\)$', name)
    if m:
        country_text = m.group(2).lower()
        brand = m.group(1).strip()
        country = COUNTRY_CODES.get(country_text, 'unknown')
        logging.debug(f"📍 Parenthetical country: '{name}' -> brand: '{brand}', country: '{country}'")
        return brand, country

    # Enhanced country detection patterns for various formats
    country_patterns = [
        r'\b(slovakia|slovak)\s+hd$',  # "JOJ Sport Slovakia HD"
        r'\b(uk|united kingdom|britain)\b$',  # "Sky Sports Racing UK"
        r'\b(poland|polish)\b$',  # "Polsat Sport 3 Poland"
        r'\b(ireland|irish)\b$',  # Irish channels
        r'\b(france|french)\b$',  # French channels
        r'\b(germany|german)\b$',  # German channels
        r'\b(spain|spanish)\b$',  # Spanish channels
        r'\b(italy|italian)\b$',  # Italian channels
    ]

    name_lower = name.lower()

    # Check for country patterns
    for pattern in country_patterns:
        match = re.search(pattern, name_lower)
        if match:
            country_name = match.group(1)
            country_code = COUNTRY_CODES.get(country_name, 'unknown')

            # Extract brand by removing country part
            brand = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
            logging.debug(f"📍 Pattern match: '{name}' -> brand: '{brand}', country: '{country_code}'")
            return brand, country_code

    # Original logic for space-separated countries
    parts = name.split()
    for i in range(len(parts) - 1, 0, -1):
        maybe = ' '.join(parts[i:]).lower()
        if maybe in COUNTRY_CODES:
            brand = ' '.join(parts[:i]).strip()
            country = COUNTRY_CODES[maybe]
            logging.debug(f"📍 Space-separated: '{name}' -> brand: '{brand}', country: '{country}'")
            return brand, country

    # Check for embedded country names
    for country_name, code in COUNTRY_CODES.items():
        if country_name in name_lower:
            brand = re.sub(rf'\b{re.escape(country_name)}\b', '', name, flags=re.I).strip()
            logging.debug(f"📍 Embedded country: '{name}' -> brand: '{brand}', country: '{code}'")
            return brand, code

    logging.debug(f"📍 No country detected: '{name}' -> brand: '{name}', country: 'unknown'")
    return name, 'unknown'

# ── abbreviation utils ────────────────────────────────────────────────────

def _expand_abbr(slug: str) -> list[str]:
    res = {slug}
    for ab, full in ABBR_MAP.items():
        if ab in slug:
            res.add(slug.replace(ab, full))
    return list(res)

def _compress_long(slug: str) -> list[str]:
    res = {slug}
    for ab, full in ABBR_MAP.items():
        if full in slug:
            res.add(slug.replace(full, ab))
    return list(res)

# ── ENHANCED EPG lookup build ──────────────────────────────────────────────

def build_epg_lookup(lines: list[str]) -> dict[str, list[str]]:
    """
    ENHANCED EPG lookup table builder with progress tracking
    For every EPG line create MANY aliases, so
    TNT.Sports.4.HD.uk → tnt sports 4 hd, tnt sports 4, tnt sports …
    All aliases also exist with the country suffix: "… uk".
    """
    logging.info("📋 Building EPG lookup table...")
    table: dict[str, list[str]] = defaultdict(list)

    processed = 0
    for line in tqdm(lines, desc="Processing EPG entries", disable=not logging.getLogger().isEnabledFor(logging.INFO)):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue

        processed += 1

        # split "… .uk" or keep whole line if no country code
        parts = raw.split(".")
        country = parts[-1].lower() if len(parts) > 1 and len(parts[-1]) == 2 else None
        brand = parts[:-1] if country else parts  # every block except cc
        brand_sp = " ".join(brand)  # dotted → spaced words
        brand_cl = re.sub(r"[^a-z0-9 ]", " ", brand_sp.lower())
        brand_cl = re.sub(r"\s+", " ", brand_cl).strip()  # normalised

        # progressive prefixes: "tnt sports 4 hd" → full, drop "hd", drop "4", …
        words = brand_cl.split()
        for i in range(len(words), 0, -1):
            frag = " ".join(words[:i])
            for key in (frag, frag.replace(" ", "")):  # spaced and slug form
                table[key].append(raw)
                if country:
                    table[f"{key}.{country}"].append(raw)

        # original full lower-cased line for safety
        table[raw.lower()].append(raw)

        # Add progressive prefixes for better matching
        if len(parts) > 1:
            for i in range(1, len(parts)):
                partial = '.'.join(parts[:i]).lower()
                table[partial].append(raw)

    logging.info(f"✅ EPG lookup built: {len(table)} unique keys from {processed} entries")
    return table

# ── ENHANCED brand variation generator ─────────────────────────────────────

def generate_brand_variations(brand: str) -> list[str]:
    """Generate comprehensive variations of brand names for matching"""
    out: set[str] = set()
    b = brand.lower()

    # Add base brand variations
    out.add(b)
    out.add(b.replace(' ', ''))

    # Remove common suffixes
    out.add(re.sub(r'\b(tv|hd|sd|channel|network|sports?|news)\b', '', b).strip())

    # Number replacements
    num = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'}
    for word, dig in num.items():
        if word in b:
            out.add(b.replace(word, dig))

    # Sport/Sports variations
    if 'sports' in b:
        out.add(b.replace('sports', 'sport'))
    if 'sport' in b and 'sports' not in b:
        out.add(b.replace('sport', 'sports'))

    # Network name compressions
    nets = {
        'espn': 'espn', 'fox sports': 'foxsports',
        'sky sports': 'skysports', 'tnt sports': 'tntsports',
        'bein sports': 'beinsports', 'bt sport': 'btsport'
    }
    for full, short in nets.items():
        if full in b:
            out.add(b.replace(full, short))

    # Add abbreviation expansions and compressions
    slug = b.replace(' ', '')
    out |= set(_compress_long(slug))
    out |= set(_expand_abbr(slug))
    out.add(slug)

    return [v for v in out if v.strip()]

# ── ENHANCED country ranking for competing IDs ─────────────────────────────

def _best_by_country(matches: list[str], prefer: str | None) -> str:
    """
    ENHANCED country preference with detailed logging
    Select best match based on country preference
    """
    if not matches:
        return ""

    if len(matches) == 1:
        return matches[0]

    logging.debug(f"🎯 Choosing from {len(matches)} matches for country '{prefer}': {matches}")

    # If we have a preferred country, try to find exact match
    if prefer:
        for match in matches:
            if match.lower().endswith(f".{prefer}"):
                logging.debug(f"✅ Country preference: Selected '{match}' (preferred: {prefer})")
                return match

    # Apply enhanced country priority ranking
    for country_code in COUNTRY_PRIORITY:
        for match in matches:
            if match.lower().endswith(f".{country_code}"):
                logging.debug(f"🏆 Priority selection: Selected '{match}' (priority: {country_code})")
                return match

    # Return first match if no country priority applies
    best = matches[0]
    logging.debug(f"🔄 Fallback: Selected '{best}'")
    return best

# ── ENHANCED EPG match with better fallback prevention ─────────────────────

def find_best_epg_match(channel_name: str, lookup: dict[str, list[str]]) -> str:
    """
    ENHANCED EPG matching with better fallback logic to prevent incorrect matches
    """
    logging.debug(f"🔍 EPG: Searching for '{channel_name}'")

    brand, country = extract_channel_info(channel_name)
    brand_lc = brand.lower()
    slug = brand_lc.replace(' ', '')

    # Build comprehensive search keys in priority order
    keys: list[str] = []

    # Country-specific matches (highest priority)
    if country != 'unknown':
        keys.extend([
            f"{brand_lc}.{country}",
            f"{slug}.{country}",
            f"{brand_lc}.{country}.hd",
            f"{slug}.{country}.hd"
        ])

    # Brand-only matches
    keys.extend([brand_lc, slug])

    # Brand variations
    for variation in generate_brand_variations(brand):
        keys.append(variation)
        if country != 'unknown':
            keys.append(f"{variation}.{country}")

    # Search through keys with detailed logging
    for key in keys:
        if key in lookup:
            matches = lookup[key]
            best_match = _best_by_country(matches, None if country == 'unknown' else country)
            logging.debug(f"✅ EPG: Key match '{key}' -> '{best_match}'")
            return best_match

    # Enhanced fuzzy matching with country awareness
    candidates = []
    for lookup_key in lookup:
        if len(lookup_key) >= 3:
            # Prefer candidates from the same country
            if country != 'unknown' and lookup_key.endswith(f'.{country}'):
                candidates.insert(0, lookup_key)  # Add to front
            else:
                candidates.append(lookup_key)

    # Try fuzzy matching with brand name
    fuzzy_matches = difflib.get_close_matches(slug, candidates, n=3, cutoff=0.65)
    if fuzzy_matches:
        # Collect all matches from fuzzy results
        all_matches = []
        for fm in fuzzy_matches:
            all_matches.extend(lookup[fm])

        if all_matches:
            best_match = _best_by_country(all_matches, country if country != 'unknown' else None)
            logging.debug(f"🔍 EPG: Fuzzy match -> '{best_match}'")
            return best_match

    # If no good match found, return empty string instead of wrong fallback
    logging.debug(f"❌ EPG: No suitable match for '{channel_name}' - avoiding incorrect fallback")
    return ""

# ═════ ENHANCED logo helpers ═══════════════════════════════════════════════

def slugify(text: str) -> str:
    txt = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    txt = txt.replace("&amp;", "-and-").replace("+", "-plus-")
    txt = re.sub(r"[^\w\s-]", "", txt)
    return re.sub(r"\s+", "-", txt).strip("-")

def build_logo_index(sess: requests.Session) -> dict[str, str]:
    """
    ENHANCED logo index builder with progress tracking
    """
    logging.info("🖼️  Building logo index from GitHub...")
    index: dict[str, str] = {}

    try:
        logging.debug("📡 Fetching country directories...")
        countries = [d["name"] for d in sess.get(TVLOGO_API, timeout=30).json()
                    if d["type"] == "dir"]

        logging.info(f"🌍 Found {len(countries)} country directories")

        with tqdm(countries, desc="Processing countries", disable=not logging.getLogger().isEnabledFor(logging.INFO)) as pbar:
            for c in pbar:
                pbar.set_description(f"Processing {c}")
                logging.debug(f"📁 Processing country: {c}")

                try:
                    r = sess.get(f"{TVLOGO_API}/{c}", timeout=30)
                    country_logos = 0

                    for f in r.json():
                        if f["type"] != "file" or not f["name"].endswith(".png"):
                            continue

                        base = f["name"][:-4]
                        url = f"{TVLOGO_RAW}{c}/{f['name']}"
                        index.update({f["name"]: url, base: url})
                        country_logos += 1

                        # Add country-less versions for better matching
                        for suf in ("-us", "-uk", "-ca", "-au", "-de", "-fr", "-es", "-it", "-sk", "-pl"):
                            if base.endswith(suf):
                                index[base[:-len(suf)]] = url

                    logging.debug(f"✅ {c}: {country_logos} logos processed")

                except Exception as e:
                    logging.warning(f"⚠️  Failed to process {c}: {e}")

    except Exception as e:
        logging.error(f"❌ Logo index build failed: {e}")

    logging.info(f"✅ Logo index built: {len(index)} logo variants")
    return index

def find_best_logo(name: str, logos: dict[str, str]) -> str:
    """
    ENHANCED logo matching with better country/brand detection
    """
    if not logos:
        logging.debug(f"❌ LOGO: No logos available for '{name}'")
        return f"{TVLOGO_RAW}misc/no-logo.png"

    logging.debug(f"🔍 LOGO: Searching for '{name}'")

    # Extract brand and country
    brand, country = extract_channel_info(name)
    brand_slug = slugify(brand)

    # Search patterns in priority order
    search_patterns = []

    # Country-specific logos (highest priority)
    if country != 'unknown':
        search_patterns.extend([
            f"{brand_slug}-{country}",
            f"{brand_slug}.{country}",
        ])

    # Brand-only patterns
    search_patterns.extend([
        brand_slug,
        brand_slug.replace('-', ''),
    ])

    # Brand variations
    for var in generate_brand_variations(brand):
        var_slug = slugify(var)
        search_patterns.append(var_slug)
        if country != 'unknown':
            search_patterns.append(f"{var_slug}-{country}")

    # Original name as fallback
    search_patterns.append(slugify(name))

    # Search through patterns
    for pattern in search_patterns:
        if not pattern:
            continue

        # Try exact match
        if pattern in logos:
            logo_url = logos[pattern]
            logging.debug(f"✅ LOGO: Match found '{name}' -> '{logo_url}'")
            return logo_url

        # Try with .png extension
        png_pattern = f"{pattern}.png"
        if png_pattern in logos:
            logo_url = logos[png_pattern]
            logging.debug(f"✅ LOGO: PNG match '{name}' -> '{logo_url}'")
            return logo_url

        # Try without HD/SD suffixes
        for suffix in ["-hd", "-sd"]:
            clean_pattern = pattern.replace(suffix, "")
            if clean_pattern in logos:
                logo_url = logos[clean_pattern]
                logging.debug(f"✅ LOGO: Clean match '{name}' -> '{logo_url}'")
                return logo_url

    logging.debug(f"❌ LOGO: No match for '{name}'")
    return f"{TVLOGO_RAW}misc/no-logo.png"

# ═════ schedule / streams ══════════════════════════════════════════════════

def get_schedule():
    """
    Fetch schedule with enhanced logging
    """
    logging.info("📅 Fetching schedule from DaddyLive...")
    try:
        r = requests.get(SCHEDULE_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        schedule = r.json()

        # Count events
        total_events = sum(len(events) for cats in schedule.values() for events in cats.values())
        logging.info(f"✅ Schedule fetched: {total_events} events across {len(schedule)} time slots")

        return schedule
    except Exception as e:
        logging.error(f"❌ Failed to fetch schedule: {e}")
        raise

def _extract_cid(item) -> str:
    return str(item["channel_id"]) if isinstance(item, dict) else str(item)

def _channel_entries(event):
    for key in ("channels", "channels2"):
        val = event.get(key)
        if not val:
            continue
        if isinstance(val, list):
            yield from val
        elif isinstance(val, dict)
      Add events.py with custom proxy
  
