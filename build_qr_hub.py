#!/usr/bin/env python3
"""Generate qr-codes.html — QR hub page for the Lee Brower Storefront.

Reads ~/workspace/qr-codes/index.csv (the decode-verified QR master list)
and renders a standalone page reusing the storefront's own CSS from
build_store.py, so the look matches index.html exactly. Standalone on
purpose: build_store.py regenerates index.html from products.csv, so a
hand-added link there would be wiped on the next build.
"""
import csv, html, sys
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_store  # noqa: E402  (reuse the storefront CSS verbatim)

CSV_PATH = Path("/home/hatch/workspace/qr-codes/index.csv")
SITE_BASE = "https://wadebrower792.github.io/lee-brower-storefront"

CAT_ORDER = ["Contractor Tools", "Apps & Software", "Prompt Packs",
             "Courses & Film", "Books & Faith", "Games", "Merch", "Other"]

def esc(s):
    return html.escape(s, quote=True)

rows = list(csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8")))
storefront = [r for r in rows if r["category"] == "Storefront"]
products = [r for r in rows if r["category"] != "Storefront"]
assert len(rows) == 86 and len(storefront) == 2 and len(products) == 84, \
    f"unexpected counts: {len(rows)} rows, {len(storefront)} storefront, {len(products)} products"

by_cat = OrderedDict()
for c in CAT_ORDER:
    got = [r for r in products if r["category"] == c]
    if got:
        by_cat[c] = got
for r in products:  # any category outside the known order, keep it
    if r["category"] not in by_cat:
        by_cat.setdefault(r["category"], []).append(r)

def store_card(r, big=False):
    label = ("Gumroad store" if r["slug"] == "storefront-store"
             else "GitHub Pages storefront")
    cls = "qr-store" if big else "qr-card"
    return (f'<article class="{cls}">'
            f'<a href="{esc(r["gumroad_url"])}">'
            f'<img src="qr/{esc(r["qr_file"])}" alt="QR code for {esc(r["product_name"])}" '
            f'loading="lazy" decoding="async"></a>'
            f'<h3>{esc(r["product_name"])}</h3>'
            f'<p class="qr-label">{esc(label)}</p>'
            f'<p class="qr-link"><a href="{esc(r["gumroad_url"])}">'
            f'Scan to open the store</a></p></article>')

def prod_card(r):
    price = esc(r["price"])
    return (f'<article class="qr-card">'
            f'<a href="{esc(r["gumroad_url"])}">'
            f'<img src="qr/{esc(r["qr_file"])}" alt="QR code for {esc(r["product_name"])}" '
            f'loading="lazy" decoding="async"></a>'
            f'<h3>{esc(r["product_name"])}</h3>'
            f'<p class="qr-price">{price}</p>'
            f'<p class="qr-link"><a href="{esc(r["gumroad_url"])}">Buy on Gumroad</a></p>'
            f'</article>')

store_html = "".join(store_card(r, big=True) for r in storefront)
sections = []
for cat, items in by_cat.items():
    cards = "".join(prod_card(r) for r in items)
    sections.append(
        f'<section class="shelf-sec"><div class="sec-head">'
        f'<h2>{esc(cat)}</h2><span class="sec-count">{len(items)}</span>'
        f'<span class="sec-rule"></span></div>'
        f'<div class="qr-grid">{cards}</div></section>')
sections_html = "\n".join(sections)

QR_CSS = """
.qr-wrap{max-width:1280px;margin:0 auto;padding:0 1.25rem 1rem}
.qr-intro{max-width:760px;margin:0 auto 2rem;text-align:center;color:#d7dce6}
.qr-intro p{margin:.7rem 0}
.qr-store-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,420px));gap:1.5rem;justify-content:center;margin-bottom:1rem}
.qr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1.1rem}
.qr-store,.qr-card{background:linear-gradient(180deg,#171d29,#12151d);border:1px solid var(--line);border-radius:16px;overflow:hidden;text-align:center;padding:1.2rem 1rem 1.3rem}
.qr-store{border-color:rgba(212,169,78,.65)}
.qr-store img{width:280px;height:280px;max-width:100%;margin:0 auto;background:#fff;border-radius:10px;padding:10px}
.qr-card img{width:180px;height:180px;max-width:100%;margin:0 auto;background:#fff;border-radius:8px;padding:8px}
.qr-store h3,.qr-card h3{font-size:1rem;line-height:1.35;margin:.9rem 0 .3rem;font-weight:700}
.qr-card h3{font-size:.92rem}
.qr-label{color:var(--gold2);font-size:.9rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.qr-price{color:var(--gold);font-weight:800;font-size:1.2rem}
.qr-link{margin-top:.4rem;font-size:.92rem}
.qr-link a{color:var(--gold);text-decoration:none}
.qr-link a:hover{text-decoration:underline}
@media (max-width:700px){.qr-store img{width:240px;height:240px}.qr-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}}
"""

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QR Codes for Every Product — Lee Brower Storefront</title>
<meta name="description" content="Scan a code, land in the store. Every product in the Lee Brower Storefront has its own QR code — point your phone camera at one and it takes you straight to that product on Gumroad.">
<link rel="canonical" href="{SITE_BASE}/qr-codes.html">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Lee Brower Storefront">
<meta property="og:title" content="QR Codes for Every Product — Lee Brower Storefront">
<meta property="og:description" content="Scan a code, land in the store. Every product in the Lee Brower Storefront has its own QR code.">
<meta property="og:url" content="{SITE_BASE}/qr-codes.html">
<script src="https://gumroad.com/js/gumroad.js"></script>
<style>{build_store.CSS}{QR_CSS}</style>
</head>
<body>
<div class="langbar"><a href="./" hreflang="en" aria-current="true">English</a><a href="es/" hreflang="es">Español</a><a href="pt/" hreflang="pt">Português</a><a href="fr/" hreflang="fr">Français</a><a href="de/" hreflang="de">Deutsch</a></div>
<header class="hero">
<img class="hero-bg" src="assets/hero.webp" alt="" fetchpriority="high">
<div class="hero-shade"></div>
<div class="hero-inner">
<img class="mark" src="assets/logo.webp" alt="Lee Brower — hard hat logo" width="184" height="184">
<h1>Scan a Code, <span>Shop the Store</span></h1>
<p class="tagline">Every product in the Lee Brower Storefront has its own QR code. Point your phone camera at one and it takes you straight to that product — no typing, no searching.</p>
<p class="hero-meta">86 QR codes · 2 storefront codes · 84 product codes · All decode-verified</p>
</div>
</header>
<main class="qr-wrap">
<section class="shelf-sec">
<div class="sec-head"><h2>Storefront QR Codes</h2><span class="sec-count">2</span><span class="sec-rule"></span></div>
<div class="qr-intro"><p>These two codes open the whole store. The Gumroad store is where checkout happens; the GitHub Pages storefront is the full catalog you can browse first. Print them, stick them on a flyer, put them on a truck — anywhere a phone can see them.</p></div>
<div class="qr-store-grid">{store_html}</div>
</section>
{sections_html}
<section class="vendor">
<h2>How to use a QR code</h2>
<p>Open your phone's camera and point it at the code. A link pops up at the top of the screen — tap it and you're on that product's page, with the price right there. No app to install, no account needed to look. Checkout runs through Gumroad, same as the store.</p>
<p style="margin-top:.7rem"><a href="./">Back to the Lee Brower Storefront</a> · <a href="blog/qr-codes-for-every-product-2026-11-11.html">Read the announcement</a> · <a href="./terms.html">Terms</a></p>
</section>
</main>
<footer>
<div class="foot-in">
<p>All prices are the live Gumroad prices. Checkout, receipts and file delivery are handled by Gumroad. <a href="./terms.html">House Terms</a> · <a href="./products/merch.html">Physical goods &amp; merch</a> · Local carpentry, handyman and site-work services live on the <a href="https://wadebrower792.github.io/lee-brower-store/">Lee Brower hub</a>.</p>
</div>
</footer>
</body>
</html>
'''

out = ROOT / "qr-codes.html"
out.write_text(page, encoding="utf-8")
print(f"generated qr-codes.html: {len(page.encode('utf-8'))} bytes")
print(f"storefront codes: {len(storefront)}, product codes: {len(products)}, "
      f"categories: {len(by_cat)}")
