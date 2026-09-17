"""Check the Providence site against the brief.

Two kinds of check. The ordinary ones — every page loads, nav is right, each
residence has a unique title and canonical. And the ones that test things the
brief actually specified but which are usually only ever asserted by eye: the
70/20/10 colour budget, measured off the rendered pixels, and the list of
words she asked never to appear.
"""
import os, re, sys, json, glob, collections

# read straight from the build so the test cannot drift from the data
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as _b
FUTURE_DUBAI_FOR_TEST = _b.FUTURE_DUBAI
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("PROV_BASE", "file://" + ROOT)
OUT = os.path.join(ROOT, "shots")
problems, checks = [], 0

PAGES = ["index.html", "residences.html", "residences/vauxhall-residence.html",
         "corporate-stays.html", "about.html", "property-partners.html",
         "contact.html", "book.html", "privacy-policy.html", "cookie-policy.html",
         "terms-and-conditions.html", "booking-terms.html"]

NAV_LABELS = ["Home", "Collection", "Corporate Stays", "About",
              "Property Partners", "Contact"]

# She listed these explicitly as words the copy should not lean on.
BANNED = ["luxury", "luxurious", "opulent", "exclusive", "prestigious", "lavish"]

PALETTE = {"ivory": (0xF6, 0xF1, 0xE8), "espresso": (0x28, 0x23, 0x1F),
           "champagne": (0xB3, 0x9A, 0x70), "taupe": (0xA9, 0x9C, 0x8D),
           "cream": (0xFF, 0xFD, 0xF8)}


def ok(name, cond, got=None):
    global checks
    checks += 1
    if not cond:
        problems.append("%s%s" % (name, "" if got is None else "  (got %r)" % (got,)))



def _lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def classify(px):
    """Which of the brief's three colour groups does this pixel belong to?

    Judged by distance in RGB to the five brand colours, then mapped to the
    group the brief budgets: light (ivory + cream), dark (espresso), accent
    (champagne + taupe). Photographs are excluded by the caller.
    """
    r, g, b = px[:3]
    best, bestd = None, 1e9
    for name, (cr, cg, cb) in PALETTE.items():
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < bestd:
            best, bestd = name, d
    if bestd > 4200:            # not close to any brand colour — photo or midtone
        return None
    return {"ivory": "light", "cream": "light", "espresso": "dark",
            "champagne": "accent", "taupe": "accent"}[best]


