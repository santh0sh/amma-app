"""Picks the image of the day: rotates categories, rotates all gods, festival override."""
import datetime as dt
import io

from PIL import Image

from common import DATA, get, load_json

CYCLE = ["god", "nature", "peacock", "flowers", "kids"]
# Krishna appears once per round, every other god twice (her wallpaper is already Krishna).
GOD_ROUND = ["ganesha", "murugan", "lakshmi", "shiva", "santoshi", "vishnu", "hanuman",
             "durga", "saraswati", "rama", "ayyappan", "krishna",
             "ganesha", "murugan", "lakshmi", "shiva", "santoshi", "vishnu", "hanuman",
             "durga", "saraswati", "rama", "ayyappan"]
DEITY_FOR = {
    "gokulashtami": "krishna", "vinayagar_chathurthi": "ganesha",
    "sankatahara_chathurthi": "ganesha", "chathurthi": "ganesha",
    "pradosham": "shiva", "sani_pradosham": "shiva", "maadha_sivarathiri": "shiva",
    "maha_sivarathiri": "shiva", "sashti": "murugan", "karthigai": "murugan",
    "kandha_sashti": "murugan", "thaipoosam": "murugan", "panguni_uthiram": "murugan",
    "ekadasi": "vishnu", "vaikunta_ekadasi": "vishnu", "thiruvonam": "vishnu",
    "purattasi_sani": "vishnu", "navarathiri": "durga", "saraswathi_pooja": "saraswati",
    "vijayadasami": "durga", "varalakshmi_viratham": "lakshmi", "deepavali": "lakshmi",
    "sri_rama_navami": "rama", "hanuman_jayanthi": "hanuman", "karthigai_deepam": "shiva",
}
# Festivals outrank monthly special days when both fall on one day.
PRIORITY = ["festival", "special"]
NO_REPEAT_DAYS = 45
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def pool():
    base = load_json(DATA / "image_pool.json", {})
    return base


def choose_tag(day: dt.date, day_keys: dict):
    """day_keys: {'festival': [...keys], 'special': [...keys]} -> (tag, reason_key)"""
    for level in PRIORITY:
        for key in day_keys.get(level, []):
            if key in DEITY_FOR:
                return DEITY_FOR[key], key
    cat = CYCLE[day.toordinal() % len(CYCLE)]
    if cat != "god":
        return cat, None
    god_days = day.toordinal() // len(CYCLE)
    return GOD_ROUND[god_days % len(GOD_ROUND)], None


def choose_image(tag: str, day: dt.date, used: dict, extra: dict | None = None):
    items = list(pool().get(tag, [])) + list((extra or {}).get(tag, []))
    if not items:
        items = [i for v in pool().values() for i in v if i["category"] == "nature"]

    def last_used(item):
        d = used.get(item["title"])
        return dt.date.fromisoformat(d) if d else dt.date.min

    fresh = [i for i in items if (day - last_used(i)).days > NO_REPEAT_DAYS]
    candidates = fresh or sorted(items, key=last_used)[:max(1, len(items) // 3)]
    return candidates[day.toordinal() % len(candidates)]


def download(item, width=1400) -> Image.Image:
    r = get(COMMONS_API, params=dict(action="query", format="json", prop="imageinfo",
                                     titles=item["title"], iiprop="url", iiurlwidth=width))
    page = next(iter(r.json()["query"]["pages"].values()))
    url = page["imageinfo"][0].get("thumburl") or page["imageinfo"][0]["url"]
    return Image.open(io.BytesIO(get(url).content)).convert("RGB")
