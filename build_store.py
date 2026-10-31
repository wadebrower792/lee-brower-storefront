#!/usr/bin/env python3
"""build_store.py — Lee Brower Storefront generator (v2, redesign 2026-10-23).

Reads products.csv (the store's single source of truth, 16-column schema)
and generates a visual, responsive, multi-language store:

  index.html          English (canonical)
  es/index.html       Spanish — full chrome + product copy (i18n.py)
  pt|fr|de/index.html UI chrome translated; product copy stays English

Design: black-and-gold premium storefront — hero band with brand art,
sticky category bar, featured shelf, category sections with icon headers,
product cards with cover art (local WebP covers from covers_map.json when
available, else the product's Gumroad image), price + Buy on every card,
search + category filter (JS, with full content present without JS).

Buy buttons are plain anchors to https://wadebrower.gumroad.com/l/<slug>;
the official Gumroad overlay script is included exactly ONCE per page and
turns those links into overlay checkouts.

SEO: sitemap.xml keeps the canonical URL set (home + product pages +
#p-<handle> anchors) and adds hreflang alternates via xhtml:link for the
language variants; robots.txt welcomes all crawlers incl. AI search;
index.html carries per-product JSON-LD Product/Offer data from the CSV
(real titles, real prices, real Gumroad URLs — nothing invented).

Workflow: edit products.csv -> python3 build_store.py -> commit -> push.
"""
import csv, datetime, html, json, re
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape as xml_escape

import i18n

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "products.csv"
COVERS_MAP_PATH = ROOT / "covers_map.json"
SITE_BASE = "https://wadebrower792.github.io/lee-brower-storefront"
GUMROAD_BASE = "https://wadebrower.gumroad.com/l/"
SITE_NAME = "Lee Brower Storefront"
HERO_IMG = "assets/hero.webp"
LOGO_IMG = "assets/logo.webp"

CATEGORY_ORDER = ["Contractor Tools", "Apps & Software", "Prompt Packs",
                  "Courses & Film", "Books & Faith", "Games", "Merch", "Other"]

# Inline SVG icons (24x24, stroke) per English category name.
CATEGORY_ICONS = {
    "Contractor Tools": '<path d="M14.7 6.3a4.5 4.5 0 0 0-6 6L3 18l3 3 5.7-5.7a4.5 4.5 0 0 0 6-6L14 13l-3-3 3.7-3.7z"/>',
    "Apps & Software": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M6 6.5h.01M9 6.5h.01"/>',
    "Prompt Packs": '<path d="M4 17l6-5-6-5M12 19h8"/>',
    "Courses & Film": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 9h18M3 15h18M8 5v14M16 5v14M10.5 10.2l4 1.8-4 1.8z" fill="currentColor" stroke="none"/>',
    "Books & Faith": '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h13"/>',
    "Games": '<path d="M6 9h12a5 5 0 0 1 5 5c0 2.8-2.2 5-5 5-1.7 0-3.2-.8-4.1-2H9.9C9 18.2 7.5 19 6 19c-2.8 0-5-2.2-5-5a5 5 0 0 1 5-5z"/><path d="M7 12v4M5 14h4M16.5 13h.01M18.5 15.5h.01"/>',
    "Merch": '<path d="M8 4L3 8l2.5 3L8 9.5V20h8V9.5L18.5 11 21 8l-5-4a4 4 0 0 1-8 0z"/>',
    "Other": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "Featured": '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/>',
}

COVERS_MAP = {}
if COVERS_MAP_PATH.exists():
    COVERS_MAP = json.loads(COVERS_MAP_PATH.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def anchor_id(r: dict) -> str:
    return "p-" + slugify(r["handle"])


def cover_src(r: dict, lang: str) -> str:
    """Local WebP cover when mapped (relative to the page's folder),
    else the product's Gumroad image URL from the CSV."""
    prefix = "../" if lang != "en" else ""
    local = COVERS_MAP.get(r["handle"])
    if local:
        return prefix + "covers/" + local
    return r["image_src"]


def price_num(r: dict) -> float:
    m = re.match(r"[\d.]+", r["price"])
    return float(m.group()) if m else 0.0


def price_str(r: dict) -> str:
    v = price_num(r)
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0").rstrip(".")


def abs_url(path: str) -> str:
    return path if path.startswith("http") else f"{SITE_BASE}/{path.lstrip('/')}"


def lang_url(lang: str, anchor: str = "") -> str:
    return f"{SITE_BASE}/{i18n.LANG_PATH[lang]}{anchor}"


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
    local = COVERS_MAP.get(r["handle"])
    img = f"covers/{local}" if local else r["image_src"]
    if img:
        product["image"] = abs_url(img)
    return {"@type": "ListItem", "position": position, "item": product}


def store_jsonld(rows: list) -> str:
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": SITE_BASE + "/#website",
             "name": SITE_NAME, "url": SITE_BASE + "/"},
            {"@type": "Store", "@id": SITE_BASE + "/#store",
             "name": SITE_NAME, "url": SITE_BASE + "/",
             "description": i18n.STORE_META["en"]["desc"]},
            {"@type": "ItemList", "@id": SITE_BASE + "/#products",
             "name": "Lee Brower catalog",
             "numberOfItems": len(rows),
             "itemListElement": [product_jsonld(r, i + 1)
                                 for i, r in enumerate(rows)]},
        ],
    }
    return json.dumps(graph, indent=1, ensure_ascii=False)


