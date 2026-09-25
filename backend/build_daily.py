"""Daily job: calendar + day notes + image of the day + good-morning cards.

Writes into $AMMA_OUT (the `data` branch checkout), which the app reads via
raw.githubusercontent.com. Safe to re-run: same day gives the same result.
"""
import datetime as dt
import sys

import card
import images
import tdc
from common import DATA, OUT, load_json, save_json, today_ist

WEEKDAY_TA = card.WEEKDAY_TA
TAMIL_MONTHS = ["சித்திரை", "வைகாசி", "ஆனி", "ஆடி", "ஆவணி", "புரட்டாசி", "ஐப்பசி",
                "கார்த்திகை", "மார்கழி", "தை", "மாசி", "பங்குனி"]
NOTES = load_json(DATA / "day_notes.json", {})
KEEP_CARDS = 7
ALT_CATEGORIES = ["god", "nature", "peacock", "flowers", "kids"]


def note_for(section, key):
    return NOTES.get(section, {}).get(key)


def tamil_date(sheet):
    """'8 - புரட்டாசி - பராபவ  வெள்ளி' -> (month, day)"""
    val = (sheet.get("date") or {}).get("value", "")
    parts = [p.strip() for p in val.split("-")]
    try:
        return parts[1], int(parts[0])
    except (IndexError, ValueError):
        return None, None


def merge_calendar(cal, parsed, day):
    for field in ("specials", "festivals", "holidays"):
        cal.setdefault(field, {}).update(parsed[field])
    cal["wedding_days"] = sorted(set(cal.get("wedding_days", [])) | set(parsed["wedding_days"]))
    cal.setdefault("sheets", {})[day.isoformat()] = parsed["sheet"]
    tm, td = tamil_date(parsed["sheet"])
    if tm:
        cal.setdefault("tamil_dates", {})[day.isoformat()] = [tm, td]
    # keep a year of sheets
    cutoff = (day - dt.timedelta(days=400)).isoformat()
    cal["sheets"] = {k: v for k, v in cal["sheets"].items() if k >= cutoff}
    return cal


def estimate_tamil(cal, d):
    """Best-effort Tamil month/day for dates near a known one (same month only)."""
    known = cal.get("tamil_dates", {})
    if d.isoformat() in known:
        return tuple(known[d.isoformat()])
    for back in range(1, 32):
        ref = (d - dt.timedelta(days=back)).isoformat()
        if ref in known:
            m, day_no = known[ref]
            if day_no + back <= 29:
                return m, day_no + back
            return None, None
    return None, None


def day_info(cal, d):
    iso = d.isoformat()
    items = []
    sp = list(cal.get("specials", {}).get(iso, []))
    if d.weekday() == 5 and "pradosham" in sp:
        sp[sp.index("pradosham")] = "sani_pradosham"
    if iso in cal.get("wedding_days", []):
        sp.append("subamuhurtham")
    tm, td = estimate_tamil(cal, d)
    if tm == "புரட்டாசி" and d.weekday() == 5:
        items.append({"kind": "festival", "key": "purattasi_sani", **note_for("festival", "purattasi_sani")})
    for f in cal.get("festivals", {}).get(iso, []):
        n = note_for("festival", f.get("key")) if f.get("key") else None
        items.append({"kind": "festival", "key": f.get("key"), "name": f["ta"] or f["en"],
                      "note": (n or {}).get("note", "")})
    seen = {i["key"] for i in items if i.get("key")}
    for k in sp:
        n = note_for("thithi_and_special", k)
        if n and k not in seen:
            items.append({"kind": "special", "key": k, **n})
    for h in cal.get("holidays", {}).get(iso, []):
        if not any(h["ta"] == i["name"] for i in items):
            items.append({"kind": "holiday", "key": None, "name": h["ta"] or h["en"], "note": "அரசு விடுமுறை"})
    wk = note_for("weekday", str((d.weekday() + 1) % 7))
    return {
        "date": iso,
        "weekday_ta": WEEKDAY_TA[d.weekday()],
        "tamil_month": tm, "tamil_day": td,
        "tamil_date": f"{tm} {td}" if tm else "",
        "items": items,
        "weekday_note": wk,
    }


def notify_line(info):
    names = [i["name"] for i in info["items"] if i["kind"] != "holiday"]
    if names:
        first = next(i for i in info["items"] if i["kind"] != "holiday")
        note = (first.get("note") or "").split(".")[0]
        return f"இன்று {', '.join(names[:2])}. {note}".strip()
    return "காலை வணக்கம்! இன்றைய படம் தயார்."


