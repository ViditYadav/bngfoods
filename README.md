# BNG Foods – Order Website

स्वाद की पहचान · The Real Taste of Bharat

Online ordering site for BNG Foods spices. Customers choose products and pack sizes, and the order is sent to BNG Foods on WhatsApp. Bulk / wholesale enquiries are sent the same way.

## Files

| File | What it is |
|---|---|
| `index.html` | The website (design and ordering logic). Usually no need to edit. |
| `store.json` | **All products, prices, pack sizes, contact details and order settings.** Edit this file to update the site. |
| `images/` | Logo, product pack photos, header background, gallery photos/videos. |
| `images/certificates/` | Photos or PDFs of your FSSAI, GST, Udyam and Gumasta certificates (page 1 only, personal details hidden). |

## Pages

The site has four pages, linked in the menu under the header (and in the footer):

| Page | Link | What it shows |
|---|---|---|
| Shop | `yoursite/` | Products, cart, bulk enquiry (as before) |
| Behind the Masala | `yoursite/#gallery` | Photos, videos and reels of your machines, grinding and packing |
| Certificates | `yoursite/#certificates` | FSSAI, GST, Udyam and Gumasta certificates with Verify links |
| Careers | `yoursite/#careers` | Job openings and an application form |

You can share these links directly, e.g. on WhatsApp or Instagram.
All forms (checkout, bulk enquiry, job application) ask for **Pincode** and **City**. Typing the pincode fills in the city automatically.

## Manage products from a Google Sheet (recommended)

Instead of editing `store.json`, you can manage everything from **BNG-Foods-Website-Sheet** (Google Sheets):
prices, pack sizes, new products, hiding products, WhatsApp number, phone, email and badges.

1. Upload `BNG-Foods-Website-Sheet.xlsx` to Google Drive → open it → **File → Save as Google Sheets**.
2. **File → Share → Publish to web** → choose the **Products** tab and **Comma-separated values (.csv)** → **Publish** → copy the link.
3. Do the same for the **Settings**, **Gallery** and **Careers** tabs.
4. Paste the links into `store.json`:
   `"sheetProductsCsv"`, `"sheetSettingsCsv"`, `"sheetGalleryCsv"`, `"sheetCareersCsv"` and upload `store.json` to GitHub.

From then on, edit the Google Sheet. The website picks up changes within about 5 minutes (Google refreshes published sheets every few minutes).
New product photos: upload them to the `images` folder on GitHub and type the file name in the sheet's Image column.
If the sheet can't be reached, the site uses the products in `store.json` as a backup.

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

**Contact, order settings and badges** – edit the `shop` section at the top:

- `whatsapp` – country code + number, no spaces or + (e.g. `917805003225`)
- `phoneDisplay`, `email`
- `minOrder` (in ₹, 0 = no minimum)
- `whatsappApiKey`, `orderEmailKey` – automatic order sending (see below)
- `instagram`, `youtube`, `facebook` – page links for the Behind the Masala page
- `badges` – the quality points shown under the header

After editing, check the file is valid JSON (every item separated by a comma, no comma after the last item). You can paste it into https://jsonlint.com to check.

## Behind the Masala (photos, videos, reels)

Add one entry per photo or video, in the sheet's **Gallery** tab or in `store.json` → `gallery`:

```json
{"src": "https://www.instagram.com/reel/XXXXXXX/", "title": "Grinding in our unit", "hindi": "हमारी यूनिट में पिसाई"}
```

`src` can be:
- a YouTube link, a YouTube **Shorts** link, an **Instagram reel / post** link or a **Facebook** video/reel link (the post must be public)
- a photo file name from the `images` folder (`machine-1.jpg`)
- a short video file (`.mp4`). Keep files under ~20 MB; for longer videos use YouTube.

Optional: `"cover": "machine-cover.jpg"` (photo shown before an Instagram/Facebook video plays), `"wide": true` (wide photo), `"show": false` (hide).
Photos / Videos / Reels filter buttons appear automatically.
Add your Instagram / YouTube / Facebook page links in the Settings tab (or `shop.instagram`, `shop.youtube`, `shop.facebook`) to show Follow buttons.

## Certificates

1. Take a clear photo or scan of each certificate (JPG). Before uploading, cover anything you don't want public, such as an Aadhaar or PAN number or home address.
2. Upload to `images/certificates/` with these names: `fssai.jpg`, `gst.jpg`, `udyam.jpg`, `gumasta.jpg`. (A PDF also works: change `file` in `store.json` to e.g. `images/certificates/gst.pdf`.)
3. Enter the numbers in the sheet's **Settings** tab (FSSAI Registration No., GSTIN, Udyam Registration No., Gumasta / Shop Act No.) or in `store.json` → `certificates` → `number`.

Until a photo is uploaded the card says "Certificate copy coming soon". The FSSAI number is shown on the shop page and all numbers in the footer.

## Careers

Add a row in the sheet's **Careers** tab (or `store.json` → `careers`) and set **Show on Website** to Yes. Set it to No when the job is filled.
Two example jobs (Machine Operator, Packing Staff) are already there, hidden.
Applications arrive the same way as orders (WhatsApp / email). Applicants are asked to send their resume on WhatsApp afterwards.

## Automatic order sending (no customer action needed)

When a customer taps **Place order**, the site can send the order to you automatically and show
"आपका ऑर्डर मिल गया है! BNG Foods टीम आपको कॉल करेगी". Set up one or both (free):

**WhatsApp to your own number – CallMeBot**
1. Go to https://www.callmebot.com/blog/free-api-whatsapp-messages/
2. Follow the steps: save their number in your phone and send them the activation message from your business WhatsApp.
3. You receive an **API key** on WhatsApp.
4. Put it in `store.json` → `"whatsappApiKey": "YOUR-KEY"`

**Email to your inbox – Web3Forms**
1. Go to https://web3forms.com and enter `Contact.bngfoods@gmail.com`.
2. You receive an **Access Key** by email.
3. Put it in `store.json` → `"orderEmailKey": "YOUR-KEY"`

If neither key is set (or sending fails), customers get a one-tap **Send on WhatsApp** button instead.

## Testing locally

Do not double-click `index.html` – products will not load from a file on disk. Upload the site, or run a local server in this folder:

```
python3 -m http.server 8000
```

then open http://localhost:8000

## Hosting

Works on any static host: GitHub Pages, Netlify, Cloudflare Pages, or any web hosting.
