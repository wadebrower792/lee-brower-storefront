#!/usr/bin/env python3
"""build_store.py — Lee Brower Storefront generator.

Reads products.csv (the store's single source of truth, 16-column schema from
CSV-AUTOMATION-RESEARCH.md) and generates index.html: an Amazon-style store —
header + search, category nav, a Featured row, and one card per `live` row.

Buy buttons are plain anchors to https://wadebrower.gumroad.com/l/<gumroad_slug>;
the official Gumroad overlay script (gumroad.com/js/gumroad.js) is included
exactly ONCE and turns those links into overlay checkouts, with the final
payment step on Gumroad's own page (per Gumroad's help docs).

Workflow: edit products.csv -> python3 build_store.py -> commit -> push.
Adding a product (e.g. Trade Board) = one new CSV row + rerun this script.

SEO is generated here too, never hand-edited: the same run writes sitemap.xml
(every store page + one #p-<handle> anchor per live product) and robots.txt,
and index.html carries per-product JSON-LD Product/Offer data built from the
CSV (real titles, real prices, real Gumroad URLs — nothing invented).

The "Sell in this store" vendor section below is static store furniture (not a
product row). Its rent button is a PLACEHOLDER mailto: the Store Vendor Spot
Gumroad membership does not exist yet (daily creation cap) — no checkout URL
is invented.
"""
import csv, datetime, html, json, re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "products.csv"
OUT_PATH = ROOT / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
ROBOTS_PATH = ROOT / "robots.txt"
GUMROAD_BASE = "https://wadebrower.gumroad.com/l/"
SITE_BASE = "https://wadebrower792.github.io/lee-brower-storefront"
SITE_NAME = "Lee Brower Storefront"
STORE_TITLE = ("Lee Brower Storefront — Contractor AI Tools, Construction "
               "Bid Kit, Software, Courses & Books")
STORE_DESC = ("Contractor AI tools and software built by a working contractor: "
              "ContractorOS AI office software, the Contractor Quote & Bid Kit "
              "for construction bidding, AI prompt playbooks for concrete, "
              "excavation and carpentry, plus courses, books and games. "
              "Live prices and direct Gumroad checkout.")

CATEGORY_ORDER = ["Contractor Tools", "Apps & Software", "Prompt Packs",
                  "Courses & Film", "Books & Faith", "Games", "Merch", "Other"]

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def esc(s: str) -> str:
    return html.escape(s, quote=True)

def anchor_id(r: dict) -> str:
    return "p-" + slugify(r["handle"])

def card_html(r: dict) -> str:
    url = GUMROAD_BASE + r["gumroad_slug"]
    search = " ".join([r["title"], r["category"], r["tags"], r["blurb"]]).lower()
    blurb = f'<p class="blurb">{esc(r["blurb"])}</p>' if r["blurb"] else ""
    compare = (f'<span class="was">${esc(r["compare_at_price"])}</span> '
               if r["compare_at_price"] else "")
    return f'''<article class="card" id="{esc(anchor_id(r))}" data-category="{esc(r["category"])}" data-search="{esc(search)}">
<div class="shot"><img src="{esc(r["image_src"])}" alt="{esc(r["image_alt"])}" loading="lazy"></div>
<span class="tag">{esc(r["category"])}</span>
<h3>{esc(r["title"])}</h3>
{blurb}
<div class="price">{compare}${esc(r["price"])}</div>
<a class="buy" href="{esc(url)}">Buy</a>
</article>'''

def price_num(r: dict) -> float:
    m = re.match(r"[\d.]+", r["price"])
    return float(m.group()) if m else 0.0

def price_str(r: dict) -> str:
    v = price_num(r)
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0").rstrip(".")

def abs_url(path: str) -> str:
    return path if path.startswith("http") else f"{SITE_BASE}/{path.lstrip('/')}"

def product_desc(r: dict) -> str:
    desc = (r["description"] or r["blurb"]).strip()
    if desc:
        return desc
    return (f'{r["title"]} — a {r["category"]} product by Lee Brower, '
            f'working contractor. Sold and delivered through Gumroad.')

