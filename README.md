# IPL 2026 SRH Tracker

A live dashboard for IPL 2026 with SRH highlighted. Auto-updates daily at 8 AM IST via GitHub Actions + cricketdata.org API.

---

## File Structure

```
srh-ipl-tracker/
├── index.html              ← The dashboard (reads data/ipl.json)
├── fetch_data.py           ← Python script that pulls live IPL data
├── netlify.toml            ← Netlify config
├── data/
│   └── ipl.json            ← Auto-updated daily by GitHub Actions
└── .github/
    └── workflows/
        └── update-data.yml ← The daily cron job
```

---

## Setup: Step by Step

### Step 1 — Get a Cricket API key (free)

1. Go to https://cricketdata.org
2. Click **Sign Up** → create a free account
3. After login, go to **Dashboard → API Key**
4. Copy your key (looks like `abc123-xxxx-xxxx-xxxx`)

---

### Step 2 — Create a GitHub repo

1. Go to https://github.com → click **New repository**
2. Name it `srh-ipl-tracker` (or anything you like)
3. Set it to **Public** → click **Create repository**
4. On your Mac terminal, run:

```bash
cd ~/Desktop
git clone https://github.com/YOUR_USERNAME/srh-ipl-tracker.git
# Copy all these files into that folder, then:
cd srh-ipl-tracker
git add .
git commit -m "Initial commit"
git push
```

---

### Step 3 — Add your API key as a GitHub Secret

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `CRICKET_API_KEY`
4. Value: paste your cricketdata.org key
5. Click **Add secret**

This keeps your key private — it never appears in your code.

---

### Step 4 — Deploy to Netlify (free)

1. Go to https://netlify.com → **Sign up with GitHub**
2. Click **Add new site** → **Import from Git**
3. Choose your `srh-ipl-tracker` repo
4. Leave build settings blank (no build command needed)
5. Set **Publish directory** to `.` (just a dot)
6. Click **Deploy site**

Netlify will give you a URL like `https://srh-ipl-tracker.netlify.app`

---

### Step 5 — Connect your custom domain (optional, ~₹800/yr)

1. Buy a domain on GoDaddy/Namecheap (e.g., `srhtracker.in`)
2. In Netlify → **Domain settings** → **Add custom domain**
3. Follow Netlify's DNS instructions (point your domain's nameservers to Netlify)
4. Netlify auto-provides free HTTPS (SSL certificate)

---

### Step 6 — Enable auto-deploy on data update

1. In Netlify → **Site settings** → **Build & deploy** → **Build hooks**
2. Click **Add build hook** → name it `ipl-data-update` → copy the URL
3. In GitHub repo → **Settings → Secrets** → Add new secret:
   - Name: `NETLIFY_BUILD_HOOK`
   - Value: the URL you just copied

4. Update `.github/workflows/update-data.yml` — add this step at the end of the job:

```yaml
      - name: Trigger Netlify rebuild
        run: curl -X POST ${{ secrets.NETLIFY_BUILD_HOOK }}
```

Now every time the Python script updates `data/ipl.json`, Netlify auto-redeploys.

---

## How It Works Daily

```
8:00 AM IST every day
       ↓
GitHub Actions runs fetch_data.py
       ↓
Script hits cricketdata.org API → gets points table + matches
       ↓
Writes updated data/ipl.json
       ↓
Git commits & pushes the file
       ↓
Triggers Netlify rebuild
       ↓
Your site shows today's data ✓
```

---

## Troubleshooting

- **Dashboard shows "Loading..." forever** → Check that `data/ipl.json` exists in your repo
- **GitHub Action fails** → Check that `CRICKET_API_KEY` secret is set correctly
- **API returns no IPL data** → IPL series ID in `fetch_data.py` may need updating; check cricketdata.org for the correct series ID for IPL 2026

---

## Sharing

Once live, share the Netlify URL with family:
`https://your-site.netlify.app`

Works on mobile too — fully responsive.
