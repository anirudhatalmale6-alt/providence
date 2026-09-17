#!/usr/bin/env python3
"""Build the Providence Premium Suites site.

Every page is plain static HTML with its own URL, title, meta description,
canonical and structured data — the brief asks for each residence to be
separately indexable, which rules out putting everything behind one address.

The head, navigation and footer are generated from one place so that the
statutory disclosure and the company hierarchy cannot end up worded three
different ways on three different pages.

    python3 build.py          writes the site
"""
import json, os, re, html

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://anirudhatalmale6-alt.github.io/providence"

BRAND   = "Providence Premium Suites"
LEGAL   = "Providence Living Group Ltd"
# Not invented. Shaazia has not given these yet and a company number is a
# statutory disclosure — a wrong one is worse than a visible gap.
# Supplied 10-Sep-2026. The company NUMBER is still outstanding — and unlike
# the others it is a statutory website disclosure, so build.py refuses to call
# the site launch-ready until it arrives. See launch_blockers().
COMPANY_NO    = None
REG_OFFICE    = "5 New Providence Wharf, London E14 9PF"
CONTACT_EMAIL = None
CONTACT_PHONE = "07455 125635"
PHONE_LINK    = "+447455125635"

NAV = [
    ("Home",             "index.html"),
    ("Collection",       "residences.html"),
    ("Corporate Stays",  "corporate-stays.html"),
    ("About",            "about.html"),
    ("Property Partners","property-partners.html"),
    ("Contact",          "contact.html"),
]

# --------------------------------------------------------------------------
# The portfolio. One entry here produces a card on Residences, a block on the
# home page and its own indexable page — so adding the second apartment is a
# dozen lines, which is the point.
# --------------------------------------------------------------------------
RESIDENCES = [
    {
        "slug": "vauxhall-residence",
        "name": "Vauxhall Residence",
        "where": "London, SW8",
        "meta": ["1 Bedroom", "Sleeps 2", "Thames Riverside", "Fast Wi‑Fi", "Fully Equipped"],
        "hero": "img/c16.jpg",
        "intro": "A calm one-bedroom residence moments from the river, arranged for "
                 "long evenings and early starts in equal measure.",
        "description": [
            "The Vauxhall Residence sits a short walk from the Albert Embankment, with the "
            "river at one end of the street and the Underground at the other. It was chosen "
            "for its quiet: a corner position, generous glazing and a view that opens up "
            "rather than looks across.",
            "Inside, the apartment is arranged for stays of a few nights or a few months. A "
            "full kitchen, a dining table that seats four, a bedroom dressed in pressed linen "
            "and a separate seating area that works as comfortably for a morning of calls as "
            "for an evening in.",
        ],
        "amenities": [
            "Full kitchen with dishwasher", "Washer and dryer in the apartment",
            "Fast fibre broadband", "Dedicated workspace", "Smart television",
            "Pressed cotton linen", "Nespresso machine", "Iron and board",
            "Hairdryer", "Toiletries by the bath", "Lift access", "Secure entry",
        ],
        "facts": [
            ("Guests",          "Up to 2"),
            ("Bedrooms",        "1 — king bed"),
            ("Bathrooms",       "1 — walk-in shower"),
            ("Living",          "Separate sitting and dining area"),
            ("Minimum stay",    "2 nights · 28 nights for extended rates"),
            ("Check-in",        "From 15:00 — self check-in"),
            ("Check-out",       "By 11:00"),
            ("Wi-Fi",           "Fibre broadband; details in the welcome note"),
            ("Parking",         "On-street by permit, arranged on request"),
        ],
        "transport": [
            ("Vauxhall", "Victoria line, National Rail — 6 minutes on foot"),
            ("Nine Elms", "Northern line — 12 minutes on foot"),
            ("Riverboat", "Uber Boat by Thames Clippers at St George Wharf"),
            ("Heathrow", "Approximately 45 minutes by car"),
        ],
        "nearby": [
            ("The Albert Embankment", "A level walk along the river toward Westminster."),
            ("Battersea Power Station", "Shops, restaurants and the park, 15 minutes on foot."),
            ("Tate Britain", "Across Vauxhall Bridge, ten minutes."),
            ("Borough Market", "Twenty minutes by Underground."),
        ],
        "shots": [
            ("The sitting room", "Wide, natural light, from the doorway"),
            ("The bedroom", "Pressed linen, morning light"),
            ("The kitchen", "Detail — coffee, stone, brass"),
            ("The bathroom", "Walk-in shower, toiletries"),
            ("The view", "River and city, from the window"),
        ],
        "title": "Vauxhall Residence — Serviced Apartment in Vauxhall, London SW8",
        "desc": "A one-bedroom serviced apartment in Vauxhall, London SW8. Thames riverside, "
                "full kitchen, fast broadband and self check-in. Short stays and extended "
                "corporate bookings.",
    },
]


# --------------------------------------------------------------------------
# Locations.
#
# Split deliberately into two lists, because they are two different claims:
#
#   SECURED   a property is actually taken and being prepared for opening.
#             This is a promise. It must never contain a place we merely
#             intend to enter.
#   FUTURE    places Providence intends to operate in. An intention, not an
#             inventory.
#
# "Being prepared" across forty-four locations reads as forty-four secured
# properties. A guest or a landlord who later discovers otherwise has been
# misled by us, and the rest of the site is working hard to earn their trust.
# --------------------------------------------------------------------------

SECURED = []          # nothing yet beyond Vauxhall, which is a live residence

FUTURE_LONDON = [
    ("Central London",
     ["Mayfair", "Soho", "Covent Garden", "Westminster", "Victoria", "Belgravia",
      "West End", "Piccadilly Circus", "Leicester Square", "Charing Cross",
      "Oxford Street", "Holborn", "Bloomsbury", "Fitzrovia", "Marylebone"]),
    ("West London",
     ["Notting Hill", "South Kensington", "Earls Court", "Bayswater",
      "Paddington", "Hyde Park"]),
    ("City & East",
     ["Liverpool Street", "Shoreditch", "Spitalfields", "Clerkenwell",
      "Farringdon", "City of London", "Tower Hill", "Canary Wharf"]),
    ("North",
     ["King's Cross", "Euston"]),
    ("South & Riverside",
     ["Vauxhall", "Waterloo", "London Bridge", "Kennington", "Pimlico"]),
]

# Four, not eight. A short list of intended neighbourhoods reads as considered;
# a long one reads as a search-engine page.
FUTURE_DUBAI = ["Dubai Marina", "Downtown Dubai", "Palm Jumeirah", "Business Bay"]

# The product promise, from her brief. Six principles, applied to every
# residence — this is what makes it a standard rather than a description.
# Her order, from the 01-05 list in the brief, with Light & Space kept from
# the earlier round because it is the one that describes what a room feels like.
STANDARD = [
    ("Sleep",         "Exceptional beds, linen, blackout and quiet."),
    ("Live",          "Proper kitchens and comfortable living spaces."),
    ("Work",          "Reliable high-speed Wi-Fi and space to work properly."),
    ("Service",       "Responsive Providence support throughout the stay."),
    ("Location",      "Residences selected in well-connected, desirable neighbourhoods."),
    ("Light & Space", "Rooms that feel good to spend time in, not just to sleep in."),
]

