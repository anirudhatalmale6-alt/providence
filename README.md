# Providence Premium Suites

A static website for Providence Premium Suites, the guest-facing brand of
Providence Living Group Ltd.

    python3 build.py     # writes the pages
    python3 check.py     # 300 assertions against the brief

## Why it is generated rather than hand-written

`build.py` holds the head, the navigation, the footer and the portfolio in one
place. The statutory disclosure and the company hierarchy therefore cannot end
up worded three different ways on three different pages, and adding the second
apartment is a dozen lines in `RESIDENCES` — which produces its block on the
home page, its card on Residences, and its own indexable page with its own
title, description, canonical and structured data.

The output is plain HTML and CSS. It will host anywhere.

## Pages

Home · Residences · a page per residence · Corporate & Extended Stays · About ·
Property Partners · Contact · Book · Privacy · Cookies · Terms · Booking Terms.

## The image system

Every photographic slot is a `.shot` and holds its aspect ratio whether or not
a photograph exists. Where one does not, the slot renders a composed frame
naming the shot that belongs there — so the layout never moves when the real
photography lands, and the empty frames read as the brief for the photographer.

Swapping in real photography is a filename in `build.py`.

## What check.py actually checks

Beyond the ordinary — every page loads, the nav is identical, every title and
canonical is unique, no internal link is broken, nothing scrolls sideways at
390px:

- **The colour budget, measured off the rendered pixels.** The brief asks for
  roughly 70% ivory/cream, 20% espresso, 10% taupe/champagne. Photographic
  areas are excluded, because a dark photograph is not an espresso surface.
- **The words the brief asked us not to use** — luxury, opulent, exclusive,
  prestigious, lavish — must not appear anywhere.
- **Hero legibility, measured against the photograph behind it.** The first
  version averaged a comfortable 4.86:1 while 41% of the headline's backdrop
  sat below 4.5:1 where a bright window showed through. The average is not the
  measure; the worst pixel is.
- **The statutory disclosure** appears on every page, and the missing company
  number is flagged rather than invented.

## Still needed from Shaazia

- Company number and registered office (currently marked *to be supplied*)
- Contact email and telephone
- Real photography — the frames say which shots
- A decision on the booking system, when direct booking is wanted
