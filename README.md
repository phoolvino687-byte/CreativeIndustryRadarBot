# 📡 Creative Radar

> **Personal Intelligence Platform for Creative Professionals**  
> Automated ingestion, AI summarization, multi-dimensional ranking, Telegram morning briefings, urgent flash alerts, and a dark-first interactive web dashboard.

---

## 🎯 Platform Overview

**Creative Radar** is an autonomous intelligence pipeline designed for filmmakers, video editors, 3D artists, colorists, photographers, and graphic designers. It continuously scans verified RSS/Atom feeds, filters signal from noise, normalizes updates, prioritizes primary manufacturer release notes, generates structured 3-part intelligence summaries, and publishes:

1. **Responsive Web Dashboard**: Real-time filtering, search, bookmarks, read states, camera firmware alerts, software releases, and source health diagnostics.
2. **Telegram Daily Briefing**: Sent at **03:30 UTC (09:00 Asia/Kolkata / IST)** featuring top verified stories and actionable takeaways.
3. **Immediate Urgent Alerts**: Automatic dispatch for critical firmware security patches, zero-day fixes, and limited-time deals.

---

## 💸 Zero-Cost Infrastructure Architecture

Creative Radar is designed to run indefinitely at **$0.00 recurring cost**:

| Component | Technology | Cost Tier |
| :--- | :--- | :--- |
| **Ingestion Engine** | Python 3.12 (Requests, XML ElementTree) | Free / Open Source |
| **AI Summarizer** | Google Gemini 2.5 Flash API (Strict JSON mode) | Free Tier ($0/mo) |
| **AI Fallback** | Heuristic Extractive Summarizer | Built-in ($0/mo) |
| **Automation & Scheduling** | GitHub Actions (`30 3 * * *`) | Free Tier (Public/Private repos) |
| **Dashboard Hosting** | GitHub Pages (Static HTML/CSS/Vanilla JS) | Free Unlimited Hosting |
| **Notifications** | Telegram Bot API | Free Unlimited Messaging |

> [!NOTE]
> **No Paid API Lock-In**: If `GEMINI_API_KEY` is not provided or if Google API free-tier quotas (HTTP 429) are reached, the platform **automatically and gracefully falls back** to its built-in rule-based extractive summarizer. It will never halt or fail.

---

## 🏷️ Tracked Creative Categories

1. **`adobe`**: Adobe Creative Cloud, Premiere Pro, After Effects, Photoshop, Lightroom, Substance 3D.
2. **`davinci-blackmagic`**: DaVinci Resolve Studio, Blackmagic cameras, Fairlight audio, Fusion VFX.
3. **`cameras-lenses-firmware`**: Sony, Canon, Nikon, Fujifilm, Lumix, cinema cameras, lens releases, firmware advisories.
4. **`motion-vfx-blender`**: Blender Foundation releases, geometry nodes, EEVEE Next, Unreal Engine, 3D pipelines.
5. **`design-fonts-plugins`**: Typography releases, variable fonts, Figma tools, vector design systems.
6. **`ai-tools-offers`**: OpenAI, Sora, Diffusion models, Hugging Face open weights, verified tool discounts.
7. **`photography-filmmaking-freelance`**: Cinematography setups, indie grants, client contract strategies, business craft.

---

## 🛠️ Windows 11 Beginner Setup Guide

### 1. Requirements
- Windows 11 PC
- Python 3.12+ installed (installer includes `py` launcher)
- Git for Windows (optional for local git commands)

### 2. Quick Start Using One-Click Batch Files
If you prefer not typing commands in terminals, simply double-click the included batch files:
- **`run.bat`**: Runs the live intelligence pipeline.
- **`dry_run.bat`**: Runs a full test ingestion without sending live Telegram messages.
- **`serve.bat`**: Launches a local web server and opens the dashboard in your browser (`http://localhost:8000`).
- **`test.bat`**: Runs the 35 automated verification tests.

### 3. Command-Line Setup (PowerShell)
Open PowerShell in the `CreativeIndustryRadarBot` folder:

```powershell
# 1. Install dependencies
py -3.12 -m pip install -r requirements.txt

# 2. Run the test suite
py -3.12 -m pytest -v

# 3. Initialize with realistic demo dataset (optional)
py -3.12 main.py --load-demo

# 4. Preview the dashboard locally
py -3.12 -m http.server 8000
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## 🔑 Environment Configuration (`.env`)

Copy `.env.example` to `.env` in the root folder:

```powershell
Copy-Item .env.example .env
```

Edit `.env` using Notepad:
```ini
# Optional: Google Gemini API key for structured 3-part summaries
GEMINI_API_KEY=