# One constant. She wants a stronger promise once the operation can keep it —
# changing it is this line, and nothing else.
CONCIERGE_PROMISE = "Usually replies the same day"

# She asked me to explore dropping "Premium Suites" from the customer-facing
# wordmark. It is one constant, so switching is a single edit and the legal
# trading name is unaffected.
BRAND_SUB = "Premium Suites"          # alternative: "Serviced Residences · London"

# --------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=False)


def shot(cls, src=None, alt="", mark=None, what=None, note=None, up=""):
    """A photographic slot.

    Renders the photograph where one exists, and where one does not renders a
    composed frame naming the shot that belongs there. The slot holds its
    aspect ratio either way, so nothing moves when the real photography lands
    — and the empty ones read as the shot list for the photographer.
    """
    if src and os.path.exists(os.path.join(ROOT, src)):
        # `up` matters: residences/ is one directory down, so a bare img/...
        # resolves to residences/img/... and 404s. Caught by check.py, which
        # fails on any request that does not return.
        return ('<div class="shot %s"><img src="%s%s" alt="%s" loading="lazy"></div>'
                % (cls, up, src, esc(alt)))
    bits = ['<div class="pl">']
    bits.append('<div class="mark">%s</div>' % esc(mark or "Providence"))
    if what:
        bits.append('<div class="what">%s</div>' % esc(what))
    # She asked that visitors never see unfinished wording, so the frames no
    # longer carry a "photography to come" stamp. They still name the room,
    # which reads as a caption rather than as a defect — and still tells the
    # photographer what belongs there.
    if note:
        bits.append('<div class="note">%s</div>' % esc(note))
    bits.append('</div>')
    return '<div class="shot placeholder %s" role="img" aria-label="%s">%s</div>' % (
        cls, esc((mark or "") + " — " + (what or "photography to come")), "".join(bits))


def launch_blockers():
    """What is still missing before this site can go live on her domain.

    Printed at every build. The company number is the one that matters: under
    the Companies Act a limited company must show its registered number,
    place of registration and registered office on its website. Omitting it
    is not compliant — but neither is inventing one, and she has asked that
    visitors never see 'to be supplied'. So the text is hidden and the gap is
    reported here instead of on the page.
    """
    out = []
    if not COMPANY_NO:
        out.append("Company number — REQUIRED BY LAW before the site goes live")
    if not CONTACT_EMAIL:
        out.append("Business email address")
    return out


def head(page, title, desc, canonical, og_image=None, jsonld=None, depth=0):
    up = "../" * depth
    ld = ""
    if jsonld:
        ld = '\n<script type="application/ld+json">%s</script>' % json.dumps(jsonld, indent=1)
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(BRAND)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}/{canonical}">
<meta property="og:image" content="{SITE}/{og_image or 'img/c16.jpg'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#F6F1E8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/style.css">{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


def header(active, depth=0):
    up = "../" * depth
    links = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' aria-current="page"' if href == active else "", esc(label))
        for label, href in NAV)
    mob = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' aria-current="page"' if href == active else "", esc(label))
        for label, href in NAV)
    return f"""<header class="site-head">
  <div class="wrap in">
    <a class="brand" href="{up}index.html" aria-label="{esc(BRAND)} — home">
      <span class="n">Providence</span><span class="s">{esc(BRAND_SUB)}</span>
    </a>
    <nav>{links}</nav>
    <a class="btn btn-sm" href="{up}book.html" id="navBook">Book</a>
    <button class="burger" id="burger" aria-label="Menu" aria-expanded="false" aria-controls="mobnav">
      <span></span><span></span><span></span>
    </button>
  </div>
  <div class="mobnav" id="mobnav">{mob}<a class="btn" href="{up}book.html">Book</a></div>
</header>
<main id="main">
"""


def footer(depth=0):
    up = "../" * depth
    # Anything not yet supplied is omitted entirely rather than shown as a gap.
    company_no_clause = (", company number %s" % esc(COMPANY_NO)) if COMPANY_NO else ""
    bits = []
    if CONTACT_PHONE:
        bits.append('Telephone <a href="tel:%s" style="display:inline">%s</a>'
                    % (PHONE_LINK, esc(CONTACT_PHONE)))
    if CONTACT_EMAIL:
        bits.append('Email <a href="mailto:%s" style="display:inline">%s</a>'
                    % (CONTACT_EMAIL, esc(CONTACT_EMAIL)))
    contact_line = " &middot; ".join(bits)
    res = "".join('<a href="%sresidences/%s.html">%s</a>' % (up, r["slug"], esc(r["name"]))
                  for r in RESIDENCES)
    return f"""</main>
<footer class="site-foot on-dark">
  <div class="wrap">
    <div class="cols">
      <div>
        <a class="brand" href="{up}index.html">
          <span class="n">Providence</span><span class="s">{esc(BRAND_SUB)}</span>
        </a>
        <p class="about">Thoughtfully presented serviced residences in London, for short city
        stays and extended corporate visits.</p>
      </div>
      <div>
        <h4>Stay</h4>
        {res}
        <a href="{up}residences.html">The Providence Collection</a>
        <a href="{up}corporate-stays.html">Corporate &amp; extended stays</a>
        <a href="{up}book.html">Book a stay</a>
      </div>
      <div>
        <h4>Providence</h4>
        <a href="{up}about.html">About</a>
        <a href="{up}property-partners.html">Property partners</a>
        <a href="{up}contact.html">Contact</a>
      </div>
      <div>
        <h4>Legal</h4>
        <a href="{up}privacy-policy.html">Privacy policy</a>
        <a href="{up}cookie-policy.html">Cookie policy</a>
        <a href="{up}terms-and-conditions.html">Terms &amp; conditions</a>
        <a href="{up}booking-terms.html">Booking terms</a>
      </div>
    </div>
    <div class="legal">
      <p><b>{esc(BRAND)}</b> is a trading name of <b>{esc(LEGAL)}</b>, a company registered in
      England and Wales{company_no_clause}. Registered office: {esc(REG_OFFICE)}.</p>
      <p style="margin-top:10px">{contact_line}</p>
      <p style="margin-top:10px">&copy; <span id="yr">2026</span> {esc(LEGAL)}. All rights reserved.</p>
    </div>
  </div>
</footer>

<div class="concierge" id="concierge">
  <button class="conc-open" id="concOpen" aria-expanded="false" aria-controls="concPanel">
    <span class="dot"></span><span>Concierge</span>
  </button>
  <div class="conc-panel" id="concPanel" hidden>
    <div class="conc-head">
      <div>
        <div class="conc-t">Providence Concierge</div>
        <div class="conc-s">{esc(CONCIERGE_PROMISE)}</div>
      </div>
      <button class="conc-x" id="concClose" aria-label="Close">&times;</button>
    </div>
    <div class="conc-log" id="concLog" role="log" aria-live="polite"></div>
    <div class="conc-chips" id="concChips"></div>
    <form class="conc-form" id="concForm">
      <input id="concInput" placeholder="Ask about a stay&hellip;" autocomplete="off"
             aria-label="Message the concierge">
      <button type="submit" aria-label="Send">&rarr;</button>
    </form>
  </div>
</div>
<script src="{up}assets/site.js"></script>
</body>
</html>
"""


