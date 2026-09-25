"""Shared helpers for the Amma app backend jobs."""
import datetime as dt
import json
import os
import pathlib

import requests

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = pathlib.Path(os.environ.get("AMMA_OUT", ROOT.parent / "out"))
UA = "AmmaApp/1.0 (family reading app; github.com/santh0sh/amma-app)"

session = requests.Session()
session.headers["User-Agent"] = UA


def today_ist() -> dt.date:
    override = os.environ.get("AMMA_DATE")
    if override:
        return dt.date.fromisoformat(override)
    return dt.datetime.now(IST).date()


def load_json(path, default):
    path = pathlib.Path(path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp.replace(path)


def get(url, **kw):
    kw.setdefault("timeout", 30)
    r = session.get(url, **kw)
    r.raise_for_status()
    return r
