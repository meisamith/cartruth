# CarTruth 🚗

### India's Honest Car Ownership Guide — Built for Non-Car People

> You're about to spend ₹5–25 lakhs on a car. CarDekho shows you specs. CarWale shows you prices.
> **CarTruth shows you what actually happens after you buy it.**

---

## 🔴 The Problem

Most Indians buying a car — new or secondhand — know nothing about cars. They rely on dealer pitches, YouTube reviewers with sponsorships, and that one uncle who bought a Honda City in 2014.

Nobody tells you:
- That the "claimed 22 kmpl" actually gives you 14 in city traffic
- That a single authorised service visit at 40,000 km costs ₹12,000+
- That the model you're buying has a known AC compressor failure that hits at 3 years
- Whether that ₹6.5 lakh used car is priced fairly — or you're getting ripped off

**CarTruth fixes this.** Search any Indian car model and get the real, unfiltered picture of owning it.

---

## 🟢 Live App

**🌐 [thecartruth.in](https://web-production-dfc9.up.railway.app)**

Mobile-first PWA — install it on your phone's home screen for instant access.

---

## ✨ Features

### 🔍 Car Search
Search any Indian car model — Maruti Swift to Toyota Fortuner. Autocomplete suggestions for 50+ popular models.

### 📊 Full Car Report (7 sections)
Every car gets a detailed report with:

| Section | What It Shows |
|---------|--------------|
| **Mileage Reality Check** | Company claimed vs actual owner-reported mileage, with % gap warning |
| **True Cost of Ownership** | Insurance, service costs at 10k/20k/40k km, tyre replacement, yearly total |
| **Showroom vs Outside** | How much you save going to a local mechanic vs authorised service centre |
| **Top 5 Common Problems** | Real owner-reported issues with severity ratings (low/medium/high) |
| **Before You Buy Checklist** | Separate checklists for new car and used car buyers |
| **Emergency Guide** | Step-by-step help for: battery dead, flat tyre, breakdown, engine overheating |
| **Honest Verdict** | Who should buy this car, who should avoid it, and a brutally honest one-line summary |

### ⚔️ Compare Mode
Pick two cars. See them side by side across every metric. Get a personalised winner recommendation based on your priorities and a 5-year cost difference calculation.

### 🔧 Used Car Wizard
Answer 10 simple inspection questions about any used car → get a clear YES / NO / RISKY verdict with detailed reasoning. No mechanical knowledge needed.

### 💰 Budget Calculator
Enter your budget, city, and how you'll use the car (daily commute / highway / family weekends) → get the top 3 cars that fit your real life, not just your price range.

### 📋 Fair Price Checker
Is that used car listing on OLX priced fairly? Enter the model, year, kilometres driven, and condition → get a fair price range and whether the asking price is a deal, fair, or overpriced.

### 📱 PWA (Progressive Web App)
Installable on your phone home screen. Works offline for cached car reports. Fast, native-app-like experience.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11 + Flask |
| **AI Engine** | Claude API (Anthropic) — Haiku model for speed + cost efficiency |
| **Database** | PostgreSQL on Railway (with intelligent caching — each car model is generated once, then cached forever, keeping API costs near zero) |
| **Frontend** | Vanilla JavaScript + Jinja2 templates |
| **Styling** | Custom CSS — mobile-first, dark theme (#0f0f0f + gold #e8b84b), no frameworks |
| **Animations** | GSAP (GreenSock) for smooth scroll and entrance animations |
| **Deployment** | Railway (auto-deploy from GitHub) |
| **PWA** | Service Worker + Web App Manifest for installability |

---

## 🧠 How the AI Caching Works

This is the core architecture decision that makes CarTruth viable:

```
User searches "Maruti Swift"
        ↓
Check PostgreSQL cache → Found? → Return instantly (0 API cost)
        ↓ (Not found)
Call Claude API → Generate full report → Save to cache → Return
        ↓
Next user searches "Maruti Swift" → Cache hit → Instant, free
```

**Result:** The Claude API is called only ONCE per car model, ever. After that, it's pure database reads. This means:
- 100 users searching the same car = 1 API call, not 100
- Growing user base doesn't mean growing API costs
- Response time drops from ~8 seconds (API) to ~200ms (cache)

---

## 📸 Screenshots

| Home Page | Car Report | Compare Mode |
|-----------|-----------|--------------|
| Dark theme, gold accents, search bar with autocomplete | 7-section detailed report with severity badges | Side-by-side comparison with personalised winner |

---

## 🚀 Run Locally

```bash
# Clone the repo
git clone https://github.com/meisamith/cartruth.git
cd cartruth

# Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY and DATABASE_URL in .env

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
# Open http://localhost:5000
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key ([console.anthropic.com](https://console.anthropic.com)) |
| `DATABASE_URL` | PostgreSQL connection string (Railway provides this automatically) |
| `FLASK_SECRET_KEY` | Any random secret string for session security |

---

## 📁 Project Structure

```
cartruth/
├── app.py                  # Flask routes and app entry point
├── config.py               # Environment variables and config
├── requirements.txt        # Python dependencies
├── Procfile                # Railway deployment config
├── api/
│   ├── claude_client.py    # Claude API integration and prompt engineering
│   └── car_data.py         # Caching logic + car suggestions
├── database/
│   └── db.py               # PostgreSQL connection and queries
├── templates/
│   ├── base.html           # Base template with nav, footer, PWA meta tags
│   ├── index.html          # Home page with search and popular cars
│   ├── report.html         # Full 7-section car report
│   ├── compare.html        # Side-by-side comparison view
│   ├── wizard.html         # Used car inspection wizard
│   ├── budget.html         # Budget calculator
│   └── fair_price.html     # Fair price checker
├── static/
│   ├── css/style.css       # Mobile-first dark theme stylesheet
│   ├── js/app.js           # Client-side interactivity
│   ├── manifest.json       # PWA manifest
│   ├── sw.js               # Service worker for offline support
│   └── icons/              # PWA icons (192px and 512px)
```

---

## 🎯 What Makes This Different from CarDekho / CarWale

| | CarDekho / CarWale | CarTruth |
|---|---|---|
| **Mileage** | Shows company claimed number | Shows claimed vs REAL owner-reported |
| **Cost** | Shows ex-showroom price | Shows total yearly ownership cost |
| **Problems** | Hidden in user reviews | Top 5 listed with severity ratings |
| **Used Cars** | Lists dealer inventory | Tells you if the price is fair + inspection checklist |
| **Emergency** | Nothing | Step-by-step guide for breakdowns |
| **Tone** | Showroom marketing language | Brutally honest, like a friend who knows cars |

---

## 🗺️ Roadmap

- [ ] WhatsApp share card — share any car report as a rich preview link
- [ ] Regional language support — Hindi, Kannada, Tamil, Telugu
- [ ] User-submitted real mileage data — crowdsourced accuracy
- [ ] Dealer price negotiation tips per model
- [ ] Insurance comparison calculator
- [ ] EMI vs cash analysis

---

## 👤 Built By

**Amith Choudhary**
2nd Year CSBS @ JSS Science and Technology University, Mysore

- GitHub: [@meisamith](https://github.com/meisamith)
- Project: Built end-to-end using Claude Code in 7 days

---

## 📄 License

MIT — use it, fork it, improve it.

---

*CarTruth is not affiliated with any car manufacturer or dealer. All data is AI-generated based on aggregated owner experiences and should be used as a general guide, not as a substitute for professional mechanical inspection.*