def page(path, title, desc, body, active, og_image=None, jsonld=None):
    depth = path.count("/")
    out = head(path, title, desc, path, og_image, jsonld, depth) + header(active, depth) + body + footer(depth)
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(out)
    return path


ORG_LD = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": BRAND,
    "legalName": LEGAL,
    "url": SITE + "/",
    "description": "Premium serviced accommodation in London for short and extended stays.",
    "areaServed": "London, United Kingdom",
    "parentOrganization": {"@type": "Corporation", "name": LEGAL},
}


# ==========================================================================
#  PAGES
# ==========================================================================


def secured_section():
    """Places actually taken. Renders nothing while the list is empty, which
    is the honest state — an empty promise is worse than no promise."""
    if not SECURED:
        return ""
    tiles = "".join('<li class="loc"><span class="badge">Coming soon</span>'
                    '<span class="nm">%s</span><span class="cap">%s</span></li>' % (esc(n), esc(c))
                    for n, c in SECURED)
    return ('<div class="comingblock"><div class="comingtop"><h3>Opening soon</h3>'
            '<span class="caps">Secured and in preparation</span></div>'
            '<ul class="locs">%s</ul></div>' % tiles)


def future_london_section():
    """Intended locations, grouped by part of London.

    Thirty-six identical rows read as a search-engine page. Five groups of
    names read as somebody who knows the city.
    """
    groups = "".join(
        '<div class="areagroup"><h4>%s</h4><p class="areanames">%s</p></div>'
        % (esc(area), " &middot; ".join(esc(n) for n in names))
        for area, names in FUTURE_LONDON)
    return '<div class="areas">%s</div>' % groups


def providence_standard_editorial():
    """Her point 9: design this editorially, not as five generic icon cards.

    A numbered row, a very large italic name, a thin rule. The number and the
    serif do the work; there is nothing decorative in it.
    """
    rows = "".join(
        '<div class="row reveal reveal-d%d"><div class="n">%02d</div>'
        '<div class="nm">%s</div><div class="ds">%s</div></div>'
        % (min(i, 3), i + 1, esc(k), esc(v))
        for i, (k, v) in enumerate(STANDARD))
    return '<div class="pillars">%s</div>' % rows


def providence_standard(dark=False):
    items = "".join('<div class="item"><h3>%s</h3><p>%s</p></div>' % (esc(k), esc(v))
                    for k, v in STANDARD)
    return '<div class="standard standard-6">%s</div>' % items


def eyebrow_for(i):
    """Her point: with one residence live, "Residence 01" followed by "the
    collection is growing" advertises how small we are. "The first Providence
    residence" reads as inaugural instead — the same fact, told as intent."""
    return "The first Providence residence" if i == 0 else "Residence %02d" % (i + 1)


def _residence_cards(depth_prefix=""):
    out = ""
    for i, r in enumerate(RESIDENCES):
        out += f"""
      <article class="residence{' flip' if i % 2 else ''}">
        {shot("ar-wide", r["hero"], r["name"] + ", " + r["where"], r["name"], "Sitting room — wide")}
        <div>
          <span class="caps caps-c">{eyebrow_for(i)}</span>
          <h3>{esc(r["name"])}</h3>
          <div class="where">{esc(r["where"])}</div>
          <div class="meta">{"".join("<span>%s</span>" % esc(m) for m in r["meta"])}</div>
          <p>{esc(r["intro"])}</p>
          <a class="btn btn-ghost btn-sm go" href="residences/{r['slug']}.html">View residence</a>
        </div>
      </article>"""
    return out


