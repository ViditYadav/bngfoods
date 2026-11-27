#!/usr/bin/env python3
"""
BNG Foods – builds Google-friendly pages from your product data.

What it makes (only for products that are LIVE: Show on Website = Yes and a price):
  products/                      all products, grouped by category
  products/<category>/           one page per category
  products/<product>/            one page per product (name, Hindi name, pack sizes, prices, bulk info)
  bulk-spices/                   bulk / wholesale supply page
  sitemap.xml, robots.txt        so Google finds every page

Where the data comes from (same as the website):
  1. Your published Google Sheet (links in store.json -> shop.sheetProductsCsv / sheetSettingsCsv)
  2. store.json, if the sheet can't be reached

Run:  python tools/build_pages.py
GitHub runs it automatically every day (.github/workflows/build-pages.yml), so you never need to.
Only Python's standard library is used.
"""
import csv, hashlib, html, io, json, os, re, sys, urllib.request, urllib.parse
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", ".generated.json")
TODAY = date.today().isoformat()
e = lambda s: html.escape(str(s or ""), quote=True)

# ---------------------------------------------------------------- data
SHEET_ERR = re.compile(r"^#(ERROR!|NAME\?|VALUE!|REF!|N/A|DIV/0!|NUM!|NULL!)", re.I)

def read_csv_text(text):
    rows = [[("" if SHEET_ERR.match(c.strip()) else c) for c in r] for r in csv.reader(io.StringIO(text))]
    return [r for r in rows if any(c.strip() for c in r)]

def fetch(url):
    sep = "&" if "?" in url else "?"
    with urllib.request.urlopen(url + sep + "t=build", timeout=20) as r:
        return r.read().decode("utf-8")

def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(t or "").lower())).strip()

def slug(t):
    s = re.sub(r"[^a-z0-9]+", "-", norm(t)).strip("-")
    return s or "item"

def yes(v):
    return str(v or "").strip().lower() in ("y", "yes", "true", "1", "haan", "हाँ", "हां")

def img_path(v):
    v = str(v or "").strip()
    if not v: return ""
    return v if re.match(r"^(https?:|data:|/|images/|videos/)", v, re.I) else "images/" + v

def head_index(head, *names):
    h = [norm(x) for x in head]
    for n in names:
        for i, x in enumerate(h):
            if x.startswith(n): return i
    return -1

def grams(label):
    m = re.match(r"^([\d.]+)\s*(kg|g)", norm(label).replace(" ", "") or "")
    if not m:
        m = re.match(r"^([\d.]+)\s*(kg|g)\b", str(label).strip().lower())
    return float(m.group(1)) * (1000 if m.group(2) == "kg" else 1) if m else None

def products_from_sheet(rows):
    head, body = rows[0], rows[1:]
    I = {k: head_index(head, *n) for k, n in {
        "cat": ["category"], "name": ["product"], "hindi": ["hindi"], "desc": ["description"], "size": ["pack"],
        "price": ["price"], "img": ["image"], "photo": ["full photo"], "special": ["special"], "kw": ["search"], "show": ["show"]}.items()}
    out = {}
    for r in body:
        g = lambda k: str(r[I[k]]).strip() if 0 <= I[k] < len(r) else ""
        name, size = g("name"), g("size")
        try: price = float(re.sub(r"[^\d.]", "", g("price")) or 0)
        except ValueError: price = 0
        if not name or not size or price <= 0: continue
        if I["show"] >= 0 and g("show") and not yes(g("show")): continue
        p = out.get(name)
        if not p:
            p = out[name] = {"id": slug(name), "cat": g("cat") or "Products", "name": name, "hindi": g("hindi"), "desc": g("desc"),
                             "keywords": [x.strip() for x in re.split(r"[,;]", g("kw")) if x.strip()], "featured": yes(g("special")), "packs": []}
        p["packs"].append([size, price, img_path(g("img"))])
    return list(out.values())

