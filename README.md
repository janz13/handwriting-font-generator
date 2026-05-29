# Handwriting Font Generator

Turn your handwriting into a real TrueType font (`.ttf`) from a scanned grid template.

**Live pipeline:** Upload a scanned template → Grid detection → Letter extraction → Vector tracing → Font compilation → Download your font.

---

## How It Works

1. **Print both templates** — alphabet (`template.png`, 7×9 grid) and symbols (`symbol_template.png`, 4×8 grid)
2. **Fill them in** with your handwriting using a dark pen (guide lines help position letters and symbols correctly)
3. **Scan or photograph** the completed sheets
4. **Upload both images** to the web app
5. **Download** either the individual font or the **combined** `MyHandwriting.ttf`

---

## Architecture

| Component | Tech | What It Does |
|-----------|------|--------------|
| Web UI | HTML5 + Vanilla JS | Drag-and-drop upload, progress, preview, download |
| Backend | Flask (Python) | HTTP API, pipeline orchestration |
| Grid Detection | OpenCV + NumPy | Finds grid lines, crops 62 cells |
| Vector Tracing | potrace | Converts bitmap letters to SVG outlines |
| Font Compiler | FontForge | Builds TrueType font from SVG glyphs |

---

## Local Development (Windows)

### Prerequisites

- Python 3.10+ (64-bit recommended)
- [potrace](http://potrace.sourceforge.net/) — download the Windows binary and place it on your `PATH`
- [FontForge](https://fontforge.org/en-US/downloads/) — install the Windows build

### Install

```bash
# 1. Clone the repo
cd handwriting-font-generator

# 2. Install Python dependencies
py -m pip install -r requirements.txt

# 3. Run the Flask dev server
py app.py
```

Open http://127.0.0.1:5000 in your browser.

> **Note:** If `import fontforge` fails in your system Python, `build_font.py` will automatically fall back to calling FontForge's bundled `ffpython.exe`.

---

## Online Deployment (Render.com)

The app is containerized and ready to deploy on any Docker-capable host. The instructions below use **Render** (free tier available).

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/janz13/handwriting-font-generator.git
git push -u origin main
```

### 2. Create a Render Account

Sign up at [render.com](https://render.com) (free, no credit card required for basic web services).

### 3. Deploy

1. In the Render Dashboard, click **New → Web Service**
2. Connect your GitHub repository
3. Render will auto-detect the `Dockerfile`
4. Set the following:
   - **Name:** `handwriting-font-generator`
   - **Region:** Choose one close to you
   - **Instance Type:** `Free` (or paid for faster builds)
   - **Branch:** `main`
5. Click **Create Web Service**

Render will build the Docker image (installs Debian packages `potrace` and `fontforge` automatically) and start the app on port `8000`.

### 4. Access Your Live App

Once the deploy finishes, Render gives you a public URL like:

```
https://handwriting-font-generator.onrender.com
```

Anyone with the link can upload a scanned template and generate a font.

> **Free tier note:** Render free instances spin down after 15 minutes of inactivity. The first request after idle may take ~30 seconds to wake up.

---

## Project Structure

```
.
├── app.py                     # Flask backend (API + web UI)
├── extract_letters.py         # OpenCV grid detection & cell extraction
├── build_font.py              # PNG → SVG → TTF pipeline (calls potrace + FontForge)
├── fontforge_assemble.py      # FontForge-only font builder (run via ffpython)
├── generate_template.py       # Generates blank A4 template PNG
├── make_synthetic_handwriting.py  # Test helper: draws fake handwriting
├── test_font.py               # Test helper: renders TTF preview
├── templates/
│   └── index.html             # Web frontend
├── static/
│   ├── style.css              # Modern responsive styling
│   └── app.js                 # Frontend logic (drag-drop, upload, preview)
├── Dockerfile                 # Production container image
├── render.yaml                # Render.com deployment config
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## System Dependencies Summary

These are **not** installable via `pip` and must be present on the host:

| Dependency | Linux install | Windows install |
|-----------|---------------|-----------------|
| potrace | `apt-get install potrace` | Download from [potrace.sourceforge.net](http://potrace.sourceforge.net/) |
| FontForge | `apt-get install fontforge python3-fontforge` | Download from [fontforge.org](https://fontforge.org/en-US/downloads/) |

The `Dockerfile` handles both on Debian automatically.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web UI (HTML page) |
| `POST` | `/api/upload/alphabet` | Upload alphabet template scan |
| `POST` | `/api/upload/symbols` | Upload symbols template scan |
| `GET` | `/api/download/<job_id>?mode=alphabet\|symbols` | Download generated `.ttf` |
| `GET` | `/api/preview/<job_id>?mode=alphabet\|symbols` | PNG preview of the font |
| `GET` | `/api/template` | Download blank alphabet template PNG |
| `GET` | `/api/template/symbols` | Download blank symbol template PNG |
| `POST` | `/api/combine` | Merge alphabet + symbol fonts into one TTF |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POTRACE_EXE` | `potrace` | Path to potrace binary |
| `FFPYTHON_EXE` | `ffpython` | Path to FontForge's Python interpreter |
| `FLASK_ENV` | `production` | Flask environment mode |

---

## License

MIT — feel free to use, modify, and deploy.
