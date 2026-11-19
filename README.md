# BNG Foods – Order Website

स्वाद की पहचान · The Real Taste of Bharat

Online ordering site for BNG Foods spices. Customers choose products and pack sizes, and the order is sent to BNG Foods on WhatsApp. Bulk / wholesale enquiries are sent the same way.

## Files

| File | What it is |
|---|---|
| `index.html` | The website (design and ordering logic). Usually no need to edit. |
| `store.json` | **All products, prices, pack sizes, contact details and shipping settings.** Edit this file to update the site. |
| `images/` | Logo, product pack photos and header background. |

## Common changes (edit `store.json`)

**Change a price** – find the product and change the number after the pack size:

```json
["500 g", 180, "images/turmeric-500.jpg"]
```

**Add a pack size** – add another line inside `packs`:

```json
["1 kg", 340, "images/turmeric-1kg.jpg"]
```

The photo is optional. Without it, a coloured block is shown.

**Add a new product** – copy an existing product block and change the values:

```json
{"id": "garam-masala", "cat": "Spice Powders",
 "keywords": ["garam masala", "masala", "गरम मसाला"],
 "name": "Garam Masala", "hindi": "गरम मसाला",
 "desc": "Our signature blend of whole spices.", "color": "#5c3a21",
 "packs": [["100 g", 60, "images/garam-100.jpg"], ["200 g", 110, "images/garam-200.jpg"]]}
```

- `id` must be unique, lowercase, with no spaces.
- `cat` is the category. A new category name automatically creates a new tab.
- `keywords` are extra search words (Hindi, English, Hinglish).
- Put new photos in the `images` folder.

**Contact, shipping and badges** – edit the `shop` section at the top:

- `whatsapp` – country code + number, no spaces or + (e.g. `917805003225`)
- `phoneDisplay`, `email`
- `shippingFee`, `freeShippingAbove`, `minOrder` (in ₹)
- `badges` – the quality points shown under the header

After editing, check the file is valid JSON (every item separated by a comma, no comma after the last item). You can paste it into https://jsonlint.com to check.

## Testing locally

Do not double-click `index.html` – products will not load from a file on disk. Upload the site, or run a local server in this folder:

```
python3 -m http.server 8000
```

then open http://localhost:8000

## Hosting

Works on any static host: GitHub Pages, Netlify, Cloudflare Pages, or any web hosting.