def settings_from_sheet(rows, shop):
    for r in rows:
        k, v = norm(r[0] if r else ""), (r[1].strip() if len(r) > 1 else "")
        if not k or k.startswith("setting") or not v: continue
        if k.startswith("whatsapp api"): continue
        if k.startswith("whatsapp"):
            d = re.sub(r"\D", "", v)
            if len(d) >= 10: shop["whatsapp"] = "91" + d if len(d) == 10 else d
        elif k.startswith("phone"): shop["phoneDisplay"] = v
        elif k.startswith("email"): shop["email"] = v
        elif k.startswith("brand") or k.startswith("business name"): shop["name"] = v
        elif k.startswith("tagline"): shop["tagline"] = v
        elif k.startswith("hindi"): shop["taglineHindi"] = v
        elif k.startswith("instagram") or k.startswith("youtube") or k.startswith("facebook"): shop[k.split()[0]] = v

def load():
    store = json.load(open(os.path.join(ROOT, "store.json"), encoding="utf-8"))
    shop = store["shop"]; products = store.get("products", []); source = "store.json"
    local = os.environ.get("SHEET_CSV_FILE")          # for testing: a downloaded Products CSV
    try:
        text = open(local, encoding="utf-8").read() if local else (fetch(shop["sheetProductsCsv"]) if shop.get("sheetProductsCsv") else "")
        rows = read_csv_text(text) if text else []
        sheet_products = products_from_sheet(rows) if len(rows) > 1 else []
        if sheet_products: products, source = sheet_products, "Google Sheet"
    except Exception as ex:
        print("Google Sheet not reachable, using store.json:", ex)
    try:
        if shop.get("sheetSettingsCsv") and not local: settings_from_sheet(read_csv_text(fetch(shop["sheetSettingsCsv"])), shop)
    except Exception as ex:
        print("Settings tab not reachable, using store.json:", ex)
    # normalise store.json products to [size, price, image]
    for p in products:
        p["packs"] = [[pk[0], float(pk[1]), img_path(pk[2] if len(pk) > 2 else p.get("image", ""))] for pk in p["packs"] if float(pk[1]) > 0]
        p["slug"] = slug(p["name"])
    products = [p for p in products if p["packs"]]
    return store, shop, products, source

# ---------------------------------------------------------------- page parts
def inr(n): return "₹" + f"{int(n):,}" if float(n).is_integer() else "₹" + f"{n:,.2f}"