def build_home():
    standard = providence_standard_editorial()
    r = RESIDENCES[0]
    body = f"""
<!-- ============ the opening: photography at full height ============ -->
<section class="stage stage-tall bleed-full" data-opener style="padding:0;display:grid;align-items:end">
  <div class="shot zoom in"><img src="img/d-tall.jpg" alt="A Providence residence in London"></div>
  <div class="veil"></div>
  <div class="wrap on">
    <div class="reveal in">
      <span class="idx">London &middot; Extended stays &middot; Private residences</span>
      <h1 class="display" style="margin-top:.34em;color:var(--cream)">Residences for<br><em>considered living.</em></h1>
      <div class="acts" style="display:flex;flex-wrap:wrap;gap:14px;margin-top:clamp(28px,4vh,48px)">
        <a class="btn btn-light" href="residences.html">Explore the collection</a>
        <a class="btn btn-outline-light" href="book.html">Enquire about a stay</a>
      </div>
    </div>
  </div>
  <div class="stage-caption">Providence &middot; Vauxhall</div>
</section>

<!-- ============ editorial statement, asymmetric ============ -->
<section>
  <div class="wrap">
    <div class="edit-split">
      <div class="pic reveal zoom">{'<img src="img/d-window.jpg" alt="Morning light in a Providence residence">'}</div>
      <div class="panel reveal reveal-d1">
        <span class="caps">Providence</span>
        <h2 class="display display-sm" style="margin-top:.4em">A refined way to stay in London.</h2>
        <div class="body-copy">
          <p>Providence offers thoughtfully selected serviced accommodation for guests who value
          comfort, quality and effortless living &mdash; from short city stays to extended corporate
          visits.</p>
        </div>
        <a class="btn btn-ghost btn-sm" href="about.html" style="margin-top:28px">About Providence</a>
      </div>
    </div>
  </div>
</section>

<!-- ============ the first residence, given the whole page ============ -->
<section class="sec-char" style="padding-bottom:clamp(80px,10vw,140px)">
  <div class="wrap">
    <span class="idx">Residence 01</span>
    <h2 class="display" style="margin-top:.3em;color:var(--cream)"><em>Vauxhall</em></h2>
    <p class="caps" style="margin-top:20px;color:#FFFDF8A8">London &middot; SW8</p>
  </div>
  <div class="wrap" style="margin-top:clamp(34px,5vw,60px)">
    <div class="plate">
      <div class="under reveal zoom"><img src="img/d-band.jpg" alt="{esc(r['name'])}"></div>
      <div class="over reveal reveal-d2"><img src="img/d-linen.jpg" alt="Pressed linen"></div>
    </div>
  </div>
  <div class="wrap" style="margin-top:clamp(64px,8vw,110px)">
    <div class="edit-split rev" style="align-items:end">
      <div class="panel reveal" style="background:transparent;padding:0;margin:0">
        <p class="lede" style="font-style:italic">A considered London residence by the Thames,
        created for stays that deserve more than somewhere to sleep.</p>
        <div class="meta" style="margin-top:26px;font-size:12px;letter-spacing:.2em;
             text-transform:uppercase;color:#FFFDF88F">
          {"".join("<span>%s</span>" % esc(m) for m in r["meta"])}
        </div>
        <a class="btn btn-light btn-sm" href="residences/{r['slug']}.html" style="margin-top:32px">Discover Residence 01</a>
      </div>
      <div class="pic wide reveal reveal-d1 zoom"><img src="img/d-detail.jpg" alt="Interior detail"></div>
    </div>
  </div>
</section>

<!-- ============ the Providence Standard, set as type ============ -->
<section>
  <div class="wrap">
    <div class="reveal">
      <span class="idx">The Providence Standard</span>
      <h2 class="display display-sm" style="margin-top:.34em;max-width:22ch">
        Everything you need.<br><em>Nothing you don&rsquo;t.</em></h2>
    </div>
    <div style="margin-top:clamp(40px,5vw,72px)">{standard}</div>
  </div>
</section>

<!-- ============ a full-width breath ============ -->
<section class="stage stage-mid bleed-full" style="padding:0;display:grid;align-items:end">
  <div class="shot zoom reveal"><img src="img/d-band2.jpg" alt="A Providence interior"></div>
  <div class="veil"></div>
  <div class="wrap on">
    <h2 class="display display-sm reveal" style="color:var(--cream);max-width:20ch">
      <em>The art of staying well.</em></h2>
  </div>
</section>

<!-- ============ expansion, then the corporate path ============ -->
<section>
  <div class="wrap">
    <div class="edit-split">
      <div class="pic reveal zoom"><img src="img/c02.jpg" alt="A Providence residence"></div>
      <div class="panel cream reveal reveal-d1">
        <span class="caps">The collection</span>
        <h2 class="display display-sm" style="margin-top:.4em">London is only<br><em>the beginning.</em></h2>
        <div class="body-copy">
          <p>We are actively expanding the Providence Collection across London, with Dubai to follow.
          A residence joins the collection only when the building, the light and the location are
          right.</p>
        </div>
        <a class="btn btn-ghost btn-sm" href="residences.html" style="margin-top:28px">Where we are going next</a>
      </div>
    </div>
  </div>
</section>

<section class="sec-cream sec-tight">
  <div class="wrap split">
    <div class="reveal">
      <span class="caps">Staying longer?</span>
      <h2 class="display display-sm" style="margin-top:.4em">For relocations,<br><em>projects and teams.</em></h2>
      <div class="body-copy">
        <p>Providence offers flexible London accommodation designed for longer living &mdash; invoiced
        to the company, with monthly rates and one point of contact throughout.</p>
      </div>
      <a class="btn btn-ghost" href="corporate-stays.html" style="margin-top:30px">Corporate &amp; Extended Stays</a>
    </div>
    <div class="pic reveal reveal-d1" style="aspect-ratio:4/5;overflow:hidden">
      <img src="img/d-detail.jpg" alt="Workspace detail" style="width:100%;height:100%;object-fit:cover">
    </div>
  </div>
</section>
"""
    return page("index.html",
                "Providence Premium Suites — Serviced Apartments in London",
                "Premium serviced accommodation in London. Thoughtfully presented residences for "
                "short city stays and extended corporate visits.",
                body, "index.html", jsonld=ORG_LD)


def build_residences():
    r = RESIDENCES[0]
    secured = secured_section()
    london = future_london_section()
    dubai = " &middot; ".join(esc(n) for n in FUTURE_DUBAI)
    wherepick = "<option>No preference</option>" + "".join(
        "<option>%s</option>" % esc(n)
        for _area, names in FUTURE_LONDON for n in names) + "".join(
        "<option>%s (Dubai)</option>" % esc(n) for n in FUTURE_DUBAI)
    body = f"""
<section class="sec-tight" style="padding-top:clamp(56px,9vw,120px);padding-bottom:clamp(30px,4vw,56px)">
  <div class="wrap">
    <div class="reveal in">
      <span class="idx">The Collection</span>
      <h1 class="display" style="margin-top:.3em;max-width:18ch">Places chosen<br><em>with purpose.</em></h1>
    </div>
  </div>
</section>

<!-- ============ Vauxhall, given the width of the page ============ -->
<section class="stage stage-tall bleed-full" style="padding:0;display:grid;align-items:end">
  <div class="shot zoom reveal"><img src="img/d-band.jpg" alt="{esc(r['name'])}"></div>
  <div class="veil"></div>
  <div class="wrap on">
    <div class="reveal reveal-d1">
      <span class="idx">Residence 01 &mdash; the first Providence residence</span>
      <h2 class="display" style="margin-top:.3em;color:var(--cream)"><em>Vauxhall</em></h2>
      <p class="caps" style="margin-top:18px;color:#FFFDF8AD">{esc(r["where"])}</p>
    </div>
  </div>
  <div class="stage-caption">Providence &middot; Vauxhall, SW8</div>
</section>

<section>
  <div class="wrap">
    <div class="edit-split rev">
      <div class="panel reveal" style="background:transparent;padding:0;margin:0">
        <p class="lede" style="font-style:italic">A considered London residence by the Thames,
        created for stays that deserve more than somewhere to sleep.</p>
        <div class="meta" style="margin-top:26px;font-size:12px;letter-spacing:.2em;
             text-transform:uppercase;color:var(--ink-3)">
          {"".join("<span>%s</span>" % esc(m) for m in r["meta"])}
        </div>
        <a class="btn btn-ghost btn-sm" href="residences/{r['slug']}.html" style="margin-top:32px">Discover Residence 01</a>
      </div>
      <div class="pic wide reveal reveal-d1 zoom"><img src="img/d-window.jpg" alt="Morning light"></div>
    </div>
  </div>
</section>

<!-- ============ expansion: intent, clearly labelled as intent ============ -->
<section class="sec-char">
  <div class="wrap">
    <div class="reveal">
      <span class="idx">The Providence Collection</span>
      <h2 class="display display-sm" style="margin-top:.32em;color:var(--cream);max-width:20ch">
        London is only<br><em>the beginning.</em></h2>
      <p class="lede" style="margin-top:24px;max-width:52ch">We are actively expanding the Providence
      Collection across London, with Dubai to follow.</p>
    </div>
    {secured}
    <div style="margin-top:clamp(42px,6vw,76px)" class="reveal reveal-d1">
      <div class="comingtop"><h3 style="color:var(--cream)">On our radar</h3>
        <span class="caps">Neighbourhoods we intend to operate in</span></div>
      {london}
      <p class="radarnote">These are the areas Providence is looking at, not properties we hold.
      When a residence is secured it appears in the collection above.</p>
    </div>
  </div>
</section>

<!-- ============ Dubai, its own moment ============ -->
<section class="stage stage-mid bleed-full" id="dubai" style="padding:0;display:grid;align-items:end">
  <div class="shot zoom reveal"><img src="img/d-detail.jpg" alt="Architectural detail"></div>
  <div class="veil"></div>
  <div class="wrap on">
    <div class="reveal reveal-d1">
      <span class="idx">The next chapter</span>
      <h2 class="display" style="margin-top:.3em;color:var(--cream)"><em>Dubai.</em></h2>
      <p class="lede" style="margin-top:20px;max-width:46ch;color:#FFFDF8C7">A first Dubai collection
      is planned. We are looking at a small number of neighbourhoods, chosen the same way as London.</p>
      <p class="dubaiareas" style="margin-top:20px;font-size:clamp(17px,1.8vw,21px)">{dubai}</p>
      <a class="btn btn-light btn-sm" href="contact.html" style="margin-top:30px">Discover what&rsquo;s ahead</a>
    </div>
  </div>
</section>

<!-- ============ the private list ============ -->
<section>
  <div class="wrap">
    <div class="edit-split">
      <div class="pic reveal zoom"><img src="img/d-linen.jpg" alt="Pressed linen"></div>
      <div class="panel cream reveal reveal-d1">
        <span class="idx">Be first to stay</span>
        <h2 class="display display-sm" style="margin-top:.34em">Join the<br><em>private list.</em></h2>
        <p class="body-copy" style="margin-top:18px">Early access to new residences, before they are
        released publicly.</p>
        <form id="listForm" style="margin-top:26px">
          <div class="field"><label for="pl_name">Name</label><input id="pl_name" name="name"></div>
          <div class="field"><label for="pl_email">Email</label><input id="pl_email" name="email" type="email"></div>
          <div class="field"><label for="pl_where">Preferred location</label>
            <select id="pl_where" name="where">{wherepick}</select></div>
          <div class="two">
            <div class="field"><label for="pl_from">From</label><input id="pl_from" name="from" type="date"></div>
            <div class="field"><label for="pl_to">To</label><input id="pl_to" name="to" type="date"></div>
          </div>
          <div class="field"><label for="pl_kind">Type of stay</label>
            <select id="pl_kind" name="kind">
              <option>Short stay</option><option>Extended stay</option><option>Corporate</option>
            </select></div>
          <button class="btn btn-full" type="submit" style="margin-top:20px">Join the private list</button>
        </form>
      </div>
    </div>
  </div>
</section>

<section class="sec-cream sec-tight">
  <div class="wrap narrow" style="text-align:center">
    <span class="caps" style="display:inline-block">Staying longer?</span>
    <h2 class="display display-sm reveal" style="margin-top:.34em">For relocations,
      <em>projects and teams.</em></h2>
    <p class="body-copy reveal reveal-d1" style="margin:22px auto 0;max-width:56ch">Providence offers
    flexible London accommodation designed for longer living.</p>
    <a class="btn btn-ghost reveal reveal-d2" href="corporate-stays.html" style="margin-top:30px">Corporate &amp; Extended Stays</a>
  </div>
</section>
"""
    return page("residences.html",
                "The Providence Collection — Serviced Apartments in London",
                "The Providence collection of serviced apartments in London, presented to a single "
                "standard for short stays and extended corporate visits.",
                body, "residences.html")