# Optional: Telegram bot token and chat ID for mobile briefings
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Settings
DRY_RUN=false
RADAR_ENV=development
```

---

## 🤖 Telegram Bot Setup (Free in 2 Minutes)

### Step 1: Create Your Bot
1. Open Telegram on your phone or desktop.
2. Search for `@BotFather` (verified bot with blue checkmark).
3. Send `/newbot`.
4. Follow the prompts to name your bot (e.g., `My Creative Radar`).
5. Copy the **HTTP API Token** provided (format: `123456789:ABCdefGhI_klmNOPqrStUvwXyz`). This is your `TELEGRAM_BOT_TOKEN`.

### Step 2: Get Your Chat ID
1. Search for `@userinfobot` on Telegram.
2. Click **Start** or send any message.
3. It will reply with your numeric `Id` (e.g., `987654321`). This is your `TELEGRAM_CHAT_ID`.
4. Send `/start` to your **new bot** created in Step 1 so it has permission to message you.

### Step 3: Test Your Connection
Run the test command in PowerShell:
```powershell
py -3.12 main.py --test-telegram
```
You will instantly receive a test dispatch on Telegram!

---

## 🧠 Google Gemini API Key Setup (Free Tier)

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google account.
3. Click **"Create API Key"**.
4. Copy the generated key (starts with `AIzaSy...`).
5. Paste into `GEMINI_API_KEY` in `.env` (locally) and GitHub Secrets (for automation).

---

## 🚀 GitHub Actions & GitHub Pages Deployment

### 1. Push to GitHub
Create a new GitHub repository called `CreativeIndustryRadarBot`. In PowerShell:

```powershell
git init
git add .
git commit -m "feat: complete creative radar platform"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/CreativeIndustryRadarBot.git
git push -u origin main
```

### 2. Configure GitHub Secrets
In your GitHub repository:
1. Navigate to **Settings** > **Secrets and variables** > **Actions**.
2. Click **"New repository secret"** and add each secret:

| Secret Name | Required? | Value Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Optional | Free Google Gemini key from Google AI Studio. |
| `TELEGRAM_BOT_TOKEN` | Optional | Bot token received from `@BotFather`. |
| `TELEGRAM_CHAT_ID` | Optional | Numeric Telegram user or channel ID. |

### 3. Enable GitHub Pages
1. Go to **Settings** > **Pages**.
2. Under **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: **`main`** / Folder: **`/ (root)`**
3. Click **Save**. Your public dashboard will be live at:
   `https://<YOUR_USERNAME>.github.io/CreativeIndustryRadarBot/`

### 4. Triggering Scheduled or Manual Runs
- **Automated**: Runs every morning at **03:30 UTC (09:00 Asia/Kolkata / IST)**.
- **Manual**: Go to **Actions** > **Creative Radar Intelligence Pipeline** > **Run workflow**.

---

## 🛡️ Security & Privacy Guardrails

1. **Zero Secret Leakage**:
   - All published JSON files (`data/radar.json`, `data/health.json`) are scanned with an automated safety audit before writing to disk.
   - A runtime `SecretFilter` strips secret tokens from all logging streams.
   - Test suite includes `test_security.py` verifying no tokens appear in public code, JSON, or HTML.
2. **Untrusted Data Sanitization**:
   - External RSS contents are isolated within `<untrusted_content>` delimiter tags to prevent prompt injection.
   - HTML descriptions are sanitized and entity-decoded to prevent cross-site scripting (XSS).
3. **Atomic File Persistence**:
   - Data writes use swap files (`.tmp`) and `os.replace` to prevent corrupted or half-written JSON files.
4. **Anti-Duplication**:
   - Dispatched alert IDs are tracked in `data/state.json` to prevent repetitive Telegram alerts across runs.

---

## 🩺 Source Registry (`config/sources.json`)

You can edit or expand sources anytime in `config/sources.json`:

```json
{
  "id": "cined-gear",
  "name": "CineD Gear & Firmware",
  "category": "cameras-lenses-firmware",
  "url": "https://www.cined.com/feed/",
  "homepage_url": "https://www.cined.com/",
  "type": "rss",
  "trust_level": "reputable",
  "enabled": true
}
```

- **`trust_level`**:
  - `official`: Direct manufacturer releases (priority weight: 10/10).
  - `reputable`: Established industry journalism (priority weight: 7.5/10).
  - `community`: Forums, rumors, community setups (priority weight: 5.0/10).
- **`enabled`**: Set to `false` to pause monitoring a feed without deleting it.

---

## ❓ Troubleshooting

| Issue | Resolution |
| :--- | :--- |
| **`python: command not found` on Windows** | Use `py -3.12` or run `run.bat` / `test.bat` directly. Windows 11 execution aliases can be adjusted in *Settings > Apps > Advanced app settings > App execution aliases*. |
| **Telegram message not arriving** | Ensure you have sent at least one `/start` message to your bot on Telegram so it is permitted to initiate a conversation with you. Verify token and chat ID with `py -3.12 main.py --test-telegram`. |
| **Gemini Quota 429 warning** | Normal on high-volume days under Google free tier. Creative Radar automatically switches to extractive summaries without failing the pipeline. |
| **Feed reports HTTP 403 or 404** | Check the **Source Health** button in the dashboard or review `data/health.json` to inspect feed status codes and latencies. |

---

## 📄 License
MIT License. Open source and free for personal and commercial use.