CSS = """
:root{--bg:#fbf7f0;--ink:#2a1a12;--muted:#7b6a58;--line:#ece2d3;--maroon:#7d1616;--maroon-d:#4a0d0d;--gold:#e8b32c;--gold-l:#ffd45c}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
:lang(hi),[lang=hi]{font-family:Hind,Inter,sans-serif}a{color:var(--maroon)}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
header{background:var(--maroon-d);color:#fff;border-bottom:2px solid var(--gold)}
header .wrap{display:flex;align-items:center;gap:12px;min-height:60px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff;flex:1;min-width:0}
.brand img{height:44px}.brand b{font-family:Fraunces,serif;font-size:18px;display:block}
.brand span{font-size:12.5px;color:var(--gold);display:block;line-height:1.55}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:999px;padding:11px 18px;font-weight:700;text-decoration:none;border:0;cursor:pointer;font-size:15px}
.btn-gold{background:linear-gradient(135deg,#ffd45c,#f0a81c);color:#3b1d00}.btn-wa{background:linear-gradient(135deg,#3a9a44,#22742c);color:#fff}
.btn-red{background:linear-gradient(135deg,#e8372c,#b3141c);color:#fff}.btn-line{border:1.5px solid var(--maroon);color:var(--maroon);background:#fff}
header .btn{padding:8px 14px;font-size:13.5px}
.crumbs{font-size:13px;color:var(--muted);margin:14px 0 4px}.crumbs a{color:var(--muted)}
h1{font-family:Fraunces,serif;color:var(--maroon);font-size:clamp(26px,5vw,38px);line-height:1.15;margin:6px 0 4px}
h1 small{display:block;font-family:Hind,Inter,sans-serif;font-size:.6em;color:var(--ink);font-weight:600;line-height:1.5;margin-top:4px}
h2{font-family:Fraunces,serif;color:var(--maroon);font-size:clamp(20px,3.6vw,26px);margin:26px 0 10px}
.lead{font-size:16.5px;color:#4a3a2c;max-width:70ch}
.prod{display:grid;gap:20px;align-items:start;margin-top:10px}
@media(min-width:760px){.prod{grid-template-columns:340px 1fr}}
.pic{background:#fff;border:1px solid var(--line);border-radius:18px;padding:14px;text-align:center}
.pic img{max-width:100%;height:auto;max-height:340px;object-fit:contain}
.pic.ph{display:grid;place-items:center;min-height:240px;font-family:Hind,Inter,sans-serif;font-size:30px;color:var(--maroon)}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;font-size:15px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}th{background:#f6ecdc;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#6b4a2b}
td.p{font-weight:800}
.acts{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}
.box{background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}@media(min-width:700px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
.card{display:block;background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px;text-decoration:none;color:var(--ink)}
.card img{width:100%;height:130px;object-fit:contain}.card .ph{height:130px;display:grid;place-items:center;font-family:Hind,Inter,sans-serif;font-size:20px;color:var(--maroon);background:#faf3e6;border-radius:10px}
.card b{display:block;font-size:14px;margin-top:6px}.card span{font-size:12.5px;color:var(--muted)}
ul.ticks{padding-left:20px}ul.ticks li{margin:4px 0}
details{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:8px 0}summary{font-weight:700;cursor:pointer}
footer{background:linear-gradient(180deg,#4a0d0d,#2e0808);color:#e6cdb0;font-size:13.5px;padding:20px 0 26px;margin-top:36px}
footer a{color:#fff}footer p{margin:6px 0}footer .links a{margin-right:14px;display:inline-block;padding:3px 0}
"""

