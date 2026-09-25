"""Weekly stories job.

Sources (all free and legal to read):
  * Project Madurai (projectmadurai.org) - public-domain / freely distributable
    Tamil etexts. We build a catalog and convert story-type works to clean,
    paged text the app can read offline and read aloud.
  * FreeTamilEbooks (freetamilebooks.com) - Creative Commons ebooks. Downloads
    are behind a browser challenge, so the app shows them and opens the book
    page in the browser.

New items are detected by diffing against the previous catalog (first_seen).
"""
import html
import re
import sys
import time


from common import OUT, get, load_json, save_json, today_ist

PM_BASE = "https://www.projectmadurai.org"
FTE_API = "https://freetamilebooks.com/wp-json/wp/v2"

GROUPS = [  # (group id, Tamil label, genre substrings)
    ("novel", "நாவல்கள்", ["நாவல்", "புதினம்"]),
    ("kids", "சிறுவர் கதைகள்", ["சிறுவர்"]),
    ("short", "சிறுகதைகள்", ["சிறுகதை", "கதைகள்", "கதை"]),
    ("devotional", "பக்தி & புராணம்", ["சமயம்", "புராணம்", "இதிகாசம்", "பக்தி", "சைவ", "வைணவ", "சித்தர்", "ஆன்மிக", "பண்டார"]),
    ("drama", "நாடகம்", ["நாடக"]),
    ("history", "வரலாறு", ["வரலாறு", "சரித்திரம்", "வாழ்க்கை"]),
    ("poetry", "கவிதை & பாடல்", ["கவிதை", "பாடல்", "பிரபந்தம்", "காப்பியம்", "காவியம்", "சங்க", "நீதி", "இசை"]),
    ("essay", "கட்டுரைகள்", ["கட்டுரை", "சொற்பொழிவு", "திறனாய்வு", "இலக்கியம்", "பயணம்", "சமூகம்", "நலம்", "மெய்யியல்"]),
]
SKIP_GENRE = ["கிருத்துவம்", "இஸ்லாமியம்"]  # keep catalog focused on what Amma reads


def group_for(genre):
    for gid, _label, keys in GROUPS:
        if any(k in genre for k in keys):
            return gid
    return "other"


def _txt(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()


def pm_catalog():
    s = get(f"{PM_BASE}/pmworks.html").content.decode("utf-8", "replace")
    works = []
    for row in re.findall(r"<tr>(.*?)</tr>", s, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(tds) < 6:
            continue
        num, title, author, genre = (_txt(t) for t in tds[:4])
        parts = re.findall(r'href="([^"]*utf8[^"]+\.html?)"', tds[5])
        if not num.isdigit() or not parts or not title:
            continue
        if any(k in genre for k in SKIP_GENRE):
            continue
        gid = group_for(genre)
        works.append({
            "id": f"pm{int(num):04d}", "source": "pm", "title": title,
            "author": author or "", "genre": genre, "group": gid,
            "parts": [PM_BASE + p if p.startswith("/") else p for p in parts],
            "readable": True,  # every Project Madurai text opens in the in-app reader
        })
    return works


def fte_terms(kind):
    out, page = {}, 1
    while True:
        r = get(f"{FTE_API}/{kind}", params={"per_page": 100, "page": page, "_fields": "id,name"})
        items = r.json()
        out.update({i["id"]: html.unescape(i["name"]) for i in items})
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return out
        page += 1


def fte_catalog():
    genres, authors = fte_terms("genres"), fte_terms("authors")
    books, page = [], 1
    while True:
        r = get(f"{FTE_API}/ebooks", params={"per_page": 100, "page": page,
                                            "_fields": "id,date,link,title,genres,authors"})
        for b in r.json():
            g = ", ".join(genres.get(x, "") for x in b.get("genres", []))
            books.append({
                "id": f"fte{b['id']}", "source": "fte", "title": _txt(b["title"]["rendered"]),
                "author": ", ".join(authors.get(a, "") for a in b.get("authors", [])),
                "genre": g, "group": group_for(g), "link": b["link"],
                "published": b["date"][:10], "readable": False,
            })
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return books
        page += 1
        time.sleep(0.5)


def main():
    day = today_ist().isoformat()
    out = OUT / "data"
    prev = load_json(out / "catalog.json", {})
    first_run = not prev
    seen = {w["id"]: w.get("first_seen", day) for w in prev.get("works", [])}

    works = []
    try:
        works += pm_catalog()
    except Exception as e:
        print(f"PM catalog failed: {e}", file=sys.stderr)
        works += [w for w in prev.get("works", []) if w["source"] == "pm"]
    try:
        works += fte_catalog()
    except Exception as e:
        print(f"FTE catalog failed: {e}", file=sys.stderr)
        works += [w for w in prev.get("works", []) if w["source"] == "fte"]

    for w in works:
        w["first_seen"] = seen.get(w["id"], "2000-01-01" if first_run else day)
        if not w.get("readable"):
            w.pop("parts", None)

    new_items = sorted((w for w in works if w["first_seen"] == day and not first_run),
                       key=lambda w: w["title"])
    groups = [{"id": g, "label": label} for g, label, _ in GROUPS] + [{"id": "other", "label": "மற்றவை"}]
    save_json(out / "catalog.json", {"updated": day, "groups": groups, "works": works})
    save_json(out / "new.json", {"updated": day, "ids": [w["id"] for w in new_items]})
    print(f"catalog: {len(works)} works, {sum(w['readable'] for w in works)} readable in-app, "
          f"{len(new_items)} new")


if __name__ == "__main__":
    main()
