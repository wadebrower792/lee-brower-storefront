# SEO Overnight Run — 2026-10-26 (Weeks 2–4, digital plan)

$0 spent. No Gumroad changes, no new products, no outreach, no messages sent.
All work on Lee's own GitHub Pages storefront only (authorized).

## Pages built and published

1. compare/contractoros-vs-buildertrend.html
   https://wadebrower792.github.io/lee-brower-storefront/compare/contractoros-vs-buildertrend.html
2. compare/contractoros-vs-jobtread.html
   https://wadebrower792.github.io/lee-brower-storefront/compare/contractoros-vs-jobtread.html
3. compare/contractoros-vs-fieldwire.html
   https://wadebrower792.github.io/lee-brower-storefront/compare/contractoros-vs-fieldwire.html
4. products/contractoros-phone.html (phone page)
   https://wadebrower792.github.io/lee-brower-storefront/products/contractoros-phone.html

Also changed: products/contractoros.html (internal links to all four new pages),
sitemap.xml (4 new URLs appended manually; build_store.py regenerates only index
pages + sitemap from products.csv and does NOT cover compare/ pages, so it was
not run — running it would have rewritten index pages for no gain).

## Prices verified live, 2026-10-26 (search, vendor pages + corroborating listings)

- Buildertrend: QUOTE ONLY. Buildertrend's own site says pricing is based on
  business size and project volume with a personalized quote; multiple 2026
  sources confirm no published pricing (pricing page is a quote request flow).
  Old tier prices circulating in third-party articles were NOT printed as prices
  — the page says to treat them as unverified unless they come from your own quote.
- JobTread: $199/mo first user billed monthly; $159/mo first user billed
  annually; +$20/mo per additional user monthly, +$18/mo annual; price breaks
  after 10 users; all features included; no free trial, 30-day money-back
  guarantee per JobTread. Sources: JobTread's own blog (jobtread.com) + GetApp
  vendor-FAQ listings, consistent across sources.
- Fieldwire: Basic $0 (100 sheets, 3 projects); Pro $29/user/mo; Business
  $49/user/mo; Premier $89/user/mo, billed annually. Sources: multiple current
  listings (Software Finder, FinancesOnline, SourceForge, Slashdot) in agreement.
  DISCREPANCY LOGGED: the Oct 25 snapshot figures (Free/$39/$64/$89) do NOT
  match current listings and were NOT reused; one outlier listing ($39/$59/$99)
  was also not used. Pages carry "verify before buying."
- ContractorOS (verified record, unchanged): Solo $49 / Pro $149 / Business $399 /
  Contractor $799 per month, 1-month free trial, checkout by Gumroad.
  Never claimed: one-time ownership, money-back guarantee, live customization,
  Procore/Autodesk sync, CPM scheduling, marketplace integration.

## Honest-lacks handling

Every comparison page carries a "Where ContractorOS honestly lacks" section in
the Procore-page pattern. Offline queue and AR measurement are described ONLY
as built in phone app builds (v1.21/v1.19) and awaiting Lee's on-device verdict
— never as shipped. Photo stamps: designed, not built. Customization: not
proven, not claimed. Branding separation kept: no page says "ContractorOS by
Siteworx"; each states ContractorOS is not a Siteworx product. Siteworx OS is
never marketed on these pages.

## Git

- Pull: fast-forward only (pulled in a cinet pointer rotation, f303c1b).
- Commit: 99ddef8 "SEO: ContractorOS vs Buildertrend/JobTread/Fieldwire
  comparisons + phone page (Week 2-4, digital plan)" — 6 files, 321 insertions.
- Push: OK, main f303c1b..99ddef8. No force-push.
- Identity: wadebrower792 <163772005+wadebrower792@users.noreply.github.com>.

## Live verification (after Pages deploy lag, ~90s + re-check)

All four pages: HTTP 200, correct <title>, Gumroad /l/contractoros-v3 link
present, price-table markers present ("Quote only" / "$199/mo" / "$29/user/mo"),
honest-lacks section present. Phone page: YouTube embed mg4aVYXUdJM present,
SAMPLE DATA ONLY badge present. Product page re-check: new internal links live.

## Skipped / unverified

- Nothing skipped. No figure was printed without a live check; Buildertrend has
  no published figure to print, so the page prints quote-only.
- The Procore comparison page's old "Offline queue: designed, not built" line
  was NOT touched in this run (out of scope); it is now stale relative to the
  v1.21/v1.19 builds and should be updated in a later pass if Lee wants it.
- Directory listings (Capterra/GetApp/Software Advice) were NOT part of this
  task and remain open from the Week 1 plan.