def product_jsonld(r: dict, position: int) -> dict:
    anchor = f"{SITE_BASE}/#{anchor_id(r)}"
    offer = {
        "@type": "Offer",
        "url": GUMROAD_BASE + r["gumroad_slug"],
        "priceCurrency": "USD",
        "price": price_str(r),
        "availability": "https://schema.org/InStock",
    }
    if r["price"].strip().endswith("/month"):
        offer["priceSpecification"] = {
            "@type": "UnitPriceSpecification",
            "price": price_str(r),
            "priceCurrency": "USD",
            "unitText": "MON",
            "referenceQuantity": {"@type": "QuantitativeValue",
                                  "value": "1", "unitCode": "MON"},
        }
    product = {
        "@type": "Product",
        "@id": anchor,
        "name": r["title"],
        "description": product_desc(r),
        "category": r["category"],
        "url": anchor,
        "offers": offer,
    }
    if r["image_src"]:
        product["image"] = abs_url(r["image_src"])
    return {"@type": "ListItem", "position": position, "item": product}

def store_jsonld(rows: list) -> str:
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": SITE_BASE + "/#website",
             "name": SITE_NAME, "url": SITE_BASE + "/"},
            {"@type": "Store", "@id": SITE_BASE + "/#store",
             "name": SITE_NAME, "url": SITE_BASE + "/",
             "description": STORE_DESC},
            {"@type": "ItemList", "@id": SITE_BASE + "/#products",
             "name": "Lee Brower catalog",
             "numberOfItems": len(rows),
             "itemListElement": [product_jsonld(r, i + 1)
                                 for i, r in enumerate(rows)]},
        ],
    }
    return json.dumps(graph, indent=1, ensure_ascii=False)

