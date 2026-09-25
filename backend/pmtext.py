"""Project Madurai HTML -> clean, paged Tamil text. Pure stdlib; shared by the
backend and the Android app (the app converts on-device so the repo stays small)."""
import html
import re

PAGE_CHARS = 4000
NOISE = re.compile(r"\s*(மின்பதிப்பு|உள்ளுறை அட்டவணைக்குத் திரும்ப|Back to (the )?contents?)\s*", re.I)

HEADER_END = re.compile(r"(header page is kept intact|தலைப்புப் பக்கத்தை)", re.I)


def html_to_text(raw):
    s = raw
    m = HEADER_END.search(s)
    if m:
        s = s[m.end():]
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</?(p|div|h\d|tr|center|hr|dd|li|table)[^>]*>", "\n\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = s.replace("\r", "").replace("\u00a0", " ").replace("\ufeff", "")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    paras = [p.strip() for p in text.split("\n\n")]
    tamil = re.compile(r"[\u0b80-\u0bff]")
    junk = re.compile(r"^[-_=*.\s]*$")
    # drop English/boilerplate paragraphs at both ends
    while paras and (not tamil.search(paras[0]) or junk.match(paras[0])):
        paras.pop(0)
    while paras and (not tamil.search(paras[-1]) or junk.match(paras[-1])):
        paras.pop()
    paras = [NOISE.sub(" ", p).strip() for p in paras]
    return "\n\n".join(p for p in paras if p)


def paginate(text):
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    pages, cur = [], ""
    for p in paras:
        if cur and len(cur) + len(p) > PAGE_CHARS:
            pages.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        pages.append(cur)
    return pages