def hreflang_links(anchor: str = "") -> str:
    out = []
    for L in i18n.LANGS:
        out.append(f'<link rel="alternate" hreflang="{L}" '
                   f'href="{esc(lang_url(L, anchor))}">')
    out.append(f'<link rel="alternate" hreflang="x-default" '
               f'href="{esc(lang_url("en", anchor))}">')
    return "\n".join(out)


def sitemap_alternates(anchor: str = "") -> list:
    lines = []
    for L in i18n.LANGS:
        lines.append(
            f'    <xhtml:link rel="alternate" hreflang="{L}" '
            f'href="{xml_escape(lang_url(L, anchor))}"/>')
    lines.append(
        f'    <xhtml:link rel="alternate" hreflang="x-default" '
        f'href="{xml_escape(lang_url("en", anchor))}"/>')
    return lines


def write_sitemap(rows: list) -> int:
    today = datetime.date.today().isoformat()
    urls = [(SITE_BASE + "/", "weekly", "1.0", "")]
    for f in sorted((ROOT / "products").glob("*.html")):
        urls.append((f"{SITE_BASE}/products/{f.name}", "weekly", "0.8", None))
    for f in sorted((ROOT / "compare").glob("*.html")):
        urls.append((f"{SITE_BASE}/compare/{f.name}", "weekly", "0.8", None))
    urls.append((f"{SITE_BASE}/terms.html", "yearly", "0.5", None))
    for g in GUIDES:
        urls.append((f"{SITE_BASE}/guides/{g['slug']}.html", "monthly", "0.7", None))
    urls.append((f"{SITE_BASE}/blog/", "daily", "0.8", None))
    for b in BLOGS:
        urls.append((f"{SITE_BASE}/blog/{b['slug']}.html", "monthly", "0.7", None))
    urls.append((f"{SITE_BASE}/samples/south-alabama/", "monthly", "0.4", None))
    for r in rows:
        a = f"#{anchor_id(r)}"
        urls.append((f"{SITE_BASE}/{a}", "monthly", "0.6", a))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc, freq, prio, anchor in urls:
        lines += ["  <url>",
                  f"    <loc>{xml_escape(loc)}</loc>"]
        if anchor is not None:
            lines += sitemap_alternates(anchor)
        lines += [f"    <lastmod>{today}</lastmod>",
                  f"    <changefreq>{freq}</changefreq>",
                  f"    <priority>{prio}</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(urls)


def write_robots() -> None:
    (ROOT / "robots.txt").write_text(
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {SITE_BASE}/sitemap.xml\n", encoding="utf-8")


# Field Guides: long-form articles published on the storefront (English
# only). Source markdown lives in guides-src/; the build renders each to
# guides/<slug>.html with the store chrome, a canonical URL, and Article
# JSON-LD. Descriptions below are plain summaries of the article's own
# content — no invented claims, reviews, or sales numbers.
GUIDES = [
    {"slug": "how-to-write-a-construction-bid-that-wins-work",
     "title": "How to Write a Construction Bid That Wins Work",
     "desc": "A working contractor's plain-English guide to bids that hold up: "
             "the site walk, itemized scope, exclusions, knowing your "
             "number, and following up.",
     "date": "2026-10-27"},
    {"slug": "ai-tools-for-contractors-what-actually-saves-time",
     "title": "AI Tools for Contractors: What Actually Saves Time on a Real Job",
     "desc": "Which AI tools actually save a contractor time this week — "
             "drafting, follow-ups, and reading paper — and what not to "
             "trust them with.",
     "date": "2026-10-27"},
]

# Blog: daily posts on popular subjects, verifiable facts only, each
# carrying the store ad block. Source markdown lives in blog-src/; the
# build renders each to blog/<slug>.html plus blog/index.html, with the
# store chrome, a canonical URL, and Article JSON-LD. Descriptions are
# plain summaries of the post's own content — no invented claims.
BLOGS = [
    {"slug": "meta-muse-10-million-setups-checked",
     "title": "10 Million Setups: What Meta's Muse Numbers Actually Say",
     "desc": "Meta's Muse passed 10 million setups in the US and Canada in "
             "about six weeks — what the earnings reporting actually said, "
             "and what it did not prove.",
     "date": "2026-10-30"},
    {"slug": "binance-6-3-billion-hack-what-is-confirmed",
     "title": "Binance Hack: $6.3 Billion Gone, and What Is Actually Confirmed",
     "desc": "Hackers drained about $6.3 billion from Binance on October 29, "
             "2026 — what Binance and the tracing firms actually said, "
             "and what is attribution, not proven fact.",
     "date": "2026-10-30"},
    {"slug": "halloween-pedestrian-safety-data",
     "title": "Halloween Night Is the Riskiest Night for Young Pedestrians. "
             "The Data Says Why.",
     "desc": "Four decades of federal crash data show a 43 percent higher "
             "pedestrian fatality risk on Halloween evening — and the "
             "steepest risk for children aged 4 to 8.",
     "date": "2026-10-30"},
    {"slug": "data-center-boom-construction-october-2026",
     "title": "The Data Center Boom Is Carrying Construction — and Squeezing "
             "Everyone Else",
     "desc": "October 2026 data: data center spending up more than 70 percent "
             "year over year while other private nonresidential spending "
             "fell, and material prices up 11.2 percent.",
     "date": "2026-10-30"},
    {"slug": "clocks-fall-back-november-1-2026",
     "title": "Clocks Fall Back Sunday, November 1: What Actually Changes",
     "desc": "Daylight saving time ends at 2 a.m. local time on November 1, "
             "2026 — the earliest date the law allows — and the "
             "permanent-daylight bill has not passed the Senate.",
     "date": "2026-10-30"},
    {"slug": "spain-train-crash-urda-what-is-confirmed",
     "title": "Spain's Train Crash at Urda: What Is Confirmed, and What Is "
             "Not Yet",
     "desc": "At least 69 dead near Urda, a preliminary speed estimate of "
             "160 to 200 kph, and a corrected 74 figure — what the "
             "investigation has and has not settled.",
     "date": "2026-10-30"},
    {"slug": "midterm-elections-november-3-2026-what-polls-say",
     "title": "Midterm Elections Are Tuesday, November 3: What the Polls "
             "Actually Say",
     "desc": "All 435 House seats, 35 Senate seats, and 36 governorships are "
             "on the ballot Tuesday — and the polling averages point one "
             "way nationally while the Senate stays contested.",
     "date": "2026-10-31"},
    {"slug": "california-king-tides-october-2026-records",
     "title": "California's King Tides Just Set Records. The Next Ones "
             "Could Be Higher.",
     "desc": "San Diego's gauge hit a station record of 8.52 feet on October "
             "27, Huntington Beach declared a local emergency, and the "
             "predicted winter king tides are higher still.",
     "date": "2026-10-31"},
    {"slug": "dockworkers-strike-113-ports-supply-chain",
     "title": "Dockworkers Struck at 113 Ports on Friday. Here's What It "
             "Means for Materials and Deliveries.",
     "desc": "Reuters: 113 ports in 22 countries struck October 30 over arms "
             "shipments and seafarer deaths, while Los Angeles and Long "
             "Beach talks extended to November 5.",
     "date": "2026-10-31"},
]

GUIDE_EXTRA_CSS = """
.guide-wrap{max-width:760px;margin:0 auto;padding:2.2rem 1.25rem 3rem}
.guide-wrap h1{font-size:clamp(1.7rem,4.5vw,2.4rem);line-height:1.2;margin:1rem 0 .4rem}
.guide-wrap h2{color:var(--gold);font-size:1.35rem;margin:2.2rem 0 .4rem}
.guide-wrap p{margin:1rem 0;color:#d7dce6}
.guide-wrap blockquote{border-left:3px solid var(--gold);padding:.5rem 1.1rem;margin:1rem 0;color:var(--mut);font-style:italic}
.guide-wrap hr{border:none;border-top:1px solid var(--line);margin:2rem 0}
.byline{color:var(--gold2);font-size:.95rem}
.backlink{display:inline-block;margin-bottom:.5rem;color:var(--gold);text-decoration:none;font-weight:700}
.backlink:hover{text-decoration:underline}
.guides-sec .guide-list{display:grid;gap:1rem}
a.guide-item{display:block;background:linear-gradient(180deg,#171d29,#12151d);border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:14px;padding:1.1rem 1.3rem;text-decoration:none}
a.guide-item:hover{border-color:rgba(212,169,78,.65)}
a.guide-item strong{display:block;color:var(--txt);font-size:1.08rem;margin-bottom:.25rem}
a.guide-item span{color:var(--mut);font-size:.93rem}
"""


def md_inline(text: str) -> str:
    """Inline markdown (links, bold, italic) on already-escaped text."""
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """Minimal markdown for the guide sources: H1/H2, paragraphs with
    wrapped lines joined, blockquotes, hr. No raw HTML passes through."""
    blocks, para, quote = [], [], []
    def flush_para():
        if para:
            blocks.append("<p>" + md_inline(html.escape(" ".join(para))) + "</p>")
            para.clear()
    def flush_quote():
        if quote:
            blocks.append("<blockquote><p>" +
                          md_inline(html.escape(" ".join(quote))) + "</p></blockquote>")
            quote.clear()
    for raw in md.split("\n"):
        line = raw.strip()
        if not line:
            flush_para(); flush_quote(); continue
        if line.startswith("## "):
            flush_para(); flush_quote()
            blocks.append("<h2>" + md_inline(html.escape(line[3:].strip())) + "</h2>")
        elif line.startswith("# "):
            flush_para(); flush_quote()
            blocks.append("<h1>" + md_inline(html.escape(line[2:].strip())) + "</h1>")
        elif line == "---":
            flush_para(); flush_quote()
            blocks.append("<hr>")
        elif line.startswith("> "):
            flush_para()
            quote.append(line[2:].strip())
        elif line.startswith("By Wade Lee Brower Jr"):
            flush_para(); flush_quote()
            blocks.append('<p class="byline">' + html.escape(line) + "</p>")
        else:
            flush_quote()
            para.append(line)
    flush_para(); flush_quote()
    return "\n".join(blocks)


def guide_page_html(g: dict, body_html: str) -> str:
    url = f"{SITE_BASE}/guides/{g['slug']}.html"
    ld = {"@context": "https://schema.org", "@type": "Article",
          "headline": g["title"], "description": g["desc"],
          "author": {"@type": "Person", "name": "Wade Lee Brower Jr"},
          "datePublished": g["date"], "mainEntityOfPage": url}
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(g["title"])} — Lee Brower Storefront</title>
<meta name="description" content="{esc(g["desc"])}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Lee Brower Storefront">
<meta property="og:title" content="{esc(g["title"])}">
<meta property="og:description" content="{esc(g["desc"])}">
<meta property="og:url" content="{esc(url)}">
<script type="application/ld+json">
{json.dumps(ld, indent=1, ensure_ascii=False)}
</script>
<script src="https://gumroad.com/js/gumroad.js"></script>
<style>{CSS}{GUIDE_EXTRA_CSS}</style>
</head>
<body>
<main class="guide-wrap">
<a class="backlink" href="../">← Back to the storefront</a>
{body_html}
<p><a href="../">Back to the Lee Brower Storefront</a> · <a href="../terms.html">Terms</a></p>
</main>
</body>
</html>
'''


def guides_section_html() -> str:
    icon = CATEGORY_ICONS["Books & Faith"]
    items = "".join(
        f'<a class="guide-item" href="guides/{g["slug"]}.html">'
        f'<strong>{esc(g["title"])}</strong><span>{esc(g["desc"])}</span></a>'
        for g in GUIDES)
    return f'''<section class="guides-sec" id="guides">
<div class="sec-head"><span class="sec-ico"><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg></span><h2>Field Guides</h2><span class="sec-count">{len(GUIDES)}</span><span class="sec-rule"></span></div>
<div class="guide-list">{items}</div>
</section>'''


def write_guides() -> list:
    out_dir = ROOT / "guides"
    out_dir.mkdir(exist_ok=True)
    written = []
    for g in GUIDES:
        src = ROOT / "guides-src" / (g["slug"] + ".md")
        body = md_to_html(src.read_text(encoding="utf-8"))
        page = guide_page_html(g, body)
        (out_dir / (g["slug"] + ".html")).write_text(page, encoding="utf-8")
        written.append(g["slug"])
        print(f"generated guides/{g['slug']}.html: {len(page.encode('utf-8'))} bytes")
    return written


def blog_page_html(b: dict, body_html: str) -> str:
    url = f"{SITE_BASE}/blog/{b['slug']}.html"
    ld = {"@context": "https://schema.org", "@type": "Article",
          "headline": b["title"], "description": b["desc"],
          "author": {"@type": "Person", "name": "Wade Lee Brower Jr"},
          "datePublished": b["date"], "mainEntityOfPage": url}
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(b["title"])} — Lee Brower Blog</title>
<meta name="description" content="{esc(b["desc"])}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Lee Brower Storefront">
<meta property="og:title" content="{esc(b["title"])}">
<meta property="og:description" content="{esc(b["desc"])}">
<meta property="og:url" content="{esc(url)}">
<script type="application/ld+json">
{json.dumps(ld, indent=1, ensure_ascii=False)}
</script>
<script src="https://gumroad.com/js/gumroad.js"></script>
<style>{CSS}{GUIDE_EXTRA_CSS}</style>
</head>
<body>
<main class="guide-wrap">
<a class="backlink" href="./">← Back to the blog</a>
{body_html}
<p><a href="./">Back to the blog</a> · <a href="../">Back to the Lee Brower Storefront</a> · <a href="../terms.html">Terms</a></p>
</main>
</body>
</html>
'''


def blog_section_html() -> str:
    icon = CATEGORY_ICONS["Books & Faith"]
    latest = sorted(BLOGS, key=lambda b: b["date"], reverse=True)[:6]
    items = "".join(
        f'<a class="guide-item" href="blog/{b["slug"]}.html">'
        f'<strong>{esc(b["title"])}</strong><span>{esc(b["date"])} — '
        f'{esc(b["desc"])}</span></a>'
        for b in latest)
    return f'''<section class="guides-sec" id="blog">
<div class="sec-head"><span class="sec-ico"><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg></span><h2>Blog</h2><span class="sec-count">{len(BLOGS)}</span><span class="sec-rule"></span></div>
<div class="guide-list">{items}</div>
<p style="margin-top:1rem"><a href="blog/">See all blog posts →</a></p>
</section>'''


def write_blogs() -> list:
    out_dir = ROOT / "blog"
    out_dir.mkdir(exist_ok=True)
    written = []
    for b in BLOGS:
        src = ROOT / "blog-src" / (b["slug"] + ".md")
        body = md_to_html(src.read_text(encoding="utf-8"))
        page = blog_page_html(b, body)
        (out_dir / (b["slug"] + ".html")).write_text(page, encoding="utf-8")
        written.append(b["slug"])
        print(f"generated blog/{b['slug']}.html: {len(page.encode('utf-8'))} bytes")
    items = "".join(
        f'<a class="guide-item" href="{b["slug"]}.html">'
        f'<strong>{esc(b["title"])}</strong><span>{esc(b["date"])} — '
        f'{esc(b["desc"])}</span></a>'
        for b in sorted(BLOGS, key=lambda b: b["date"], reverse=True))
    index = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog — Lee Brower Storefront</title>
<meta name="description" content="Daily posts on popular subjects, verifiable facts only, from Wade Lee Brower Jr.">
<link rel="canonical" href="{SITE_BASE}/blog/">
<style>{CSS}{GUIDE_EXTRA_CSS}</style>
</head>
<body>
<main class="guide-wrap">
<a class="backlink" href="../">← Back to the storefront</a>
<h1>Lee Brower Blog</h1>
<p class="byline">Daily posts on popular subjects. Verifiable facts only, sources cited in each post.</p>
<div class="guide-list">{items}</div>
<p><a href="../">Back to the Lee Brower Storefront</a></p>
</main>
</body>
</html>
'''
    (out_dir / "index.html").write_text(index, encoding="utf-8")
    print(f"generated blog/index.html: {len(index.encode('utf-8'))} bytes")
    return written


CSS = """
:root{--bg:#0a0c10;--panel:#12151d;--card:#151a24;--line:#262f40;--gold:#d4a94e;--gold2:#f0cd7e;--txt:#f2f4f8;--mut:#a7b0c0;--ink:#171106}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
img{display:block}
a{color:var(--gold)}
.langbar{background:#060708;display:flex;justify-content:flex-end;gap:.25rem;padding:.45rem 1rem;border-bottom:1px solid #1a2030}
.langbar a{color:var(--mut);text-decoration:none;font-size:.85rem;padding:.35rem .7rem;border-radius:999px;min-height:36px;display:inline-flex;align-items:center}
.langbar a:hover{color:var(--gold2)}
.langbar a[aria-current="true"]{background:var(--gold);color:var(--ink);font-weight:700}
.hero{position:relative;overflow:hidden;border-bottom:3px solid var(--gold);background:#0d0f14}
.hero-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 38%}
.hero-shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,9,12,.62) 0%,rgba(8,9,12,.78) 55%,rgba(10,12,16,.97) 100%)}
.hero-inner{position:relative;max-width:1280px;margin:0 auto;padding:3.2rem 1.25rem 2.6rem;text-align:center}
.mark{width:92px;height:92px;margin:0 auto 1.1rem;border-radius:50%;border:2px solid var(--gold);box-shadow:0 10px 34px rgba(0,0,0,.55);object-fit:cover;background:#000}
.hero h1{font-size:clamp(2.3rem,6vw,3.7rem);line-height:1.08;letter-spacing:.4px;font-weight:800}
.hero h1 span{color:var(--gold)}
.hero .tagline{color:#d7dce6;max-width:680px;margin:1.05rem auto 0;font-size:clamp(1rem,2.2vw,1.13rem)}
.hero-meta{margin-top:1rem;color:var(--gold2);font-size:.92rem;letter-spacing:.05em;text-transform:uppercase}
.searchbar{max-width:620px;margin:1.7rem auto 0}
.searchbar input{width:100%;min-height:56px;padding:.9rem 1.5rem;border-radius:999px;border:1px solid rgba(212,169,78,.45);background:rgba(16,19,27,.82);color:var(--txt);font-size:1.05rem;backdrop-filter:blur(6px)}
.searchbar input::placeholder{color:#8d97a9}
.searchbar input:focus{outline:2px solid var(--gold);outline-offset:2px;border-color:var(--gold)}
nav.cats{position:sticky;top:0;z-index:40;background:rgba(9,11,15,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.cats-in{max-width:1280px;margin:0 auto;padding:.55rem 1.25rem;display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center}
.chip{background:#1b2230;color:var(--txt);border:1px solid #2c3648;border-radius:999px;padding:.5rem 1.05rem;font-size:.93rem;cursor:pointer;min-height:48px;display:inline-flex;align-items:center;transition:border-color .2s,background .2s}
.chip:hover{border-color:var(--gold)}
.chip.on{background:var(--gold);color:var(--ink);font-weight:700;border-color:var(--gold)}
main{max-width:1280px;margin:0 auto;padding:0 1.25rem 1rem}
.sec-head{display:flex;align-items:center;gap:.85rem;margin:2.6rem 0 1.15rem}
.sec-ico{flex:0 0 auto;width:46px;height:46px;border:1.5px solid var(--gold);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--gold);background:rgba(212,169,78,.07)}
.sec-ico svg{width:25px;height:25px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
.sec-head h2{font-size:clamp(1.3rem,3vw,1.6rem);font-weight:750;white-space:nowrap}
.sec-count{color:var(--ink);background:var(--gold);border-radius:999px;font-size:.8rem;font-weight:700;padding:.1rem .6rem}
.sec-rule{flex:1;height:2px;background:linear-gradient(90deg,var(--gold),rgba(212,169,78,0))}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(252px,1fr));gap:1.3rem}
.grid.feat{grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
.card{position:relative;background:linear-gradient(180deg,#171d29,#12151d);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column;transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease}
.card:hover{transform:translateY(-4px);border-color:rgba(212,169,78,.65);box-shadow:0 18px 42px rgba(0,0,0,.5)}
.card .shot{position:relative;aspect-ratio:4/3;overflow:hidden;background:#0c0f16}
.card .shot::before{content:"";position:absolute;inset:0;background-image:var(--img);background-size:cover;background-position:center;filter:blur(20px) brightness(.45) saturate(1.1);transform:scale(1.25)}
.card .shot img{position:relative;width:100%;height:100%;object-fit:contain;font-size:0;color:transparent}
.card.feat .shot{aspect-ratio:16/9}
.card .tag{position:absolute;top:.7rem;left:.7rem;z-index:2;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--gold2);background:rgba(8,9,12,.78);border:1px solid rgba(212,169,78,.5);border-radius:999px;padding:.22rem .65rem;backdrop-filter:blur(4px)}
.card .ribbon{position:absolute;top:.7rem;right:.7rem;z-index:2;font-size:.72rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:var(--ink);background:linear-gradient(90deg,var(--gold),var(--gold2));border-radius:999px;padding:.28rem .7rem}
.card .body{padding:1.05rem 1.15rem 1.2rem;display:flex;flex-direction:column;flex:1}
.card h3{font-size:1.02rem;line-height:1.38;margin-bottom:.4rem;font-weight:700}
.card.feat h3{font-size:1.15rem}
.card .blurb{color:var(--mut);font-size:.92rem;flex:1}
.cardfoot{display:flex;align-items:center;justify-content:space-between;gap:.8rem;margin-top:1rem}
.price{color:var(--gold);font-weight:800;font-size:1.28rem;white-space:nowrap}
.price .was{color:var(--mut);text-decoration:line-through;font-weight:400;font-size:.98rem;margin-right:.35rem}
a.buy{background:linear-gradient(180deg,var(--gold2),var(--gold));color:var(--ink);text-align:center;padding:.7rem 1.5rem;border-radius:11px;text-decoration:none;font-weight:800;font-size:1rem;min-height:48px;display:inline-flex;align-items:center;box-shadow:0 6px 18px rgba(212,169,78,.25);transition:filter .2s}
a.buy:hover{filter:brightness(1.1)}
.noresults{display:none;color:var(--mut);text-align:center;margin:3rem 0;font-size:1.08rem}
.vendor{max-width:820px;margin:3.4rem auto 0;padding:1.7rem 1.8rem;background:linear-gradient(180deg,#171d29,#12151d);border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:14px}
.vendor h2{color:var(--gold);font-size:1.3rem;margin-bottom:.7rem}
.vendor p,.vendor li{color:var(--mut);font-size:.97rem}
.vendor ul{margin:.7rem 0 .7rem 1.25rem}
.vendor .vprice{color:var(--txt);font-size:1.06rem}
.vendor a.vbtn{display:inline-flex;align-items:center;min-height:48px;background:#232b3a;color:var(--txt);padding:.75rem 1.3rem;border-radius:10px;text-decoration:none;font-weight:700;margin-top:.9rem;border:1px solid #2c3648}
.vendor a.vbtn:hover{background:var(--gold);color:var(--ink)}
footer{border-top:1px solid var(--line);margin-top:3.4rem;background:#08090c}
.foot-in{max-width:1280px;margin:0 auto;padding:1.8rem 1.25rem 2.6rem;color:var(--mut);font-size:.88rem}
footer a{color:var(--gold);text-decoration:none}
footer a:hover{text-decoration:underline}
@media (max-width:700px){
  .langbar{flex-wrap:wrap;justify-content:center}
  .hero-inner{padding:2.4rem 1rem 2rem}
  .mark{width:76px;height:76px}
  main{padding:0 1rem 1rem}
  .grid,.grid.feat{grid-template-columns:1fr}
  .card .shot{aspect-ratio:16/10}
  .sec-head h2{white-space:normal}
  .cats-in{justify-content:flex-start;flex-wrap:nowrap;overflow-x:auto;padding:.55rem 1rem}
  .chip{flex:0 0 auto}
  .vendor{padding:1.3rem 1.15rem}
}
@media (min-width:701px) and (max-width:1024px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(215px,1fr))}
  .grid.feat{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .card,a.buy,.chip{transition:none}
  .card:hover{transform:none}
}
"""

JS = """
(function(){
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('.shelf-sec'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var search = document.getElementById('search');
  var noresults = document.getElementById('noresults');
  var filter = 'all';
  function apply(){
    var q = search.value.trim().toLowerCase();
    var visible = 0;
    cards.forEach(function(c){
      var inFeatured = c.closest('#featured') !== null;
      var isDup = c.getAttribute('data-dup') === '1';
      // One copy per view: a category duplicate shows only under its own
      // category filter; a featured-shelf card shows under All/Featured
      // but hides under a category filter (the category copy covers it).
      var okCat = isDup ? (c.getAttribute('data-category') === filter) :
                  inFeatured ? ((filter === 'all') || (filter === 'Featured')) :
                  ((filter === 'all') || (c.getAttribute('data-category') === filter));
      var okQ = !q || c.getAttribute('data-search').indexOf(q) !== -1;
      var show = okCat && okQ;
      c.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    sections.forEach(function(s){
      var any = Array.prototype.some.call(s.querySelectorAll('.card'), function(c){ return c.style.display !== 'none'; });
      s.style.display = any ? '' : 'none';
    });
    noresults.style.display = visible ? 'none' : 'block';
  }
  chips.forEach(function(ch){
    ch.addEventListener('click', function(){
      chips.forEach(function(x){ x.classList.remove('on'); });
      ch.classList.add('on');
      filter = ch.getAttribute('data-filter');
      apply();
    });
  });
  search.addEventListener('input', apply);
})();
"""



def localized(r: dict, lang: str):
    """(title, blurb) for a product in the page language."""
    if lang == "es" and r["handle"] in i18n.ES_PRODUCTS:
        return i18n.ES_PRODUCTS[r["handle"]]
    return r["title"], r["blurb"]


def card_html(r: dict, lang: str, feat: bool = False, dup: bool = False) -> str:
    ch = i18n.CHROME[lang]
    cats = i18n.CATEGORIES[lang]
    title, blurb = localized(r, lang)
    url = GUMROAD_BASE + r["gumroad_slug"]
    img = cover_src(r, lang)
    cat_local = cats.get(r["category"], r["category"])
    search = " ".join([title, r["title"], cat_local, r["category"],
                       r["tags"], blurb, r["blurb"]]).lower()
    blurb_html = f'<p class="blurb">{esc(blurb)}</p>' if blurb else ""
    compare = (f'<span class="was">${esc(r["compare_at_price"])}</span>'
               if r["compare_at_price"] else "")
    ribbon = f'<span class="ribbon">{esc(ch["featured"])}</span>' if feat else ""
    cls = "card feat" if feat else "card"
    # dup=True: the category-section copy of a featured product. It gets a
    # suffixed id (the featured card keeps the canonical anchor) and a
    # data-dup flag so the filter JS shows exactly one copy per view.
    card_id = esc(anchor_id(r)) + ("-cat" if dup else "")
    dup_attr = ' data-dup="1"' if dup else ""
    return f'''<article class="{cls}" id="{card_id}" data-category="{esc(cat_local)}"{dup_attr} data-search="{esc(search)}">
<div class="shot" style="--img:url(&quot;{esc(img)}&quot;)"><img src="{esc(img)}" alt="{esc(r["image_alt"])}" loading="lazy" decoding="async"><span class="tag">{esc(cat_local)}</span>{ribbon}</div>
<div class="body">
<h3>{esc(title)}</h3>
{blurb_html}
<div class="cardfoot"><div class="price">{compare}${esc(r["price"])}</div>
<a class="buy" href="{esc(url)}">{esc(ch["buy"])}</a></div>
</div>
</article>'''


def section_html(cat_en: str, rows: list, lang: str, feat: bool = False,
                 dup_handles: set = frozenset()) -> str:
    ch = i18n.CHROME[lang]
    name = ch["featured"] if feat else i18n.CATEGORIES[lang].get(cat_en, cat_en)
    icon = (CATEGORY_ICONS["Featured"] if feat
            else CATEGORY_ICONS.get(cat_en, CATEGORY_ICONS["Other"]))
    sid = "featured" if feat else f"cat-{slugify(cat_en)}"
    grid_cls = "grid feat" if feat else "grid"
    cards = "".join(card_html(r, lang, feat, dup=(r["handle"] in dup_handles))
                    for r in rows)
    return f'''<section class="shelf-sec" id="{sid}">
<div class="sec-head"><span class="sec-ico"><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg></span><h2>{esc(name)}</h2><span class="sec-count">{len(rows)}</span><span class="sec-rule"></span></div>
<div class="{grid_cls}">{cards}</div>
</section>'''


def langbar_html(lang: str) -> str:
    items = []
    for L in i18n.LANGS:
        if lang == "en":
            href = "./" if L == "en" else f"{i18n.LANG_PATH[L]}"
        else:
            href = "../" if L == "en" else f"../{i18n.LANG_PATH[L]}"
            if L == lang:
                href = "./"
        cur = ' aria-current="true"' if L == lang else ""
        items.append(f'<a href="{href}" hreflang="{L}"{cur}>{esc(i18n.LANG_NAMES[L])}</a>')
    return '<div class="langbar">' + "".join(items) + "</div>"




def render_page(lang: str, rows: list, featured: list, by_cat: dict,
                cats: list, json_ld: str) -> str:
    ch = i18n.CHROME[lang]
    meta = i18n.STORE_META[lang]
    prefix = "../" if lang != "en" else ""
    nav = [f'<button class="chip on" data-filter="all">{esc(ch["all"])}</button>',
           f'<button class="chip" data-filter="Featured">{esc(ch["featured"])}</button>']
    for c in cats:
        local = i18n.CATEGORIES[lang].get(c, c)
        nav.append(f'<button class="chip" data-filter="{esc(local)}">{esc(local)}</button>')
    sections = [section_html("Featured", featured, lang, feat=True)]
    # Category sections include featured products too (as dup cards), so a
    # flagship is findable by scrolling its category, not only on the
    # Featured shelf. The filter JS shows exactly one copy per view.
    dup_handles = {r["handle"] for r in featured}
    for c in cats:
        sections.append(section_html(c, by_cat[c], lang,
                                     dup_handles=dup_handles))
    ld = f'<script type="application/ld+json">\n{json_ld}\n</script>\n' if lang == "en" else ""
    rel_root = "./" if lang == "en" else "../"
    return f'''<!DOCTYPE html>
<!-- Generated by build_store.py from products.csv — edit the CSV, not this file. -->
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(meta["title"])}</title>
<meta name="description" content="{esc(meta["desc"])}">
<link rel="canonical" href="{esc(lang_url(lang))}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Lee Brower Storefront">
<meta property="og:title" content="{esc(meta["title"])}">
<meta property="og:description" content="{esc(meta["desc"])}">
<meta property="og:url" content="{esc(lang_url(lang))}">
<meta property="og:image" content="{SITE_BASE}/covers/contractoros.webp">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(meta["title"])}">
<meta name="twitter:description" content="{esc(meta["desc"])}">
<meta name="twitter:image" content="{SITE_BASE}/covers/contractoros.webp">
{hreflang_links()}
{ld}<script src="https://gumroad.com/js/gumroad.js"></script>
<style>{CSS}</style>
</head>
<body>
{langbar_html(lang)}
<header class="hero">
<img class="hero-bg" src="{prefix}{HERO_IMG}" alt="" fetchpriority="high">
<div class="hero-shade"></div>
<div class="hero-inner">
<img class="mark" src="{prefix}{LOGO_IMG}" alt="Lee Brower — hard hat logo" width="184" height="184">
<h1>Lee Brower <span>Storefront</span></h1>
<p class="tagline">{esc(ch["tagline"])}</p>
<p class="hero-meta">{esc(meta["hero_meta"].format(n=len(rows)))}</p>
<div class="searchbar"><input id="search" type="search" placeholder="{esc(ch["search_ph"])}" aria-label="{esc(ch["search_label"])}"></div>
</div>
</header>
<nav class="cats" aria-label="{esc(ch["cats_label"])}"><div class="cats-in">{''.join(nav)}</div></nav>
<main id="store">
{''.join(sections)}{guides_section_html() if lang == "en" else ""}{blog_section_html() if lang == "en" else ""}
<p class="noresults" id="noresults">{esc(ch["noresults"])}</p>
</main>
<footer>
<div class="foot-in">
<p>{esc(ch["footer_prices"])} <a href="{rel_root}terms.html">{esc(ch["footer_terms"])}</a> · <a href="{rel_root}products/merch.html">{esc(ch["footer_merch"])}</a> · {esc(ch["footer_hub_pre"])}<a href="https://wadebrower792.github.io/lee-brower-store/">{esc(ch["footer_hub"])}</a>.</p>
</div>
</footer>
<script>{JS}</script>
</body>
</html>
'''


def main() -> None:
    rows = [r for r in csv.DictReader(CSV_PATH.open(newline="", encoding="utf-8"))
            if r["status"] == "live"]
    featured = sorted([r for r in rows if r["featured"] == "true"],
                      key=lambda r: -price_num(r))
    # Category sections include featured rows too (rendered as dup cards);
    # the filter JS guarantees one visible copy per view.
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    cats = [c for c in CATEGORY_ORDER if c in by_cat] + \
           [c for c in by_cat if c not in CATEGORY_ORDER]
    for c in cats:
        by_cat[c].sort(key=lambda r: int(r["sort_order"]))

    json_ld = store_jsonld(rows)
    for lang in i18n.LANGS:
        page = render_page(lang, rows, featured, by_cat, cats, json_ld)
        if lang == "en":
            out = ROOT / "index.html"
        else:
            out = ROOT / i18n.LANG_PATH[lang] / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print(f"generated {out.relative_to(ROOT)}: {len(page.encode('utf-8'))} bytes")

    write_guides()
    write_blogs()
    n_urls = write_sitemap(rows)
    write_robots()
    print(f"generated sitemap.xml: {n_urls} URLs (canonical set + hreflang alternates)")
    print(f"generated robots.txt")
    print(f"cards per page: {len(rows) + len(featured)} rendered ({len(rows)} products, {len(featured)} also in categories, {len(cats)} categories)")


if __name__ == "__main__":
    main()