with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errs, failed = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("requestfailed", lambda r: failed.append(r.url))
    os.makedirs(OUT, exist_ok=True)

    titles, descs, canons = {}, {}, {}

    for path in PAGES:
        url = "%s/%s" % (BASE, path)
        pg.goto(url, wait_until="load", timeout=30000)
        pg.wait_for_timeout(450)
        depth = path.count("/")

        ok("%s loads with a heading" % path, pg.locator("h1").count() >= 1)
        t = pg.title()
        d = pg.get_attribute('meta[name="description"]', "content") or ""
        c = pg.get_attribute('link[rel="canonical"]', "href") or ""
        titles[path], descs[path], canons[path] = t, d, c
        ok("%s has a title" % path, 20 < len(t) < 75, (len(t), t))
        ok("%s has a meta description" % path, 60 < len(d) < 185, (len(d), d))
        ok("%s has a canonical" % path, c.endswith(path), c)
        ok("%s names the brand in the title" % path,
           "Providence" in t or "Residence" in t or "Vauxhall" in t, t)

        # navigation, identical everywhere
        nav = pg.eval_on_selector_all(".site-head nav a", "e=>e.map(x=>x.textContent.trim())")
        ok("%s nav is the six items" % path, nav == NAV_LABELS, nav)
        ok("%s Book is a button, not a nav link" % path,
           pg.locator("#navBook").count() == 1 and "btn" in (pg.get_attribute("#navBook", "class") or ""))

        # the wordmark: Providence dominant, Premium Suites smaller and spaced
        n_size = float(pg.eval_on_selector(".site-head .brand .n",
                                           "e=>getComputedStyle(e).fontSize").replace("px", ""))
        s_size = float(pg.eval_on_selector(".site-head .brand .s",
                                           "e=>getComputedStyle(e).fontSize").replace("px", ""))
        s_track = pg.eval_on_selector(".site-head .brand .s", "e=>getComputedStyle(e).letterSpacing")
        ok("%s Providence dominates the wordmark" % path, n_size >= s_size * 2.4, (n_size, s_size))
        ok("%s Premium Suites is letter-spaced" % path,
           float(s_track.replace("px", "")) >= 2.5, s_track)
        ok("%s wordmark is typographic, no image" % path,
           pg.eval_on_selector_all(".site-head .brand img, .site-head .brand svg", "e=>e.length") == 0)

        # fonts: editorial serif for headings, clean sans for body
        hf = pg.eval_on_selector("h1", "e=>getComputedStyle(e).fontFamily")
        bf = pg.eval_on_selector("body", "e=>getComputedStyle(e).fontFamily")
        hw = pg.eval_on_selector("h1", "e=>getComputedStyle(e).fontWeight")
        ok("%s headings use the serif" % path, "Cormorant" in hf, hf)
        ok("%s body uses the sans" % path, "Jost" in bf, bf)
        ok("%s headings are not heavy" % path, int(hw) <= 400, hw)

        # copy discipline
        text = pg.inner_text("body").lower()
        hits = [w for w in BANNED if re.search(r"\b%s\b" % w, text)]
        ok("%s avoids the words she asked us not to use" % path, not hits, hits)

        # statutory disclosure, on every page
        foot = pg.inner_text("footer")
        ok("%s footer names the trading brand and the company" % path,
           "Providence Premium Suites" in foot and "Providence Living Group Ltd" in foot)
        ok("%s footer says it is a trading name" % path, "trading name of" in foot, foot[:120])
        ok("%s footer says registered in England and Wales" % path,
           "registered in England and Wales" in foot)
        ok("%s footer shows the registered office she supplied" % path,
           "5 New Providence Wharf, London E14 9PF" in foot, foot[-200:])
        ok("%s footer shows the telephone she supplied" % path,
           "07455 125635" in foot, foot[-200:])
        # She asked that visitors never see unfinished wording. Anything not
        # yet supplied is omitted entirely rather than shown as a gap.
        page_text = pg.inner_text("body")
        for junk in ("to be supplied", "To be supplied", "Photography to come",
                     "PHOTOGRAPHY TO COME", "TBC", "Lorem", "placeholder imagery"):
            ok("%s shows no unfinished wording (%r)" % (path, junk), junk not in page_text)
        ok("%s never invents a company number" % path,
           not re.search(r"[Cc]ompany number\s*\d", page_text))

        # nothing may scroll sideways, at either size
        for w, h, tag in ((1280, 900, "desktop"), (390, 800, "phone")):
            pg.set_viewport_size({"width": w, "height": h})
            pg.wait_for_timeout(260)
            over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            ok("%s no sideways scroll at %s" % (path, tag), over <= 2, over)
        pg.set_viewport_size({"width": 1280, "height": 900})
        pg.wait_for_timeout(200)

    ok("no javascript errors anywhere", not errs, errs)
    ok("no asset failed to load", not [u for u in failed if not u.startswith("https://fonts")], failed)

    # --- every page must be separately indexable ---
    ok("every page has a distinct title", len(set(titles.values())) == len(titles),
       [t for t, n in collections.Counter(titles.values()).items() if n > 1])
    ok("every page has a distinct description", len(set(descs.values())) == len(descs),
       [d for d, n in collections.Counter(descs.values()).items() if n > 1])
    ok("every canonical is distinct", len(set(canons.values())) == len(canons))
    ok("the residence has its own URL, not a fragment",
       "residences/vauxhall-residence.html" in canons["residences/vauxhall-residence.html"])
    ok("the residence title carries the location for local search",
       "Vauxhall" in titles["residences/vauxhall-residence.html"] and
       "London" in titles["residences/vauxhall-residence.html"],
       titles["residences/vauxhall-residence.html"])
    ok("corporate page targets corporate accommodation London",
       "Corporate Accommodation London" in titles["corporate-stays.html"],
       titles["corporate-stays.html"])

    # --- structured data ---
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(300)
    ld = json.loads(pg.inner_text('script[type="application/ld+json"]'))
    ok("home carries Organization data", ld.get("@type") == "Organization", ld.get("@type"))
    ok("and names the parent company", ld.get("parentOrganization", {}).get("name") ==
       "Providence Living Group Ltd", ld.get("parentOrganization"))
    pg.goto("%s/residences/vauxhall-residence.html" % BASE, wait_until="load"); pg.wait_for_timeout(300)
    ld2 = json.loads(pg.inner_text('script[type="application/ld+json"]'))
    ok("the residence carries Apartment data", ld2.get("@type") == "Apartment", ld2.get("@type"))
    ok("with its postcode", ld2.get("address", {}).get("postalCode") == "SW8")

    # --- the hero, as briefed ---
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(500)
    # --- the editorial opening, requested 15-Sep ---------------------------
    h1 = pg.inner_text("h1")
    ok("the opening states the proposition", "considered living" in h1.lower(), h1)
    stage = pg.inner_text(".stage")
    ok("it names London, extended stays and private residences",
       all(w in stage for w in ("London", "Extended stays", "Private residences")), stage[:160])
    acts = pg.eval_on_selector_all(".stage .acts a", "e=>e.map(x=>x.textContent.trim().upperCase?0:x.textContent.trim().toUpperCase())")
    ok("the opening has both calls to action",
       acts == ["EXPLORE THE COLLECTION", "ENQUIRE ABOUT A STAY"], acts)
    ok("the opening is a full-bleed photograph", pg.locator(".stage .shot img").count() >= 1)
    words = len(pg.inner_text(".stage .on").split())
    ok("the opening is not cluttered with text", words <= 22, words)

    # her point 4: the display voice must be genuinely oversized, and italic
    fs = float(pg.eval_on_selector(".display", "e=>getComputedStyle(e).fontSize").replace("px", ""))
    ok("the display type is oversized", fs >= 90, fs)
    ok("and italic", pg.eval_on_selector(".display", "e=>getComputedStyle(e).fontStyle") == "italic")
    ok("and set in the serif",
       "Cormorant" in pg.eval_on_selector(".display", "e=>getComputedStyle(e).fontFamily"))

    # her point 5: dark punctuation must actually be present, and not dominate
    ok("there is at least one near-black section",
       pg.eval_on_selector_all(".sec-char", "e=>e.length") >= 1)
    ok("full-bleed photography is used more than once",
       pg.eval_on_selector_all(".bleed-full", "e=>e.length") >= 2)
    ok("asymmetric splits are used",
       pg.eval_on_selector_all(".edit-split", "e=>e.length") >= 2)
    ok("a plate overlaps a larger image", pg.eval_on_selector_all(".plate .over", "e=>e.length") >= 1)

    # her point 16: motion must exist AND must switch itself off
    ok("scroll reveals are present", pg.eval_on_selector_all(".reveal", "e=>e.length") >= 6)
    css = open(os.path.join(ROOT, "assets", "style.css"), encoding="utf-8").read()
    ok("prefers-reduced-motion is respected", "prefers-reduced-motion" in css)
    ok("and it neutralises the reveal, not just the zoom",
       "reduce" in css and ".reveal,.reveal-d1" in css.replace(" ", ""))

    # her point 15: the journey must stay obvious
    ok("a booking action is in the header",
       pg.locator("#navBook").count() == 1 and
       pg.eval_on_selector("#navBook", "e=>getComputedStyle(e).display") != "none")

    # --- the four Providence Standard points ---
    std = pg.eval_on_selector_all(".pillars .nm", "e=>e.map(x=>x.textContent.trim())")
    ok("the Providence Standard is present",
       std == ["Sleep", "Live", "Work", "Service", "Location", "Light & Space"], std)
    ok("it is numbered editorially, not iconified",
       pg.eval_on_selector_all(".pillars .n", "e=>e.map(x=>x.textContent.trim())")[:3] == ["01", "02", "03"])
    ok("and it is set in the italic serif, not in cards",
       pg.eval_on_selector(".pillars .nm", "e=>getComputedStyle(e).fontStyle") == "italic")

    # --- the colour budget, measured rather than claimed -------------------
    # Sample the page away from photographs and count which brand group each
    # pixel belongs to. The brief asks for roughly 70 / 20 / 10.
    pg.set_viewport_size({"width": 1280, "height": 900})
    counts = collections.Counter()
    for path in ["index.html", "residences.html", "about.html", "contact.html",
                 "corporate-stays.html", "property-partners.html"]:
        pg.goto("%s/%s" % (BASE, path), wait_until="load", timeout=30000)
        pg.wait_for_timeout(500)
        # Exclude photographic slots entirely. Hiding only the <img> left the
        # placeholder's taupe fill behind, which counted stand-ins for
        # photographs as brand surface and inflated the accent share.
        # Exclude photographic slots AND the hero. Hiding only the <img> left
        # the placeholder's taupe fill counting as brand surface; leaving the
        # hero in counted a dark photograph as an espresso surface and put the
        # dark share at 36% when the design is nothing like that heavy.
        pg.evaluate("document.querySelectorAll('.shot, .hero, .stage, .pic img, .plate').forEach(function(i){i.style.visibility='hidden'})")
        total_h = pg.evaluate("document.body.scrollHeight")
        for frac in (0.05, 0.3, 0.55, 0.8):
            pg.evaluate("window.scrollTo(0,%d)" % int(total_h * frac))
            pg.wait_for_timeout(220)
            shot = pg.screenshot()
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(shot)).convert("RGB")
            im = im.resize((im.width // 8, im.height // 8))
            for px in im.getdata():
                g = classify(px)
                if g:
                    counts[g] += 1
    tot = sum(counts.values()) or 1
    light = counts["light"] / tot * 100
    dark = counts["dark"] / tot * 100
    accent = counts["accent"] / tot * 100
    print("colour budget measured:  light %.1f%%   dark %.1f%%   accent %.1f%%" % (light, dark, accent))
    ok("ivory and cream dominate (brief: ~70%%)", light >= 62, round(light, 1))
    ok("espresso is present but secondary (brief: ~20%%)", 12 <= dark <= 30, round(dark, 1))
    ok("champagne and taupe are actually used, as an accent (brief: ~10%%)",
       1.0 <= accent <= 16, round(accent, 1))
    ok("the site does not read as gold", accent < light / 3, (round(accent, 1), round(light, 1)))


    # --- every local link and asset must resolve to a real file -------------
    # An "the link exists" assertion only proves the anchor is in the markup.
    # It says nothing about whether the page on the other end was generated.
    here = os.path.dirname(os.path.abspath(__file__))
    html_files = sorted(glob.glob(os.path.join(here, "*.html")) +
                        glob.glob(os.path.join(here, "*", "*.html")))
    ok("the site has its pages and a page per residence",
       len(html_files) >= 12, len(html_files))
    dead = []
    for f in html_files:
        src = open(f, encoding="utf-8").read()
        for ref in re.findall(r'(?:href|src)="([^"]+)"', src):
            if re.match(r'^(https?:|mailto:|tel:|data:|#|javascript:)', ref):
                continue
            target = ref.split("#")[0].split("?")[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(f), target))
            if not os.path.exists(resolved):
                dead.append("%s -> %s" % (os.path.relpath(f, here), ref))
    ok("every local link and asset resolves", not dead, dead[:8])
    # and the residence page the Collection sends people to really is there
    ok("the residence detail page exists",
       os.path.exists(os.path.join(here, "residences", "vauxhall-residence.html")))

    # --- hero legibility, measured against the photograph behind it ---------
    # Cream type over a photograph is the single most likely place for this
    # design to become unreadable, and the average is no guide: the first
    # version averaged a comfortable 4.86:1 while 41% of the headline's
    # backdrop sat below 4.5:1 where a bright window showed through.
    import io as _io
    from PIL import Image as _Image
    for w, h, tag in ((1280, 900, "desktop"), (390, 800, "phone")):
        pg.set_viewport_size({"width": w, "height": h})
        pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(700)
        for sel, label, big in ((".stage .display", "opening headline", True),
                                (".stage .idx", "opening eyebrow", False)):
            box = pg.eval_on_selector(sel, "e=>{const r=e.getBoundingClientRect();"
                                            "return {x:r.x,y:r.y,w:r.width,h:r.height}}")
            pg.eval_on_selector(".stage .on", "e=>e.style.visibility='hidden'")
            pg.wait_for_timeout(180)
            im = _Image.open(_io.BytesIO(pg.screenshot())).convert("RGB")
            crop = im.crop((int(box["x"]), int(box["y"]),
                            int(box["x"] + max(1, box["w"])), int(box["y"] + max(1, box["h"]))))
            px = list(crop.getdata())
            rs = sorted(contrast((0xFF, 0xFD, 0xF8), q) for q in px)
            pg.eval_on_selector(".stage .on", "e=>e.style.visibility='visible'")
            pg.wait_for_timeout(120)
            floor = 3.0 if big else 4.5          # large-text threshold
            p1 = rs[len(rs) // 100]              # 1st percentile
            # A single worst pixel is antialiasing noise at a glyph edge or one
            # specular highlight. The 1st percentile is the honest "worst
            # realistic" backdrop, and the share below threshold is what a
            # reader actually experiences.
            ok("%s legible on %s (1st percentile)" % (label, tag), p1 >= floor, round(p1, 2))
            below = 100.0 * sum(1 for r in rs if r < 4.5) / len(rs)
            ok("%s: almost none of the backdrop is thin on %s" % (label, tag),
               below <= 0.5, round(below, 2))
            ok("%s: no part of the backdrop is catastrophic on %s" % (label, tag),
               rs[0] >= 1.6, round(rs[0], 2))
    pg.set_viewport_size({"width": 1280, "height": 900})


    # --- the details she supplied, and the one she has not -----------------
    pg.goto("%s/contact.html" % BASE, wait_until="load"); pg.wait_for_timeout(400)
    ctext = pg.inner_text("main")
    ok("contact page carries the telephone", "07455 125635" in ctext, ctext[:300])
    ok("contact page carries the address", "5 New Providence Wharf" in ctext)
    ok("the telephone is tappable on a phone",
       pg.eval_on_selector_all('a[href^="tel:"]', "e=>e.length") >= 1)
    import subprocess as _sp
    blockers = _sp.run(["python3", "-c",
        "import sys; sys.path.insert(0,%r); import build; print(chr(10).join(build.launch_blockers()))" % ROOT],
        capture_output=True, text=True).stdout
    ok("the build still reports the company number as a launch blocker",
       "Company number" in blockers, blockers)

    # --- the Collection page, in its editorial form ------------------------
    pg.goto("%s/residences.html" % BASE, wait_until="load"); pg.wait_for_timeout(900)
    page_text = pg.inner_text("main")
    low = page_text.lower()

    ok("the page opens with her line",
       "places chosen" in low and "with purpose" in low, page_text[:160])
    ok("the collection is named", "the providence collection" in low)
    nav_labels = pg.eval_on_selector_all(".site-head nav a", "e=>e.map(x=>x.textContent.trim())")
    ok("the nav says Collection", "Collection" in nav_labels, nav_labels)

    # her point 7: Vauxhall presented deliberately, with the location
    ok("Vauxhall leads the page", "vauxhall" in low)
    ok("with its postcode", "sw8" in low)
    ok("labelled as Residence 01, as she asked",
       "residence 01" in low, page_text[:200])
    ok("and named as the first Providence residence",
       "the first providence residence" in low)
    ok("it links through to the residence page",
       pg.eval_on_selector_all("a[href*='vauxhall-residence']", "e=>e.length") >= 1)
    ok("with her editorial line",
       "deserve more than somewhere to sleep" in low)

    # --- expansion: an intention must never read as an inventory -----------
    # Her earlier point, still enforced: "being prepared" across 44 locations
    # states 44 secured properties. They are not.
    for claim in ("being prepared", "36 locations", "44 locations", "8 locations"):
        ok("the page never claims %r" % claim, claim not in low, page_text[:200])
    ok("the expansion is framed as intent",
       "london is only" in low and "the beginning" in low, page_text[:200])
    ok("and says so in her words",
       "actively expanding the providence collection across london" in low)
    ok("intended areas are labelled as a radar, not as stock",
       "on our radar" in low and "neighbourhoods we intend to operate in" in low)
    ok("and it says explicitly they are not held", "not properties we hold" in low)
    ok("nothing is badged Coming Soon while nothing is secured", "coming soon" not in low)

    # grouped, not 36 rows
    groups = pg.eval_on_selector_all(".areagroup h4", "e=>e.map(x=>x.textContent.trim())")
    ok("London is grouped by area", len(groups) == 5, groups)
    for want in ("CENTRAL LONDON", "WEST LONDON", "CITY & EAST", "SOUTH & RIVERSIDE"):
        ok("group %r present" % want, want in [g.upper() for g in groups], groups)
    names = pg.inner_text(".areas")
    for want in ("Mayfair", "Notting Hill", "Shoreditch", "Vauxhall", "King's Cross", "Canary Wharf"):
        ok("area list still contains %s" % want, want in names)
    ok("the areas are not 36 separate rows",
       pg.eval_on_selector_all(".areas li", "e=>e.length") == 0)
    ok("the expansion sits on a near-black section",
       pg.eval_on_selector_all(".sec-char .areas", "e=>e.length") == 1)

    # --- Dubai, its own moment ---------------------------------------------
    dub = pg.inner_text("#dubai")
    ok("Dubai is a separate chapter", "the next chapter" in dub.lower(), dub[:200])
    ok("with a short list of neighbourhoods",
       all(n in dub for n in ("Dubai Marina", "Downtown Dubai", "Palm Jumeirah", "Business Bay")))
    ok("only four, not eight", len(FUTURE_DUBAI_FOR_TEST) == 4)
    ok("Dubai does not carry an invented launch date",
       not re.search(r"\b20\d\d\b", dub), dub[:200])
    ok("Dubai is full-bleed photography",
       pg.eval_on_selector_all("#dubai .shot img", "e=>e.length") == 1)

    # --- the attribute line -------------------------------------------------
    # U+2011 non-breaking hyphen renders as "-" but never breaks
    meta = pg.inner_text(".meta").lower().replace("\u2011", "-")
    for want in ("1 bedroom", "sleeps 2", "thames riverside", "fast wi-fi", "fully equipped"):
        ok("attribute %r" % want, want in meta, meta)
    ok("database wording is gone", "river location" not in pg.inner_text("body").lower())
    ok("the attribute line is not overloaded",
       pg.eval_on_selector_all(".meta span", "e=>e.length") <= 5,
       pg.eval_on_selector_all(".meta span", "e=>e.length"))
    # inner_text cannot see a ::before, so the separators have to be measured.
    # They were scoped to .residence and silently vanished wherever the same
    # attribute line was reused: "1 BEDROOMSLEEPS 2THAMES RIVERSIDE".
    # sweep every page at both widths, so the coverage cannot quietly fall to
    # zero if the attribute line moves or gets renamed
    all_pages = sorted(
        [os.path.basename(p) for p in glob.glob(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "*.html"))] +
        ["residences/" + os.path.basename(p) for p in glob.glob(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "residences", "*.html"))])
    for w in (1440, 390):
        carried = 0
        for path in all_pages:
            pg.set_viewport_size({"width": w, "height": 900})
            pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(300)
            seps = pg.eval_on_selector_all(
                ".meta span + span",
                "e=>e.map(x=>getComputedStyle(x,'::before').content)")
            if not seps:
                continue
            carried += 1
            ok("%s at %dpx separates the attributes" % (path, w),
               all("\u00b7" in s for s in seps), seps)
        ok("the attribute line is actually on the page at %dpx" % w,
           carried >= 2, carried)

    # On a phone the split stacks. Nothing may touch: a button whose bottom
    # edge meets the next photograph reads as a bug, not a composition.
    pg.set_viewport_size({"width": 390, "height": 844})
    tightest = None
    for path in all_pages:
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(300)
        gaps = pg.eval_on_selector_all(".edit-split", """es=>es.map(s=>{
            const k=[...s.children].map(c=>c.getBoundingClientRect())
                     .filter(r=>r.height>0);
            let m=null;
            for(let i=1;i<k.length;i++){const g=k[i].top-k[i-1].bottom;
                if(m===null||g<m)m=g;}
            return m;})""")
        for g in gaps:
            if g is None:
                continue
            if tightest is None or g < tightest:
                tightest = g
    ok("nothing touches inside a stacked split on a phone",
       tightest is not None and tightest >= 20, tightest)

    # An attribute may wrap at a space, but never at a hyphen: "FAST WI-" on
    # one line and "FI" on the next reads as a typo. white-space:nowrap was
    # the wrong cure -- build.py emits the spans with no whitespace between
    # them, so nowrap removed every break opportunity and took the page 214px
    # sideways. The real rule is a data rule: a hyphen inside an attribute has
    # to be U+2011, which renders identically and never breaks.
    for path in ("index.html", "residences.html"):
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(350)
        texts = pg.eval_on_selector_all(".meta span,.facts span",
                                        "es=>es.map(e=>e.textContent)")
        ok("%s has attributes to check" % path, len(texts) >= 3, len(texts))
        breakable = [t for t in texts if "-" in t]
        ok("%s: no attribute can break at a hyphen" % path, not breakable, breakable)
        ok("%s: Wi-Fi is written with a non-breaking hyphen" % path,
           any("Wi\u2011Fi" in t for t in texts), texts)
    pg.set_viewport_size({"width": 1440, "height": 900})

    # Small type on the near-black sections. The computed colour here carries
    # an alpha, so it MUST be composited against the background before the
    # ratio is taken -- reading the rgba triple straight off gave 18:1 for
    # type that actually sits at 6.3:1.
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(700)
    def composited(sel):
        return pg.eval_on_selector(sel, """e=>{
            const cs=getComputedStyle(e);
            const p=(s)=>s.match(/[\d.]+/g).map(Number);
            const fg=p(cs.color);
            let n=e, bg=null;
            while(n && n!==document.documentElement){
                const b=p(getComputedStyle(n).backgroundColor);
                if((b[3]===undefined?1:b[3])>0.99){bg=b.slice(0,3);break}
                n=n.parentElement;
            }
            if(!bg) bg=[255,255,255];
            const a=fg[3]===undefined?1:fg[3];
            return [0,1,2].map(i=>a*fg[i]+(1-a)*bg[i]).concat(bg);
        }""")
    def ratio(fg, bg):
        f=lambda v:(v/255)/12.92 if v/255<=0.03928 else (((v/255)+0.055)/1.055)**2.4
        L=lambda c:.2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])
        a,b2=L(fg),L(bg); hi,lo=max(a,b2),min(a,b2)
        return (hi+.05)/(lo+.05)
    for sel, label in ((".sec-char .meta", "the attribute line on the dark section"),
                       (".sec-char .body-copy", "body copy on the dark section"),
                       (".pillars .desc", "the Providence Standard descriptions")):
        if pg.locator(sel).count() == 0:
            continue
        v = composited(sel)
        r = ratio(v[:3], v[3:])
        ok("%s is legible (%.2f:1)" % (label, r), r >= 4.5, round(r, 2))
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.goto("%s/residences.html" % BASE, wait_until="load"); pg.wait_for_timeout(450)

    # --- the private list ---------------------------------------------------
    ok("the private list is offered", "be first to stay" in low)
    ok("with her wording",
       "early access to new residences, before they are released publicly" in low)
    for fid in ("#pl_name", "#pl_email", "#pl_where", "#pl_from", "#pl_to", "#pl_kind"):
        ok("private list has %s" % fid, pg.locator(fid).count() == 1)
    kinds = pg.eval_on_selector_all("#pl_kind option", "e=>e.map(x=>x.textContent.trim())")
    ok("stay types offered", kinds == ["Short stay", "Extended stay", "Corporate"], kinds)
    ok("preferred location lists every area",
       pg.eval_on_selector_all("#pl_where option", "e=>e.length") >= 40)

    # --- corporate is quietly present --------------------------------------
    ok("a corporate path exists on the collection page",
       "staying longer" in low and "relocations" in low, page_text[-400:])
    ok("and links to the corporate page",
       pg.eval_on_selector_all("a[href='corporate-stays.html']", "e=>e.length") >= 1)

    # --- the editorial language is used here too ---------------------------
    ok("the Collection page uses the display voice",
       pg.eval_on_selector_all(".display", "e=>e.length") >= 4)
    ok("it uses full-bleed photography", pg.eval_on_selector_all(".bleed-full", "e=>e.length") >= 2)
    ok("and asymmetric splits", pg.eval_on_selector_all(".edit-split", "e=>e.length") >= 2)

    # --- The Providence Standard, six principles ---------------------------
    for path in ("index.html", "about.html"):
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(500)
        items = pg.eval_on_selector_all(".pillars .nm, .standard .item h3",
                                        "e=>e.map(x=>x.textContent.trim())")
        ok("%s carries the six Providence standards" % path, len(items) == 6, items)
    pg.goto("%s/residences.html" % BASE, wait_until="load"); pg.wait_for_timeout(500)

    # --- concierge ----------------------------------------------------------
    for path in ("index.html", "residences/vauxhall-residence.html"):
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(500)
        ok("%s has the concierge" % path, pg.locator("#concOpen").count() == 1)
        # Measure the GEOMETRY, not the attribute. `hidden` loses to a class
        # rule that sets display, and it fails silently — the panel was
        # rendering open and covering the hero tagline.
        ok("%s concierge starts closed" % path, pg.eval_on_selector("#concPanel", "e=>e.hidden") is True)
        ok("%s closed concierge occupies no space" % path,
           pg.eval_on_selector("#concPanel", "e=>e.getBoundingClientRect().height") == 0,
           pg.eval_on_selector("#concPanel", "e=>e.getBoundingClientRect().height"))
        ok("%s the closed concierge sits at the bottom, clear of the hero" % path,
           pg.eval_on_selector("#concierge", "e=>e.getBoundingClientRect().top") >
           pg.evaluate("window.innerHeight") * 0.75,
           pg.eval_on_selector("#concierge", "e=>Math.round(e.getBoundingClientRect().top)"))
        pg.click("#concOpen"); pg.wait_for_timeout(450)
        ok("%s concierge opens" % path, pg.eval_on_selector("#concPanel", "e=>e.hidden") is False)
        ok("%s concierge greets" % path, pg.eval_on_selector_all(".conc-msg.them", "e=>e.length") >= 1)
        ok("%s concierge offers quick questions" % path,
           pg.eval_on_selector_all(".conc-chip", "e=>e.length") >= 4)
        # it must answer from the site's own facts
        pg.fill("#concInput", "what are your check in times?")
        pg.eval_on_selector("#concForm", "e=>e.requestSubmit()")
        pg.wait_for_timeout(900)
        txt = pg.inner_text("#concLog")
        ok("%s concierge answers check-in from the real facts" % path,
           "15:00" in txt and "11:00" in txt, txt[-220:])
        # and must hand over rather than invent
        pg.fill("#concInput", "do you take bitcoin and can I bring a horse")
        pg.eval_on_selector("#concForm", "e=>e.requestSubmit()")
        pg.wait_for_timeout(900)
        txt2 = pg.inner_text("#concLog")
        ok("%s concierge hands unknowns to a person rather than inventing" % path,
           "better answered by a person" in txt2, txt2[-220:])
        # the deep page must link correctly out of its subdirectory
        ctas = pg.eval_on_selector_all(".conc-cta", "e=>e.map(x=>x.getAttribute('href'))")
        if path.startswith("residences/"):
            ok("concierge links resolve from a subdirectory",
               all(h.startswith("../") for h in ctas), ctas)
        pg.click("#concClose"); pg.wait_for_timeout(300)
        ok("%s concierge closes" % path, pg.eval_on_selector("#concPanel", "e=>e.hidden") is True)

    pg.set_viewport_size({"width": 390, "height": 800})
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(500)
    pg.click("#concOpen"); pg.wait_for_timeout(450)
    over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    ok("the concierge does not push the phone layout sideways", over <= 2, over)
    pg.set_viewport_size({"width": 1280, "height": 900})

    # --- mobile menu works ---
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(400)
    ok("the desktop nav is hidden on a phone",
       pg.eval_on_selector(".site-head nav", "e=>getComputedStyle(e).display") == "none")
    ok("the menu button is shown",
       pg.eval_on_selector("#burger", "e=>getComputedStyle(e).display") != "none")
    ok("the menu starts closed",
       pg.eval_on_selector("#mobnav", "e=>getComputedStyle(e).display") == "none")
    pg.click("#burger"); pg.wait_for_timeout(350)
    ok("tapping opens it",
       pg.eval_on_selector("#mobnav", "e=>getComputedStyle(e).display") != "none")
    ok("and it carries every page plus Book",
       pg.eval_on_selector_all("#mobnav a", "e=>e.length") == len(NAV_LABELS) + 1)
    ok("the Book button stays visible on a phone",
       pg.eval_on_selector("#navBook", "e=>getComputedStyle(e).display") != "none")

    # --- forms are real and say what happens next ---
    pg.set_viewport_size({"width": 1280, "height": 900})
    for path, form in (("book.html", "#bookForm"), ("contact.html", "#contactForm"),
                       ("corporate-stays.html", "#corpForm"),
                       ("property-partners.html", "#partnerForm")):
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(400)
        ok("%s has its form" % path, pg.locator(form).count() == 1)
        pg.eval_on_selector(form + " button[type=submit]", "e=>e.click()")
        pg.wait_for_timeout(350)
        # .caps applies text-transform, and inner_text returns rendered text
        ok("%s says the form is not connected yet" % path,
           "not yet connected" in pg.inner_text(form).lower(), pg.inner_text(form)[-200:])

    # --- links all resolve ---
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(300)
    hrefs = set()
    for path in PAGES:
        pg.goto("%s/%s" % (BASE, path), wait_until="load"); pg.wait_for_timeout(220)
        for h in pg.eval_on_selector_all("a[href]", "e=>e.map(x=>x.getAttribute('href'))"):
            if h.startswith(("http", "#", "tel:", "mailto:")):
                continue
            base_dir = os.path.dirname(os.path.join(ROOT, path))
            hrefs.add(os.path.normpath(os.path.join(base_dir, h)))
    missing = [h for h in hrefs if not os.path.exists(h)]
    ok("every internal link points at a file that exists", not missing, missing)

    # --- sitemap + robots ---
    ok("a sitemap exists", os.path.exists(os.path.join(ROOT, "sitemap.xml")))
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    ok("the sitemap lists every page", all(p in sm for p in PAGES),
       [p for p in PAGES if p not in sm])
    ok("robots points at the sitemap", "Sitemap:" in open(os.path.join(ROOT, "robots.txt")).read())

    # --- screenshots ---
    pg.set_viewport_size({"width": 1280, "height": 900})
    for name in ("index", "residences", "corporate-stays", "about", "property-partners", "book"):
        pg.goto("%s/%s.html" % (BASE, name), wait_until="load"); pg.wait_for_timeout(650)
        pg.mouse.move(2, 2)
        pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(220)
        pg.screenshot(path="%s/%s.png" % (OUT, name))
    pg.goto("%s/residences/vauxhall-residence.html" % BASE, wait_until="load"); pg.wait_for_timeout(650)
    pg.screenshot(path="%s/residence-top.png" % OUT)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight*0.22)"); pg.wait_for_timeout(300)
    pg.screenshot(path="%s/residence-mid.png" % OUT)
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.goto("%s/index.html" % BASE, wait_until="load"); pg.wait_for_timeout(650)
    pg.screenshot(path="%s/phone-home.png" % OUT)
    pg.goto("%s/residences/vauxhall-residence.html" % BASE, wait_until="load"); pg.wait_for_timeout(650)
    pg.screenshot(path="%s/phone-residence.png" % OUT)

    br.close()

print("checks: %d" % checks)
print("PROBLEMS: %s" % ("\n  - " + "\n  - ".join(problems) if problems else "none"))
sys.exit(1 if problems else 0)