def page(depth, title, desc, canonical, body, ld, shop, og_image=None):
    up = "../" * depth
    site = shop.get("siteUrl", "").rstrip("/")
    ogi = og_image or (site + "/images/og-image.jpg")
    lds = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    wa = f"https://wa.me/{shop['whatsapp']}?text=" + urllib.parse.quote(f"Namaste {shop['name']}, I have a question about your products.")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(shop['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{e(ogi)}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#4a0d0d">
<link rel="icon" type="image/png" href="{up}images/favicon-48.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Inter:wght@400;600;700;800&family=Hind:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
{lds}
</head><body>
<header><div class="wrap">
  <a class="brand" href="{up}"><img src="{up}{e(shop.get('logo','images/logo.png'))}" alt="{e(shop['name'])} logo" width="41" height="44"><span><b>{e(shop['name'])}</b><span lang="hi">{e(shop.get('taglineHindi',''))}</span></span></a>
  <a class="btn btn-gold" href="{up}">Shop online</a>
</div></header>
<main class="wrap">
{body}
</main>
{footer(depth, shop)}
</body></html>
"""

def address_line(shop):
    a = shop.get("address") or {}
    return ", ".join(x for x in [a.get("street"), a.get("town"), (a.get("district") or "") + (" District" if a.get("district") else ""), a.get("state"), a.get("pincode")] if x)

def footer(depth, shop):
    up = "../" * depth
    tel = re.sub(r"\D", "", shop.get("phoneDisplay", "")) or shop["whatsapp"]
    tel = ("91" + tel) if len(tel) == 10 else tel
    cats = shop["_cats"]
    links = "".join(f'<a href="{up}products/{slug(c)}/">{e(c)}</a>' for c in cats)
    return f"""<footer><div class="wrap">
  <p><b style="color:#fff">{e(shop['name'])}</b> · <span lang="hi">{e(shop.get('taglineHindi',''))}</span> · {e(shop.get('tagline',''))}</p>
  <p>{e(address_line(shop))}{(' · <a href="' + e((shop.get('address') or {}).get('mapsUrl')) + '">Get directions</a>') if (shop.get('address') or {}).get('mapsUrl') else ''}</p>
  <p><a href="tel:+{e(tel)}">{e(shop.get('phoneDisplay',''))}</a> · <a href="mailto:{e(shop.get('email',''))}">{e(shop.get('email',''))}</a> · <a href="https://wa.me/{e(shop['whatsapp'])}">WhatsApp</a></p>
  <p class="links"><a href="{up}">Shop online</a><a href="{up}products/">All products</a>{links}<a href="{up}bulk-spices/">Bulk spices</a><a href="{up}#certificates">Licences</a></p>
  <p style="font-size:12px;color:#b99b7a">{shop['_lic']}</p>
</div></footer>"""

def org_ld(shop):
    a = shop.get("address") or {}
    site = shop.get("siteUrl", "").rstrip("/")
    tel = re.sub(r"\D", "", shop.get("phoneDisplay", "")) or shop["whatsapp"]
    tel = ("91" + tel) if len(tel) == 10 else tel
    d = {"@context": "https://schema.org", "@type": "LocalBusiness", "@id": site + "/#business", "name": shop["name"],
         "description": shop.get("intro", ""), "url": site + "/", "logo": site + "/" + shop.get("logo", "images/logo.png"),
         "image": site + "/images/og-image.jpg", "telephone": "+" + tel, "email": shop.get("email", ""),
         "address": {"@type": "PostalAddress", "streetAddress": a.get("street", ""), "addressLocality": a.get("town", ""),
                     "addressRegion": a.get("state", ""), "postalCode": a.get("pincode", ""), "addressCountry": "IN"},
         "areaServed": shop.get("servesAreas") or "IN", "slogan": shop.get("tagline", "")}
    same = [shop[k] for k in ("instagram", "youtube", "facebook") if shop.get(k)]
    if same: d["sameAs"] = same
    if a.get("mapsUrl"): d["hasMap"] = a["mapsUrl"]
    return d

def crumbs_ld(items, site):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": site + u} for i, (n, u) in enumerate(items)]}

def wa_link(shop, text): return f"https://wa.me/{shop['whatsapp']}?text=" + urllib.parse.quote(text)

def first_img(p):
    for pk in p["packs"]:
        if pk[2]: return pk[2]
    return ""

def card(p, up):
    im = first_img(p)
    pic = f'<img src="{up}{e(im)}" alt="{e(p["name"])}" loading="lazy">' if im and not im.startswith("http") else (f'<img src="{e(im)}" alt="{e(p["name"])}" loading="lazy">' if im else f'<div class="ph" lang="hi">{e(p.get("hindi") or p["name"])}</div>')
    lo = min(pk[1] for pk in p["packs"])
    return f'<a class="card" href="{up}products/{p["slug"]}/">{pic}<b>{e(p["name"])}</b><span lang="hi">{e(p.get("hindi",""))}</span><br><span>From {inr(lo)}</span></a>'

# ---------------------------------------------------------------- pages
def product_page(p, shop, by_cat):
    site = shop["siteUrl"].rstrip("/"); up = "../../"
    url = f"{site}/products/{p['slug']}/"
    sizes = [pk[0] for pk in p["packs"]]
    bulk = [pk for pk in p["packs"] if (grams(pk[0]) or 0) >= 5000]
    hi = f" ({p['hindi']})" if p.get("hindi") else ""
    area = (shop.get("address") or {}).get("district", "")
    title = f"{p['name']}{hi} – Manufacturer in {area}, MP | {shop['name']}" if area else f"{p['name']}{hi} | {shop['name']}"
    if len(title) > 75: title = f"{p['name']} – {area}, MP | {shop['name']}" if area else f"{p['name']} | {shop['name']}"
    desc = f"{p.get('desc','').rstrip('.')}. Available in {', '.join(sizes)}" + (" incl. bulk bags" if bulk else "") + \
           f". Factory-direct from {shop['name']}, {(shop.get('address') or {}).get('town','')}, {area} (MP). Order online or on WhatsApp."
    im = first_img(p)
    pic = f'<div class="pic"><img src="{up}{e(im)}" alt="{e(p["name"])} – {e(shop["name"])}" width="340" height="340"></div>' if im else f'<div class="pic ph" lang="hi">{e(p.get("hindi") or p["name"])}</div>'
    rows = "".join(f"<tr><td>{e(pk[0])}</td><td class='p'>{inr(pk[1])}</td></tr>" for pk in p["packs"])
    order_text = f"Namaste {shop['name']}, I want to order {p['name']}."
    bulk_text = f"Namaste {shop['name']}, I want bulk price for {p['name']}."
    related = [q for q in by_cat[p["cat"]] if q is not p][:8]
    body = f"""
<nav class="crumbs"><a href="{up}">Home</a> › <a href="{up}products/">Products</a> › <a href="{up}products/{slug(p['cat'])}/">{e(p['cat'])}</a> › {e(p['name'])}</nav>
<div class="prod">
  {pic}
  <div>
    <h1>{e(p['name'])}{f'<small lang="hi">{e(p["hindi"])}</small>' if p.get('hindi') else ''}</h1>
    <p class="lead">{e(p.get('desc',''))}</p>
    <table><thead><tr><th>Pack size</th><th>Price</th></tr></thead><tbody>{rows}</tbody></table>
    <div class="acts">
      <a class="btn btn-red" href="{up}#p-{p['slug']}">Order online</a>
      <a class="btn btn-wa" href="{e(wa_link(shop, order_text))}">Order on WhatsApp</a>
      {f'<a class="btn btn-line" href="{e(wa_link(shop, bulk_text))}">Get bulk price</a>' if bulk else ''}
    </div>
  </div>
</div>
<div class="box">
  <h2 style="margin-top:4px">Why buy from {e(shop['name'])}</h2>
  <ul class="ticks">
    <li>Processed and packed in our own unit in {e((shop.get('address') or {}).get('town',''))}, {e(area)} District, Madhya Pradesh.</li>
    {''.join(f'<li>{e(b)}</li>' for b in shop.get('badges', []))}
    {'<li>Bulk bags of ' + ', '.join(e(pk[0]) for pk in bulk) + ' for shops, wholesalers, hotels and caterers. <a href="' + up + 'bulk-spices/">Bulk supply details</a></li>' if bulk else ''}
    <li>Registered food business: {shop['_lic_short']}</li>
  </ul>
</div>
{f'<h2>More {e(p["cat"])}</h2><div class="grid">' + ''.join(card(q, up) for q in related) + '</div>' if related else ''}
"""
    ld = [{"@context": "https://schema.org", "@type": "Product", "name": p["name"], "alternateName": p.get("hindi") or None,
           "description": p.get("desc", ""), "sku": p["slug"], "category": p["cat"], "url": url,
           "image": [site + "/" + im] if im and not im.startswith("http") else ([im] if im else [site + "/images/og-image.jpg"]),
           "brand": {"@type": "Brand", "name": shop["name"]}, "manufacturer": {"@id": site + "/#business"},
           "offers": {"@type": "AggregateOffer", "priceCurrency": "INR", "lowPrice": min(pk[1] for pk in p["packs"]),
                      "highPrice": max(pk[1] for pk in p["packs"]), "offerCount": len(p["packs"]),
                      "availability": "https://schema.org/InStock", "seller": {"@id": site + "/#business"}}},
          crumbs_ld([("Home", "/"), ("Products", "/products/"), (p["cat"], f"/products/{slug(p['cat'])}/"), (p["name"], f"/products/{p['slug']}/")], site),
          org_ld(shop)]
    ld[0] = {k: v for k, v in ld[0].items() if v is not None}
    return page(2, title, desc, url, body, ld, shop, og_image=(site + "/" + im) if im and not im.startswith("http") else None)

def category_page(cat, items, shop):
    site = shop["siteUrl"].rstrip("/"); up = "../../"; cs = slug(cat)
    url = f"{site}/products/{cs}/"
    area = (shop.get("address") or {}).get("district", "")
    has_bulk = any((grams(pk[0]) or 0) >= 5000 for p in items for pk in p["packs"])
    title = f"{cat} Manufacturer in {area}, MP – Retail & Bulk | {shop['name']}"
    names = ", ".join(p["name"] for p in items[:6])
    desc = f"{cat} from {shop['name']}: {names}. Factory-direct from {area}, Madhya Pradesh" + (", in retail packs and bulk bags." if has_bulk else ".")
    body = f"""
<nav class="crumbs"><a href="{up}">Home</a> › <a href="{up}products/">Products</a> › {e(cat)}</nav>
<h1>{e(cat)}</h1>
<p class="lead">{e(shop['name'])} makes and packs {e(cat.lower())} in its own unit in {e((shop.get('address') or {}).get('town',''))}, {e(area)} District, Madhya Pradesh. {len(items)} product{'s' if len(items)!=1 else ''}{', in retail packs and bulk bags for businesses' if has_bulk else ''}.</p>
<div class="grid">{''.join(card(p, up) for p in items)}</div>
<div class="acts"><a class="btn btn-red" href="{up}">Order online</a><a class="btn btn-gold" href="{up}bulk-spices/">Bulk &amp; wholesale</a></div>
"""
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": cat, "url": url,
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{site}/products/{p['slug']}/", "name": p["name"]} for i, p in enumerate(items)]},
          crumbs_ld([("Home", "/"), ("Products", "/products/"), (cat, f"/products/{cs}/")], site), org_ld(shop)]
    return page(2, title, desc, url, body, ld, shop)

def all_products_page(by_cat, shop):
    site = shop["siteUrl"].rstrip("/"); up = "../"
    url = f"{site}/products/"
    area = (shop.get("address") or {}).get("district", "")
    total = sum(len(v) for v in by_cat.values())
    title = f"Spices & Masala Products – {shop['name']}, {area} (MP)"
    desc = f"All {shop['name']} products: " + ", ".join(by_cat) + f". Spice manufacturer in {area}, Madhya Pradesh – retail packs and bulk supply."
    secs = "".join(f'<h2><a href="{up}products/{slug(c)}/" style="text-decoration:none">{e(c)}</a></h2><div class="grid">' +
                   "".join(card(p, up).replace('href="../products/', 'href="../products/') for p in items) + "</div>" for c, items in by_cat.items())
    body = f"""
<nav class="crumbs"><a href="{up}">Home</a> › Products</nav>
<h1>Our products<small lang="hi">हमारे मसाले</small></h1>
<p class="lead">{total} products from our unit in {e((shop.get('address') or {}).get('town',''))}, {e(area)} District, Madhya Pradesh.</p>
{secs}
<div class="acts"><a class="btn btn-red" href="{up}">Order online</a><a class="btn btn-gold" href="{up}bulk-spices/">Bulk &amp; wholesale</a></div>
"""
    ld = [crumbs_ld([("Home", "/"), ("Products", "/products/")], site), org_ld(shop)]
    return page(1, title, desc, url, body, ld, shop)

def bulk_page(products, shop):
    site = shop["siteUrl"].rstrip("/"); up = "../"
    url = f"{site}/bulk-spices/"
    a = shop.get("address") or {}; area = a.get("district", "")
    bulk_items = [(p, [pk for pk in p["packs"] if (grams(pk[0]) or 0) >= 5000]) for p in products]
    bulk_items = [(p, b) for p, b in bulk_items if b]
    sizes = sorted({pk[0] for _, b in bulk_items for pk in b}, key=lambda s: grams(s) or 0) or ["5 kg", "10 kg", "30 kg", "50 kg"]
    title = f"Bulk Spices Manufacturer & Wholesale Supplier in {area}, MP | {shop['name']}"
    desc = f"Factory-direct bulk spices from {shop['name']}, {a.get('town','')}, {area} (MP): " + \
           ", ".join(p["name"] for p, _ in bulk_items[:5]) + f". Bags of {', '.join(sizes)}. GST invoice. Private label on request."
    rows = "".join(f"<tr><td><a href='{up}products/{p['slug']}/'>{e(p['name'])}</a><br><span lang='hi' style='color:#7b6a58;font-size:13px'>{e(p.get('hindi',''))}</span></td>"
                   f"<td>{' · '.join(e(pk[0]) + ' <b>' + inr(pk[1]) + '</b>' for pk in b)}</td></tr>" for p, b in bulk_items)
    quote = wa_link(shop, f"Namaste {shop['name']}, I want bulk price for spices.")
    tel = re.sub(r"\D", "", shop.get("phoneDisplay", "")) or shop["whatsapp"]; tel = ("91" + tel) if len(tel) == 10 else tel
    faqs = [
        ("Which bulk pack sizes do you supply?", f"Bulk bags of {', '.join(sizes)}. Larger or custom packing can be discussed."),
        ("Do you provide a GST invoice?", f"Yes. {shop['name']} is GST registered and supplies with a proper GST invoice."),
        ("Do you offer private label or custom packing?", "Yes. We can pack in your brand and pack size; contact us with your requirement."),
        ("Where is your factory?", address_line(shop) + "." + (" Google Maps: " + (shop.get("address") or {}).get("mapsUrl") if (shop.get("address") or {}).get("mapsUrl") else "")),
        ("How do I get a bulk price?", f"Send your requirement on WhatsApp or call {shop.get('phoneDisplay','')}. Our team will share pricing."),
    ]
    faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(ans)}</p></details>" for q, ans in faqs)
    body = f"""
<nav class="crumbs"><a href="{up}">Home</a> › Bulk spices</nav>
<h1>Bulk spices, direct from the manufacturer<small lang="hi">थोक मसाले – सीधे फैक्ट्री से</small></h1>
<p class="lead">{e(shop['name'])} processes and packs its spices in its own unit in {e(a.get('town',''))}, {e(area)} District, Madhya Pradesh. Retailers, kirana stores, wholesalers, distributors, hotels, restaurants, caterers and food businesses buy factory-direct, without middlemen.</p>
<p lang="hi">हम अपने मसाले खुद तैयार और पैक करते हैं, इसलिए आपको सीधे फैक्ट्री से थोक भाव में माल मिलता है। दुकानदार, होलसेलर, डिस्ट्रीब्यूटर, होटल-रेस्टोरेंट, कैटरर्स और फ़ूड बिज़नेस के लिए।</p>
<div class="acts"><a class="btn btn-wa" href="{e(quote)}">Get bulk price on WhatsApp</a><a class="btn btn-line" href="tel:+{e(tel)}">Call {e(shop.get('phoneDisplay',''))}</a></div>
<div class="box"><ul class="ticks">
  <li><b>Factory-direct pricing</b> – no middlemen, better margins for resellers.</li>
  <li><b>Bulk bags:</b> {', '.join(e(s) for s in sizes)}.</li>
  <li><b>Private label &amp; custom packing</b> – your brand, your pack size.</li>
  <li><b>Registered supplier:</b> {shop['_lic_short']}</li>
</ul></div>
{('<h2>Bulk price list</h2><table><thead><tr><th>Product</th><th>Bulk packs</th></tr></thead><tbody>' + rows + '</tbody></table>') if rows else ''}
<h2>Questions</h2>{faq_html}
"""
    ld = [{"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faqs]},
          crumbs_ld([("Home", "/"), ("Bulk spices", "/bulk-spices/")], site), org_ld(shop)]
    return page(1, title, desc, url, body, ld, shop)

# ---------------------------------------------------------------- build
def main():
    store, shop, products, source = load()
    if not shop.get("siteUrl"): shop["siteUrl"] = "https://bngfoods.in"
    site = shop["siteUrl"].rstrip("/")
    cats = []
    for p in products:
        if p["cat"] not in cats: cats.append(p["cat"])
    by_cat = {c: [p for p in products if p["cat"] == c] for c in cats}
    certs = store.get("certificates", [])
    shop["_cats"] = cats
    shop["_lic"] = " · ".join(f"{e(c.get('label') or c['name'])} {e(c['number'])}" for c in certs if c.get("number"))
    shop["_lic_short"] = ", ".join(f"{e(c.get('label') or c['name'])} {e(c['number'])}" for c in certs if c.get("number") and c.get("id") in ("fssai", "gst")) or "FSSAI and GST registered."
    # slugs must not clash with each other or with your own folders
    taken = {"images", "admin", "tools", "videos", "bulk-spices", "products", "brochure"}
    for c in cats:
        if slug(c) in taken: raise SystemExit(f"Category name '{c}' clashes with a folder name; rename it.")
        taken.add(slug(c))
    for p in products:
        if p["slug"] in taken: p["slug"] = p["slug"] + "-1"
        taken.add(p["slug"])

    old = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    if isinstance(old, list): old = {k: {} for k in old}
    made, state = [], {}
    def write(rel, text):                      # remember content hash so dates change only when a page changes
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()
        prev = old.get(rel, {})
        state[rel] = {"hash": h, "lastmod": prev.get("lastmod") if prev.get("hash") == h and prev.get("lastmod") else TODAY}
        path = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write(text)
    write("products/index.html", all_products_page(by_cat, shop))
    for c, items in by_cat.items():
        write(f"products/{slug(c)}/index.html", category_page(c, items, shop))
    for p in products:
        write(f"products/{p['slug']}/index.html", product_page(p, shop, by_cat))
    write("bulk-spices/index.html", bulk_page(products, shop))

    def lm(u):
        rel = (u.strip("/") + "/index.html") if u != "/" else None
        return state.get(rel, {}).get("lastmod", TODAY) if rel else TODAY
    urls = [("/", "1.0"), ("/products/", "0.8"), ("/bulk-spices/", "0.9")] + [(f"/products/{slug(c)}/", "0.8") for c in cats] + [(f"/products/{p['slug']}/", "0.7") for p in products] + [("/brochure/", "0.6")]
    home_lm = max([v["lastmod"] for v in state.values()] + ["2000-01-01"])
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          "".join(f"  <url><loc>{site}{u}</loc><lastmod>{home_lm if u in ('/', '/brochure/') else lm(u)}</lastmod><priority>{pr}</priority></url>\n" for u, pr in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /tools/\n\nSitemap: {site}/sitemap.xml\n")

    # remove pages of products that are no longer live (only pages this script made earlier)
    made = list(state)
    for rel in set(old) - set(made):
        path = os.path.join(ROOT, rel)
        if rel.endswith("index.html") and rel.startswith("products/") and os.path.exists(path):
            os.remove(path)
            try: os.rmdir(os.path.dirname(path))
            except OSError: pass
    with open(MANIFEST, "w") as f: json.dump(dict(sorted(state.items())), f, indent=1)
    print(f"Built {len(state)} files from {source}: {len(products)} products, {len(cats)} categories.")

if __name__ == "__main__":
    main()
