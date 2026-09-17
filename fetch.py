"""Placeholder photography for Providence, searched by subject from Wikimedia
Commons and credited. Every candidate gets contact-sheeted before use — the
last time I trusted a placeholder service it returned a dog and a beach."""
import json, time, urllib.parse, urllib.request, os, re

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "Providence-site/1.0 (freelance build; contact via Freelancer.com)"}
TERMS = [
    "luxury hotel suite interior living room",
    "boutique hotel bedroom white linen",
    "modern apartment living room natural light interior",
    "hotel bathroom marble interior",
    "london apartment interior contemporary",
    "hotel room interior design elegant",
    "modern kitchen apartment interior white",
    "london thames view apartment window",
    "hotel suite sitting room interior",
    "bedroom interior neutral tones",
    "dining table interior apartment modern",
    "london south bank river view",
]

def q(params):
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)

picked, seen = [], set()
for term in TERMS:
    if len(picked) >= 22: break
    try:
        d = q({"action":"query","format":"json","generator":"search","gsrsearch":term,
               "gsrnamespace":"6","gsrlimit":"9","prop":"imageinfo",
               "iiprop":"url|extmetadata|size","iiurlwidth":"1600"})
    except Exception as e:
        print("  search failed", term, e); time.sleep(3); continue
    for pid, pg in ((d.get("query") or {}).get("pages") or {}).items():
        if len(picked) >= 22: break
        ii = (pg.get("imageinfo") or [{}])[0]
        url = ii.get("thumburl") or ii.get("url"); title = pg.get("title","")
        if not url or not url.lower().split("?")[0].endswith((".jpg",".jpeg")): continue
        if title in seen: continue
        w, h = ii.get("thumbwidth") or 0, ii.get("thumbheight") or 0
        if not (w and h) or w/h < 1.15 or w/h > 2.1: continue
        md = ii.get("extmetadata") or {}
        g = lambda k: re.sub(r"<[^>]+>","",(md.get(k) or {}).get("value","")).strip()
        seen.add(title)
        picked.append({"title":title,"url":url,"term":term,
                       "author": g("Artist") or "Unknown",
                       "licence": g("LicenseShortName") or "see Commons",
                       "page":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_"))})
    time.sleep(1.4)

print("candidates:", len(picked))
creds = []
for i, p in enumerate(picked, 1):
    dest = "img/c%02d.jpg" % i
    try:
        req = urllib.request.Request(p["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=70) as r, open(dest,"wb") as f:
            f.write(r.read())
        p["file"] = dest; creds.append(p)
        print("  %-14s %-46s %s" % (dest, p["title"][5:50], p["licence"]))
    except Exception as e:
        print("  FAILED", dest, e)
    time.sleep(1.1)
json.dump(creds, open("img/candidates.json","w"), indent=1)
