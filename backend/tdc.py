"""Reads today's sheet and the year's special days from tamildailycalendar.com.

The site only serves *today's* sheet to plain requests (its date picker ignores
query parameters), so this runs once a day and history accumulates on our side.
"""
import datetime as dt
import re

from bs4 import BeautifulSoup

from common import get

BASE = "https://www.tamildailycalendar.com/"
DATE_RE = re.compile(r"(\d{1,2})\s*-\s*([A-Za-z]{3})-(\d{4})")
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# English label on the site -> our key
SHEET_KEYS = {
    "Date": "date", "Today": "today", "Nalla Neram": "nalla_neram",
    "Gowri Nalla Neram": "gowri_nalla_neram", "Raahu Kaalam": "rahu_kalam",
    "Yemagandam": "emagandam", "Kuligai": "kuligai", "Soolam": "soolam",
    "Parigaram": "parigaram", "Chandirashtamam": "chandirashtamam", "Naal": "naal",
    "Lagnam": "lagnam", "Sun Rise": "sunrise", "Sraardha Thithi": "sraardha_thithi",
    "Thithi": "thithi", "Star": "nakshatram", "Subakariyam": "subakariyam",
}

# Month-summary names on the site -> note keys in data/day_notes.json
SPECIAL_KEYS = {
    "amavasai": "amavasai", "pournami": "pournami", "karthigai": "karthigai",
    "sashti viradham": "sashti", "sashti": "sashti",
    "sankatahara chathurthi": "sankatahara_chathurthi", "chathurthi": "chathurthi",
    "pradosham": "pradosham", "thiruvonam": "thiruvonam",
    "maadha sivarathiri": "maadha_sivarathiri", "ekadhasi": "ekadasi", "ekadasi": "ekadasi",
    "ashtami": "ashtami", "navami": "navami",
}

# Festival names (English part, lower-case, substring match) -> note keys
FESTIVAL_KEYS = [
    ("kerpotta", None), ("agni", None), ("navaratri begins", "navarathiri"), ("vinayagar", "vinayagar_chathurthi"), ("vaigunta", "vaikunta_ekadasi"), ("sankadahara", None), ("vinayaka", "vinayagar_chathurthi"),
    ("gokul", "gokulashtami"), ("krishna jayanthi", "gokulashtami"),
    ("mahalaya amavasai", "mahalaya_amavasai"), ("mahalaya", "mahalaya_paksham"),
    ("navarathri", "navarathiri"), ("navarathiri", "navarathiri"), ("navaratri", "navarathiri"),
    ("saraswathi", "saraswathi_pooja"), ("saraswati", "saraswathi_pooja"), ("ayutha", "saraswathi_pooja"), ("aayudha", "saraswathi_pooja"),
    ("vijaya", "vijayadasami"), ("deepavali", "deepavali"), ("diwali", "deepavali"),
    ("soorasamharam", "kandha_sashti"), ("skanda sashti", "kandha_sashti"), ("kandha sashti", "kandha_sashti"),
    ("karthigai deepam", "karthigai_deepam"), ("thirukkarth", "karthigai_deepam"), ("thirukarth", "karthigai_deepam"), ("vaikunta", "vaikunta_ekadasi"),
    ("bhogi", "bhogi"), ("mattu", "mattu_pongal"), ("maattu", "mattu_pongal"), ("pongal", "pongal"),
    ("thaipoosam", "thaipoosam"), ("thai poosam", "thaipoosam"), ("mahasivarathiri", "maha_sivarathiri"), ("ramanavami", "sri_rama_navami"), ("panguni uth", "panguni_uthiram"), ("bogi", "bhogi"), ("thai pongal", "pongal"), ("thai poosam", "thaipoosam"),
    ("maha sivarathiri", "maha_sivarathiri"), ("maha shivaratri", "maha_sivarathiri"),
    ("tamil new year", "tamil_puthandu"), ("puthandu", "tamil_puthandu"),
    ("rama navami", "sri_rama_navami"), ("panguni uthiram", "panguni_uthiram"),
    ("aadi perukku", "aadi_perukku"), ("aadi amavasai", "aadi_amavasai"),
    ("varalakshmi", "varalakshmi_viratham"), ("avani avittam", "aavani_avittam"),
    ("aavani avittam", "aavani_avittam"), ("hanuman", "hanuman_jayanthi"),
]


def _cells(tr):
    return [td.get_text(" | ", strip=True) for td in tr.find_all(["td", "th"], recursive=False)]


def _dates(text):
    out = []
    for d, mon, y in DATE_RE.findall(text):
        if mon in MONTHS:
            out.append(dt.date(int(y), MONTHS[mon], int(d)).isoformat())
    return out


def festival_key(name):
    low = name.lower()
    for needle, key in FESTIVAL_KEYS:
        if needle in low:
            return key
    return None


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = [c for c in (_cells(tr) for tr in soup.find_all("tr") if not tr.find("table")) if any(c)]
    sheet, specials, festivals, holidays, weddings = {}, {}, {}, {}, set()
    heading_date = None
    m = re.search(r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|"
                  r"October|November|December) (\d{4}) [A-Za-z]+day", soup.get_text(" "))
    if m:
        heading_date = dt.datetime.strptime(" ".join(m.groups()), "%d %B %Y").date().isoformat()
    for cells in rows:
        first = cells[0]
        if len(cells) == 2 and " | " in first:
            ta, _, en = first.partition(" | ")
            if en.strip() in SHEET_KEYS and not DATE_RE.search(cells[1]):
                sheet[SHEET_KEYS[en.strip()]] = {"label": ta.strip(), "value": cells[1].replace(" | ", "  ")}
                continue
        low = first.strip().lower()
        if low in ("govt holidays", "festivals", "wedding days") and len(cells) >= 2:
            entries, cur = [], None
            for tok in cells[1].split(" | "):
                tok = tok.strip()
                ds = _dates(tok)
                if ds:
                    cur = [ds[0], []]
                    entries.append(cur)
                elif cur is not None and tok and tok != ".":
                    cur[1].append(tok)
            for d, parts in entries:
                if low == "wedding days":
                    weddings.add(d)
                    continue
                target = festivals if low == "festivals" else holidays
                ta = parts[0] if parts else ""
                en = parts[1] if len(parts) > 1 else ""
                item = {"ta": ta, "en": en, "key": festival_key(en or ta)}
                if item not in target.setdefault(d, []):
                    target[d].append(item)
            continue
        if len(cells) >= 2 and not DATE_RE.search(first) and DATE_RE.search(cells[1]):
            key = SPECIAL_KEYS.get(first.strip().lower())
            if key:
                for d in _dates(cells[1]):
                    specials.setdefault(d, [])
                    if key not in specials[d]:
                        specials[d].append(key)
    return {
        "heading_date": heading_date,
        "sheet": sheet,
        "specials": specials,
        "festivals": festivals,
        "holidays": holidays,
        "wedding_days": sorted(weddings),
    }


def fetch_today():
    html = get(BASE + "tamil_daily_calendar.php").text
    data = parse(html)
    if not data["sheet"].get("date"):
        raise RuntimeError("tamildailycalendar.com layout changed: daily sheet not found")
    return data