def build_residence(r):
    gal = shot("", r["hero"], r["name"], r["name"], r["shots"][0][1], up="../")
    for label, what in r["shots"][1:]:
        gal += shot("ar-sq", None, "", label, what)

    facts = "".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in r["facts"])
    amen = "".join("<li>%s</li>" % esc(a) for a in r["amenities"])
    trans = "".join("<tr><th>%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in r["transport"])
    near = "".join("<div style='margin-top:22px'><h3 style='font-size:20px'>%s</h3>"
                   "<p class='mut' style='margin-top:8px;font-size:15px'>%s</p></div>"
                   % (esc(k), esc(v)) for k, v in r["nearby"])
    desc_p = "".join("<p>%s</p>" % esc(p) for p in r["description"])

    ld = {
        "@context": "https://schema.org",
        "@type": "Apartment",
        "name": r["name"],
        "description": r["intro"],
        "url": "%s/residences/%s.html" % (SITE, r["slug"]),
        "numberOfBedrooms": 1,
        "occupancy": {"@type": "QuantitativeValue", "maxValue": 2},
        "address": {"@type": "PostalAddress", "addressLocality": "London",
                    "postalCode": "SW8", "addressCountry": "GB"},
        "amenityFeature": [{"@type": "LocationFeatureSpecification", "name": a, "value": True}
                           for a in r["amenities"][:8]],
        "containedInPlace": {"@type": "Organization", "name": BRAND},
    }

    body = f"""
<section class="hero hero-sm" style="padding:0">
  <div class="bg">{shot("", r["hero"], r["name"], up="../")}</div>
  <div class="scrim"></div>
  <div class="wrap in">
    <div class="rule"></div>
    <h1>{esc(r["name"])}</h1>
    <p class="tag">{esc(r["where"])}</p>
  </div>
</section>

<section class="sec-tight">
  <div class="wrap"><div class="gallery">{gal}</div></div>
</section>

<section style="padding-top:0">
  <div class="wrap split">
    <div>
      <span class="caps eyebrow">The residence</span>
      <h2>{esc(r["intro"])}</h2>
      <div class="body-copy">{desc_p}</div>

      <h3 style="margin-top:clamp(40px,5vw,64px)">The apartment</h3>
      <table class="facts" style="margin-top:20px">{facts}</table>

      <h3 style="margin-top:clamp(40px,5vw,64px)">Amenities</h3>
      <ul class="amenities">{amen}</ul>

      <h3 style="margin-top:clamp(40px,5vw,64px)">Getting around</h3>
      <table class="facts" style="margin-top:20px">{trans}</table>

      <h3 style="margin-top:clamp(40px,5vw,64px)">The neighbourhood</h3>
      {near}

      <div style="margin-top:clamp(40px,5vw,64px)">
        {shot("ar-wide", None, "", "The location", "Street or river, daylight")}
        <p class="caps" style="margin-top:14px">Vauxhall, London SW8</p>
      </div>

      <h3 style="margin-top:clamp(40px,5vw,64px)">House rules</h3>
      <div class="body-copy">
        <p>No smoking anywhere in the residence. No parties or events. Pets by prior arrangement
        only. Quiet between 22:00 and 08:00, in fairness to the neighbours. Maximum occupancy is
        as stated above and cannot be exceeded.</p>
      </div>

      <h3 style="margin-top:clamp(40px,5vw,64px)">Cancellation</h3>
      <div class="body-copy">
        <p>Full details are set out in our <a href="../booking-terms.html" style="border-bottom:1px solid var(--champagne)">booking terms</a>.
        Cancellation windows and any deposit are confirmed in writing at the time of booking and
        before any payment is taken.</p>
      </div>
    </div>

    <aside class="bookcard">
      <div class="from">Enquire<small>Rates on application</small></div>
      <form id="resForm" style="margin-top:26px">
        <div class="two">
          <div class="field"><label for="ci">Arrive</label><input type="date" id="ci" name="ci"></div>
          <div class="field"><label for="co">Depart</label><input type="date" id="co" name="co"></div>
        </div>
        <div class="field"><label for="gs">Guests</label>
          <select id="gs" name="gs"><option>1 guest</option><option>2 guests</option></select></div>
        <div class="field"><label for="nm">Name</label><input id="nm" name="nm" placeholder="Your name"></div>
        <div class="field"><label for="em">Email</label><input id="em" name="em" type="email" placeholder="you@company.com"></div>
        <button class="btn btn-full" style="margin-top:22px" type="submit">Check availability</button>
      </form>
      <p class="caps" style="margin-top:18px;line-height:1.9">Direct booking with live availability
      and card payment is being prepared. Until then an enquiry reaches us straight away.</p>
      <a class="btn btn-ghost btn-full btn-sm" style="margin-top:16px" href="../contact.html">Contact us</a>
    </aside>
  </div>
</section>
"""
    return page("residences/%s.html" % r["slug"], r["title"], r["desc"], body,
                "residences.html", og_image=r["hero"], jsonld=ld)


def build_corporate():
    body = f"""
<section class="hero hero-sm" style="padding:0">
  <div class="bg">{shot("", None, "", "Corporate", "Workspace — desk, daylight, city")}</div>
  <div class="scrim"></div>
  <div class="wrap in">
    <div class="rule"></div>
    <h1>Corporate &amp; Extended Stays</h1>
    <p class="tag">Professionally managed residences, for as long as you need them.</p>
  </div>
</section>

<section>
  <div class="wrap narrow">
    <p class="lede">Whether you are travelling for business, relocating, working on a London project
    or requiring accommodation for an extended period, Providence Premium Suites provides
    professionally managed residences with the flexibility and comfort of home.</p>
    <div class="body-copy">
      <p>An extended stay with Providence is arranged directly with us rather than through a booking
      platform. That means a single point of contact, an invoice your finance team can work with,
      and terms that suit the length of the project rather than the length of a holiday.</p>
    </div>
  </div>
</section>

<section class="sec-taupe">
  <div class="wrap">
    <span class="caps eyebrow">What is included</span>
    <h2 style="margin-bottom:clamp(38px,5vw,60px)">Arranged for longer stays</h2>
    <div class="standard">
      <div class="item"><h3>Direct billing</h3>
        <p>Invoiced to the company, with purchase order references where required.</p></div>
      <div class="item"><h3>Flexible terms</h3>
        <p>Weekly and monthly rates, with extensions arranged without moving rooms.</p></div>
      <div class="item"><h3>Weekly housekeeping</h3>
        <p>Linen and towels refreshed, with additional service on request.</p></div>
      <div class="item"><h3>One point of contact</h3>
        <p>The same person throughout, reachable without a call centre.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap split">
    <div>
      <span class="caps eyebrow">Enquire</span>
      <h2>Tell us about the stay</h2>
      <div class="body-copy">
        <p>Send us the dates, the number of guests and anything that matters &mdash; proximity to an
        office, a quiet room for calls, parking. We will come back with what we have and what is
        coming.</p>
      </div>
      <div class="note">
        <span class="caps">Longer than a month?</span>
        <p>Extended stays of 28 nights or more are treated differently for rate and for tax, and we
        will set both out in writing before anything is confirmed.</p>
      </div>
    </div>
    <form class="bookcard" id="corpForm">
      <div class="field"><label for="co_company">Company</label><input id="co_company" name="company"></div>
      <div class="field"><label for="co_name">Name</label><input id="co_name" name="name"></div>
      <div class="field"><label for="co_email">Email</label><input id="co_email" name="email" type="email"></div>
      <div class="two">
        <div class="field"><label for="co_from">From</label><input id="co_from" name="from" type="date"></div>
        <div class="field"><label for="co_to">To</label><input id="co_to" name="to" type="date"></div>
      </div>
      <div class="field"><label for="co_msg">Anything we should know</label>
        <textarea id="co_msg" name="message" placeholder="Number of guests, preferred area, parking, anything else."></textarea></div>
      <button class="btn btn-full" type="submit" style="margin-top:20px">Enquire about a corporate stay</button>
    </form>
  </div>
</section>
"""
    return page("corporate-stays.html",
                "Corporate Accommodation London — Extended Stays | Providence",
                "Corporate accommodation and extended stay apartments in London. Direct billing, "
                "flexible monthly terms and professionally managed residences.",
                body, "corporate-stays.html")


def build_about():
    standard = providence_standard()
    body = f"""
<section class="hero hero-sm" style="padding:0">
  <div class="bg">{shot("", "img/c02.jpg", "A Providence residence")}</div>
  <div class="scrim"></div>
  <div class="wrap in">
    <div class="rule"></div>
    <h1>Elevated Living. Exceptional Stays.</h1>
  </div>
</section>

<section>
  <div class="wrap narrow">
    <p class="lede">Providence Premium Suites was created with a simple philosophy: temporary
    accommodation shouldn&rsquo;t feel temporary.</p>
    <div class="body-copy">
      <p>We create thoughtfully presented spaces where guests can settle in, switch off and
      experience London with the comfort and privacy of their own residence.</p>
      <p>Every Providence stay is centred around considered design, quality, cleanliness and
      attentive service.</p>
    </div>
    <div class="note">
      <span class="caps">Company</span>
      <p>Providence Premium Suites is a trading brand of {esc(LEGAL)}.</p>
    </div>
  </div>
</section>

<section class="sec-dark">
  <div class="wrap">
    <span class="caps eyebrow">Our standards</span>
    <h2 style="margin-bottom:clamp(38px,5vw,64px)">The Providence Standard</h2>
    {standard}
  </div>
</section>
"""
    return page("about.html",
                "About — Providence Premium Suites | Serviced Apartments London",
                "Providence Premium Suites creates thoughtfully presented serviced residences in "
                "London. A trading brand of Providence Living Group Ltd.",
                body, "about.html", og_image="img/c02.jpg")


def build_partners():
    body = f"""
<section class="hero hero-sm" style="padding:0">
  <div class="bg">{shot("", None, "", "Partners", "Building exterior — London residential")}</div>
  <div class="scrim"></div>
  <div class="wrap in">
    <div class="rule"></div>
    <h1>Your property. Professionally managed.</h1>
  </div>
</section>

<section>
  <div class="wrap narrow">
    <p class="lede">Providence works with a small number of selected owners to operate their
    property as professionally managed serviced accommodation.</p>
    <div class="body-copy">
      <p>We are not a letting agent and we are not a listing site. We take responsibility for the
      presentation of the property, for the people who stay in it and for its condition when they
      leave &mdash; and we report on all three.</p>
      <p>Arrangements differ by property. Some owners prefer a fixed monthly figure paid whether or
      not the apartment is occupied; others prefer to retain management and have us provide the
      hosting. We are glad to discuss either.</p>
    </div>
  </div>
</section>

<section class="sec-taupe">
  <div class="wrap">
    <span class="caps eyebrow">How your property is looked after</span>
    <h2 style="margin-bottom:clamp(38px,5vw,60px)">Property care</h2>
    <div class="standard">
      <div class="item"><h3>Professional cleaning</h3>
        <p>Every changeover cleaned to a written standard, with linen laundered off site.</p></div>
      <div class="item"><h3>Guest screening</h3>
        <p>Guests are verified before arrival, with house rules agreed in writing.</p></div>
      <div class="item"><h3>Regular inspections</h3>
        <p>The property is inspected on a schedule, not only when something goes wrong.</p></div>
      <div class="item"><h3>Responsive maintenance</h3>
        <p>Small repairs handled promptly; anything larger referred to you with photographs.</p></div>
    </div>
    <div class="standard" style="margin-top:clamp(30px,4vw,54px)">
      <div class="item"><h3>Presentation standards</h3>
        <p>Interiors kept to the standard the property was let in, and refreshed as needed.</p></div>
      <div class="item"><h3>Professional communication</h3>
        <p>One point of contact, and a straight answer when you ask how it is going.</p></div>
      <div class="item"><h3>Compliance</h3>
        <p>Certification, insurance and any permissions confirmed in writing before we begin.</p></div>
      <div class="item"><h3>Reporting</h3>
        <p>A regular written update on occupancy, condition and anything requiring your decision.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap split">
    <div>
      <span class="caps eyebrow">Partner with us</span>
      <h2>Let&rsquo;s talk about your property</h2>
      <div class="body-copy">
        <p>Tell us where the property is and how it is currently let. If it is not right for
        Providence we will say so plainly rather than waste your time.</p>
      </div>
      <div class="note">
        <span class="caps">Before any arrangement begins</span>
        <p>We confirm in writing that the necessary permissions are in place &mdash; the lease, any
        mortgage conditions and the appropriate insurance. It protects you as much as it protects
        us.</p>
      </div>
    </div>
    <form class="bookcard" id="partnerForm">
      <div class="field"><label for="pp_name">Name</label><input id="pp_name" name="name"></div>
      <div class="field"><label for="pp_email">Email</label><input id="pp_email" name="email" type="email"></div>
      <div class="field"><label for="pp_where">Where is the property</label><input id="pp_where" name="where" placeholder="Area and postcode"></div>
      <div class="field"><label for="pp_type">Property</label>
        <select id="pp_type" name="type">
          <option>Studio</option><option>1 bedroom</option><option>2 bedrooms</option>
          <option>3 bedrooms</option><option>Larger</option>
        </select></div>
      <div class="field"><label for="pp_msg">Anything else</label>
        <textarea id="pp_msg" name="message" placeholder="How it is let now, when it is available, anything we should know."></textarea></div>
      <button class="btn btn-full" type="submit" style="margin-top:20px">Partner with Providence</button>
    </form>
  </div>
</section>
"""
    return page("property-partners.html",
                "Property Partners — Serviced Accommodation Management London | Providence",
                "Providence works with selected London property owners to operate their apartments "
                "as professionally managed serviced accommodation.",
                body, "property-partners.html")


def build_contact():
    body = f"""
<section class="sec-tight" style="padding-top:clamp(56px,8vw,110px)">
  <div class="wrap narrow">
    <span class="caps eyebrow">Contact</span>
    <h1 style="font-size:clamp(34px,5vw,60px)">We are glad to hear from you</h1>
    <p class="lede" style="margin-top:26px">Whether you are booking a stay, arranging accommodation
    for a team or asking about your property, a person will read this and reply.</p>
  </div>
</section>

<section style="padding-top:0">
  <div class="wrap split">
    <form class="bookcard" id="contactForm">
      <div class="field"><label for="c_name">Name</label><input id="c_name" name="name"></div>
      <div class="field"><label for="c_email">Email</label><input id="c_email" name="email" type="email"></div>
      <div class="field"><label for="c_about">This is about</label>
        <select id="c_about" name="about">
          <option>A stay</option><option>A corporate or extended stay</option>
          <option>My property</option><option>Something else</option>
        </select></div>
      <div class="field"><label for="c_msg">Message</label><textarea id="c_msg" name="message"></textarea></div>
      <button class="btn btn-full" type="submit" style="margin-top:20px">Send</button>
    </form>
    <div>
      <h3>Providence Premium Suites</h3>
      <table class="facts" style="margin-top:22px">
        <tr><th>Telephone</th><td><a href="tel:{PHONE_LINK}">{esc(CONTACT_PHONE)}</a></td></tr>
        <tr><th>Address</th><td>{esc(REG_OFFICE)}</td></tr>
        <tr><th>Where we operate</th><td>London</td></tr>
        <tr><th>Company</th><td>{esc(LEGAL)}</td></tr>
      </table>
      <div class="note">
        <span class="caps">Response</span>
        <p>Enquiries are answered the same day wherever possible, and always within one working
        day.</p>
      </div>
    </div>
  </div>
</section>
"""
    return page("contact.html",
                "Contact — Providence Premium Suites | Serviced Apartments London",
                "Contact Providence Premium Suites about a stay, a corporate booking or your "
                "property in London.",
                body, "contact.html")


def build_book():
    opts = "".join("<option>%s — %s</option>" % (esc(r["name"]), esc(r["where"])) for r in RESIDENCES)
    body = f"""
<section class="sec-tight" style="padding-top:clamp(56px,8vw,110px)">
  <div class="wrap narrow">
    <span class="caps eyebrow">Book</span>
    <h1 style="font-size:clamp(34px,5vw,60px)">Book your stay</h1>
    <p class="lede" style="margin-top:26px">Tell us when you would like to come and which residence
    you have in mind. We confirm availability and the rate in writing before anything is paid.</p>
  </div>
</section>

<section style="padding-top:0">
  <div class="wrap split">
    <form class="bookcard" id="bookForm">
      <div class="field"><label for="b_res">Residence</label>
        <select id="b_res" name="residence">{opts}<option>No preference</option></select></div>
      <div class="two">
        <div class="field"><label for="b_in">Arrive</label><input id="b_in" name="checkin" type="date"></div>
        <div class="field"><label for="b_out">Depart</label><input id="b_out" name="checkout" type="date"></div>
      </div>
      <div class="two">
        <div class="field"><label for="b_guests">Guests</label>
          <select id="b_guests" name="guests"><option>1</option><option>2</option></select></div>
        <div class="field"><label for="b_code">Promotional code</label><input id="b_code" name="code" placeholder="Optional"></div>
      </div>
      <div class="field"><label for="b_name">Name</label><input id="b_name" name="name"></div>
      <div class="field"><label for="b_email">Email</label><input id="b_email" name="email" type="email"></div>
      <div class="field"><label for="b_msg">Anything we should know</label><textarea id="b_msg" name="message"></textarea></div>
      <button class="btn btn-full" type="submit" style="margin-top:20px">Request your stay</button>
      <p class="caps" style="margin-top:18px;line-height:1.9">No payment is taken on this page.</p>
    </form>
    <div>
      <h3>How booking works today</h3>
      <div class="body-copy">
        <p>Send your dates and we confirm availability, the nightly rate, any minimum stay and the
        cancellation terms in writing. Payment is arranged once you are happy with all of it.</p>
      </div>
      <div class="note">
        <span class="caps">Direct booking is being prepared</span>
        <p>Live availability, a calendar, nightly pricing, minimum-stay rules, promotional codes,
        card payment and automated confirmation are all planned. The site has been built so that a
        booking system can be connected without rebuilding it &mdash; the residence pages, rates and
        terms are already structured for it.</p>
      </div>
      <div style="margin-top:30px">
        {shot("ar-wide", None, "", "Arrival", "Entrance detail — key, door, light")}
      </div>
    </div>
  </div>
</section>
"""
    return page("book.html",
                "Book a Stay — Providence Premium Suites | Serviced Apartments London",
                "Request a stay at a Providence serviced apartment in London. Availability, rates "
                "and cancellation terms confirmed in writing before payment.",
                body, "index.html")


LEGAL_PAGES = [
    ("privacy-policy.html", "Privacy Policy", "How Providence Premium Suites collects and uses personal data.", [
        ("Who we are", "This site is operated by {LEGAL}, trading as Providence Premium Suites. "
                       "For data protection purposes {LEGAL} is the controller."),
        ("What we collect", "When you make an enquiry or a booking we collect your name, contact "
                            "details, the dates and details of your stay, and anything else you choose to tell us. "
                            "If you pay us, payment is processed by a payment provider and we do not store card details."),
        ("Why we use it", "To answer your enquiry, to arrange and manage your stay, to meet our legal "
                          "obligations and, where you have asked us to, to keep you informed."),
        ("How long we keep it", "For as long as needed to provide the stay and to meet our legal and "
                                "accounting obligations, after which it is deleted."),
        ("Who we share it with", "Only those who need it to deliver your stay — for example a cleaning "
                                 "partner or a payment provider — and anyone we are legally required to tell."),
        ("Your rights", "You may ask us for a copy of your data, ask us to correct or delete it, or object "
                        "to how we use it. Contact us using the details in the footer. You may also complain to the "
                        "Information Commissioner's Office."),
    ]),
    ("cookie-policy.html", "Cookie Policy", "The cookies used by the Providence Premium Suites website, and how to manage them in your browser.", [
        ("What we use", "This site uses only what is necessary to make it work. It does not currently set "
                        "advertising or tracking cookies."),
        ("If that changes", "If analytics or marketing cookies are introduced, you will be asked to consent "
                            "before any non-essential cookie is set, and you will be able to change your mind."),
        ("Managing cookies", "Your browser lets you block or delete cookies. Blocking essential cookies may "
                             "stop parts of the site working."),
    ]),
    ("terms-and-conditions.html", "Terms & Conditions", "Terms governing use of the Providence Premium Suites website.", [
        ("These terms", "By using this website you accept these terms. The site is operated by {LEGAL}, "
                        "trading as Providence Premium Suites."),
        ("The information here", "We take care that the site is accurate, but descriptions, images and rates "
                                 "are indicative. Nothing on this site is an offer capable of acceptance; a booking exists "
                                 "only once we confirm it in writing."),
        ("Photography", "Images are indicative. Furnishings, layout and outlook may differ between "
                        "residences, and the residence you book is confirmed to you in writing."),
        ("Intellectual property", "The content and design of this site belong to {LEGAL} unless stated."),
        ("Links", "Where we link to another site we are not responsible for its content."),
        ("Law", "These terms are governed by the law of England and Wales."),
    ]),
    ("booking-terms.html", "Booking Terms", "Booking, payment and cancellation terms for stays with Providence Premium Suites.", [
        ("Making a booking", "A booking is confirmed when we have accepted it in writing and received any "
                             "payment due. Until then dates are not held."),
        ("Rates and what is included", "The rate confirmed to you includes utilities, broadband and the "
                                       "housekeeping stated for your stay. Anything additional is quoted before it is provided."),
        ("Minimum stay", "A minimum stay may apply and is stated before you book."),
        ("Payment", "Payment terms are confirmed in writing at the time of booking. We do not take payment "
                    "through this website at present."),
        ("Cancellation", "Cancellation windows and any charge are confirmed in writing at the time of booking "
                         "and before any payment is taken. Where we have to cancel, you are refunded in full."),
        ("Your responsibilities", "Please treat the residence as you would your own home, observe the house "
                                  "rules, and tell us promptly if something is not right so we can put it right."),
        ("Damage", "You are responsible for damage beyond fair wear and tear. We will always show you "
                   "photographs and an invoice before charging for anything."),
        ("Complaints", "Tell us during your stay wherever possible — most things can be fixed the same day."),
    ]),
]


def build_legal():
    out = []
    for path, title, desc, blocks in LEGAL_PAGES:
        secs = ""
        for h, body_text in blocks:
            secs += ("<h3 style='margin-top:clamp(34px,4vw,52px)'>%s</h3>"
                     "<div class='body-copy' style='margin-top:14px'><p>%s</p></div>"
                     % (esc(h), esc(body_text.replace("{LEGAL}", LEGAL))))
        body = f"""
<section class="sec-tight" style="padding-top:clamp(56px,8vw,104px)">
  <div class="wrap narrow">
    <span class="caps eyebrow">Legal</span>
    <h1 style="font-size:clamp(32px,4.4vw,52px)">{esc(title)}</h1>
    {secs}
    <div class="note" style="margin-top:clamp(40px,5vw,64px)">
      <span class="caps">Still to be completed</span>
      <p>This policy is drafted and ready. Before the site goes live it needs the company number,
      registered office and contact details adding, and a solicitor&rsquo;s eye if you want one.</p>
    </div>
  </div>
</section>
"""
        out.append(page(path, "%s — %s" % (title, BRAND), desc, body, "index.html"))
    return out


def build_extras(pages):
    urls = "".join(
        "<url><loc>%s/%s</loc><changefreq>monthly</changefreq></url>" % (SITE, p) for p in pages)
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % urls)
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE)


def main():
    pages = [build_home(), build_residences()]
    for r in RESIDENCES:
        pages.append(build_residence(r))
    pages += [build_corporate(), build_about(), build_partners(), build_contact(), build_book()]
    pages += build_legal()
    build_extras(pages)
    print("built %d pages" % len(pages))
    for p in pages:
        print("  ", p)


if __name__ == "__main__":
    main()