def write_sitemap(rows: list) -> int:
    today = datetime.date.today().isoformat()
    urls = [(SITE_BASE + "/", "weekly", "1.0")]
    for f in sorted((ROOT / "products").glob("*.html")):
        urls.append((f"{SITE_BASE}/products/{f.name}", "weekly", "0.8"))
    urls.append((f"{SITE_BASE}/terms.html", "yearly", "0.5"))
    urls.append((f"{SITE_BASE}/samples/south-alabama/", "monthly", "0.4"))
    for r in rows:
        urls.append((f"{SITE_BASE}/#{anchor_id(r)}", "monthly", "0.6"))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, freq, prio in urls:
        lines += ["  <url>",
                  f"    <loc>{xml_escape(loc)}</loc>",
                  f"    <lastmod>{today}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>",
                  f"    <priority>{prio}</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    SITEMAP_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(urls)

def write_robots() -> None:
    ROBOTS_PATH.write_text(
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {SITE_BASE}/sitemap.xml\n", encoding="utf-8")

def main() -> None:
    rows = [r for r in csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8"))
            if r["status"] == "live"]
    featured = sorted([r for r in rows if r["featured"] == "true"],
                      key=lambda r: -price_num(r))
    by_cat = {}
    for r in rows:
        if r["featured"] != "true":
            by_cat.setdefault(r["category"], []).append(r)
    cats = [c for c in CATEGORY_ORDER if c in by_cat] + \
           [c for c in by_cat if c not in CATEGORY_ORDER]
    for c in cats:
        by_cat[c].sort(key=lambda r: int(r["sort_order"]))

    json_ld = store_jsonld(rows)

    nav = ['<button class="chip on" data-filter="all">All Products</button>',
           '<button class="chip" data-filter="Featured">Featured</button>']
    for c in cats:
        nav.append(f'<button class="chip" data-filter="{esc(c)}">{esc(c)}</button>')

    sections = [f'''<section class="shelf-sec" id="featured">
<h2 class="sec">Featured</h2>
<div class="grid">{''.join(card_html(r) for r in featured)}</div>
</section>''']
    for c in cats:
        sections.append(f'''<section class="shelf-sec" id="cat-{slugify(c)}">
<h2 class="sec">{esc(c)}</h2>
<div class="grid">{''.join(card_html(r) for r in by_cat[c])}</div>
</section>''')

    page = f'''<!DOCTYPE html>
<!-- Generated by build_store.py from products.csv — edit the CSV, not this file. -->
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(STORE_TITLE)}</title>
<meta name="description" content="{esc(STORE_DESC)}">
<link rel="canonical" href="https://wadebrower792.github.io/lee-brower-storefront/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Lee Brower Storefront">
<meta property="og:title" content="{esc(STORE_TITLE)}">
<meta property="og:description" content="{esc(STORE_DESC)}">
<meta property="og:url" content="https://wadebrower792.github.io/lee-brower-storefront/">
<meta property="og:image" content="https://wadebrower792.github.io/lee-brower-storefront/covers/contractoros.webp">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(STORE_TITLE)}">
<meta name="twitter:description" content="{esc(STORE_DESC)}">
<meta name="twitter:image" content="https://wadebrower792.github.io/lee-brower-storefront/covers/contractoros.webp">
<script type="application/ld+json">
{json_ld}
</script>
<script src="https://gumroad.com/js/gumroad.js"></script>
<style>
:root{{--bg:#0e1116;--card:#171c24;--gold:#d4a94e;--txt:#eef1f6;--mut:#9aa3b2}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--txt);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.6;padding:0 0 4rem}}
header{{max-width:1100px;margin:0 auto;padding:3rem 1.25rem 1.4rem;text-align:center}}
header h1{{font-size:2rem;letter-spacing:.5px}}
header h1 span{{color:var(--gold)}}
header p{{color:var(--mut);max-width:640px;margin:1rem auto 0}}
.searchbar{{max-width:560px;margin:1.4rem auto 0}}
.searchbar input{{width:100%;padding:.75rem 1rem;border-radius:8px;border:1px solid #232a36;background:var(--card);color:var(--txt);font-size:1rem}}
.searchbar input:focus{{outline:2px solid var(--gold);outline-offset:1px}}
nav.cats{{max-width:1100px;margin:0.4rem auto 0;padding:0 1.25rem;display:flex;flex-wrap:wrap;gap:.45rem;justify-content:center}}
.chip{{background:#232a36;color:var(--txt);border:1px solid #2c3543;border-radius:999px;padding:.4rem .95rem;font-size:.9rem;cursor:pointer}}
.chip:hover{{border-color:var(--gold)}}
.chip.on{{background:var(--gold);color:#111;font-weight:700;border-color:var(--gold)}}
main{{max-width:1100px;margin:0 auto;padding:0 1.25rem}}
h2.sec{{margin:2.4rem 0 1rem;font-size:1.35rem;border-bottom:2px solid var(--gold);display:inline-block;padding-bottom:.25rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1rem}}
.card{{background:var(--card);border:1px solid #232a36;border-radius:10px;padding:1rem;display:flex;flex-direction:column}}
.card .shot{{display:flex;align-items:center;justify-content:center;height:170px;margin:-1rem -1rem .8rem;padding:.6rem;background:radial-gradient(130% 105% at 50% 0%,#26303f 0%,#131820 72%);border-bottom:1px solid #232a36;border-radius:10px 10px 0 0}}
.card .shot img{{max-width:100%;max-height:100%;object-fit:contain;border-radius:4px}}
.card .tag{{align-self:flex-start;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--gold);border:1px solid var(--gold);border-radius:999px;padding:.08rem .6rem;margin-bottom:.55rem}}
.card h3{{font-size:1rem;line-height:1.35;margin-bottom:.35rem}}
.card .blurb{{color:var(--mut);font-size:.9rem;flex:1}}
.card .price{{color:var(--gold);font-weight:700;font-size:1.15rem;margin:.7rem 0}}
.card .price .was{{color:var(--mut);text-decoration:line-through;font-weight:400;font-size:.95rem}}
.card a.buy{{background:#232a36;color:var(--txt);text-align:center;padding:.65rem;border-radius:7px;text-decoration:none;font-weight:600}}
.card a.buy:hover{{background:var(--gold);color:#111}}
.noresults{{display:none;color:var(--mut);text-align:center;margin:2.5rem 0;font-size:1.05rem}}
.vendor{{max-width:760px;margin:3rem auto 0;padding:1.4rem 1.5rem;background:var(--card);border:1px solid #232a36;border-left:3px solid var(--gold);border-radius:8px}}
.vendor h2{{color:var(--gold);font-size:1.2rem;margin-bottom:.6rem}}
.vendor p,.vendor li{{color:var(--mut);font-size:.95rem}}
.vendor ul{{margin:.6rem 0 .6rem 1.2rem}}
.vendor .vprice{{color:var(--txt);font-size:1.05rem}}
.vendor a.vbtn{{display:inline-block;background:#232a36;color:var(--txt);padding:.7rem 1.2rem;border-radius:7px;text-decoration:none;font-weight:600;margin-top:.8rem}}
.vendor a.vbtn:hover{{background:var(--gold);color:#111}}
footer{{max-width:1100px;margin:3rem auto 0;padding:0 1.25rem;color:var(--mut);font-size:.85rem}}
footer a{{color:var(--gold);text-decoration:none}}
</style>
</head>
<body>
<header>
<h1>Lee Brower <span>Storefront</span></h1>
<p>Practical tools built by a working contractor — software, prompt packs, courses, books and games. Every price below is the live store price; checkout and delivery run through Gumroad.</p>
<div class="searchbar"><input id="search" type="search" placeholder="Search the store…" aria-label="Search products"></div>
</header>
<nav class="cats" aria-label="Categories">{''.join(nav)}</nav>
<main id="store">
{''.join(sections)}
<p class="noresults" id="noresults">Nothing on the shelves matches that — try another word.</p>
<section class="vendor" id="sell">
<h2>Sell your digital products in this store</h2>
<p>Got digital products of your own — a guide, a template pack, a course, a tool — and no storefront to put them on? Rent a spot on my shelves.</p>
<p class="vprice"><strong>Store Vendor Spot — $14.50/month.</strong> The going rate for a basic storefront subscription elsewhere is $29 a month. Mine's half, because you're renting a spot in a working store, not buying a whole platform.</p>
<ul>
<li>Your products shown as proper product cards — your graphics, your titles, your prices — on this store's shelves, in the category they belong in.</li>
<li>Every card links straight to <strong>your own Gumroad product page</strong>. The buyer pays you, at your register. I never touch your money, and I take no cut of your sales — the rent is all I charge.</li>
<li>Your spot stays up while your membership is active. Let it lapse and the cards come down.</li>
</ul>
<p>How it works, plain: you buy the spot, then you send me your product details — title, price, cover picture, a short description, and your Gumroad link for each one. Me and my crew look everything over before it goes up. This is a curated shelf, not an open upload door: digital products only, nothing illegal, nothing pirated, no adult material, no money schemes, and you must own what you're selling. I can refuse or remove any listing — my name's on the store.</p>
<p>One honest note: I'm selling shelf space, not promising traffic or sales. Folks who find this store will see your products right alongside mine. What they buy is up to them.</p>
<a class="vbtn" href="mailto:wadebrower792@gmail.com?subject=Store%20Vendor%20Spot">Vendor spots open soon — email wadebrower792@gmail.com</a>
</section>
</main>
<footer>
<p>All prices are the live Gumroad prices. Checkout, receipts and file delivery are handled by Gumroad. <a href="terms.html">House Terms</a> · <a href="products/merch.html">Physical goods &amp; merch</a> · Local carpentry, handyman and site-work services live on the <a href="https://wadebrower792.github.io/lee-brower-store/">Lee Brower hub</a>.</p>
</footer>
<script>
(function(){{
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('.shelf-sec'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var search = document.getElementById('search');
  var noresults = document.getElementById('noresults');
  var filter = 'all';
  function apply(){{
    var q = search.value.trim().toLowerCase();
    var visible = 0;
    cards.forEach(function(c){{
      var inFeatured = c.closest('#featured') !== null;
      var okCat = (filter === 'all') ? true :
                  (filter === 'Featured') ? inFeatured :
                  (c.getAttribute('data-category') === filter);
      var okQ = !q || c.getAttribute('data-search').indexOf(q) !== -1;
      var show = okCat && okQ;
      c.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    sections.forEach(function(s){{
      var any = Array.prototype.some.call(s.querySelectorAll('.card'), function(c){{ return c.style.display !== 'none'; }});
      s.style.display = any ? '' : 'none';
    }});
    noresults.style.display = visible ? 'none' : 'block';
  }}
  chips.forEach(function(ch){{
    ch.addEventListener('click', function(){{
      chips.forEach(function(x){{ x.classList.remove('on'); }});
      ch.classList.add('on');
      filter = ch.getAttribute('data-filter');
      apply();
    }});
  }});
  search.addEventListener('input', apply);
}})();
</script>
</body>
</html>
'''
    OUT_PATH.write_text(page, encoding="utf-8")
    n_urls = write_sitemap(rows)
    write_robots()
    print(f"generated {OUT_PATH.name}: {len(rows)} live cards "
          f"({len(featured)} featured, {len(cats)} categories)")
    print(f"generated {SITEMAP_PATH.name}: {n_urls} URLs "
          f"(home + {len(rows)} product anchors + store pages)")
    print(f"generated {ROBOTS_PATH.name}")

if __name__ == "__main__":
    main()