def make_card(item, info, special_line, path):
    photo = images.download(item)
    day_line = info["weekday_ta"] + (f"  |  {info['tamil_date']}" if info["tamil_date"] else "")
    im = card.render(photo, day_line=day_line, special_line=special_line,
                     credit=card.credit_line(item))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=86, optimize=True, progressive=True)


def main():
    day = today_ist()
    out_data, out_cards = OUT / "data", OUT / "cards"
    cal = load_json(out_data / "calendar.json", {})
    try:
        parsed = tdc.fetch_today()
        if parsed["heading_date"] and parsed["heading_date"] != day.isoformat():
            print(f"warning: site shows {parsed['heading_date']}, expected {day}", file=sys.stderr)
            day = dt.date.fromisoformat(parsed["heading_date"])
        cal = merge_calendar(cal, parsed, day)
        cal["source_ok"] = True
    except Exception as e:  # keep yesterday's data; the app still works
        print(f"calendar fetch failed: {e}", file=sys.stderr)
        cal["source_ok"] = False
    cal["updated"] = day.isoformat()
    save_json(out_data / "calendar.json", cal)

    info = day_info(cal, day)
    info["sheet"] = cal.get("sheets", {}).get(day.isoformat(), {})
    tomorrow = day_info(cal, day + dt.timedelta(days=1))

    # month grid data: this month and next
    month = {}
    first = day.replace(day=1)
    for k in range(0, 62):
        d = first + dt.timedelta(days=k)
        if d.month not in (first.month, (first.month % 12) + 1):
            continue
        di = day_info(cal, d)
        month[d.isoformat()] = {"items": [{"name": i["name"], "kind": i["kind"], "note": i.get("note", "")}
                                          for i in di["items"]], "tamil_date": di["tamil_date"]}
    save_json(out_data / "month.json", {"updated": day.isoformat(), "days": month})

    notify = {}
    for k in range(0, 60):
        d = day + dt.timedelta(days=k)
        notify[d.isoformat()] = notify_line(day_info(cal, d))
    save_json(out_data / "notify.json", notify)

    # image of the day + one alternative per other category
    used = load_json(out_data / "used_images.json", {})
    extra = load_json(out_data / "image_extra.json", {})
    keys = {"festival": [i["key"] for i in info["items"] if i["kind"] == "festival" and i.get("key")],
            "special": [i["key"] for i in info["items"] if i["kind"] == "special"]}
    tag, reason = images.choose_tag(day, keys)
    special_line = "  |  ".join(i["name"] for i in info["items"][:2])
    cards = []
    main_item = images.choose_image(tag, day, used, extra)
    make_card(main_item, info, special_line, out_cards / f"{day.isoformat()}.jpg")
    used[main_item["title"]] = day.isoformat()
    cards.append({"file": f"cards/{day.isoformat()}.jpg", "tag": tag, "reason": reason,
                  "title": main_item["title"], "page": main_item.get("page")})
    main_cat = main_item["category"]
    for cat in ALT_CATEGORIES:
        if cat == main_cat:
            continue
        alt_tag = cat
        if cat == "god":
            alt_tag = images.GOD_ROUND[(day.toordinal() + 3) % len(images.GOD_ROUND)]
        try:
            it = images.choose_image(alt_tag, day, used, extra)
            fn = f"cards/{day.isoformat()}_{cat}.jpg"
            make_card(it, info, special_line, OUT / fn)
            used[it["title"]] = day.isoformat()
            cards.append({"file": fn, "tag": alt_tag, "reason": None, "title": it["title"], "page": it.get("page")})
        except Exception as e:
            print(f"alt card {cat} failed: {e}", file=sys.stderr)
    save_json(out_data / "used_images.json", used)

    # prune old cards
    keep = {(day - dt.timedelta(days=k)).isoformat() for k in range(KEEP_CARDS)}
    for f in out_cards.glob("*.jpg"):
        if f.name[:10] not in keep:
            f.unlink()

    today = {"date": day.isoformat(), **info, "tomorrow": tomorrow, "cards": cards,
             "notify_line": notify_line(info), "source_ok": cal.get("source_ok", False)}
    save_json(out_data / "today.json", today)
    print(f"{day}: tag={tag} reason={reason} items={[i['name'] for i in info['items']]}")


if __name__ == "__main__":
    main()
