"""
Handwriting Font Generator — Flask Web App
==========================================
Upload a scanned grid image, extract letters, trace to SVG, and compile a TTF.
"""
import os
import sys
import uuid
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Flask, request, render_template, send_file, jsonify, url_for
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = Path("uploads")
OUTPUT_FOLDER = Path("outputs")
EXTRACTED_FOLDER = Path("extracted_letters")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}

def _find_executable(name: str, windows_paths: list[str]) -> str:
    """Resolve an executable: env var > known Windows paths > PATH."""
    # 1. Explicit environment variable
    env = os.environ.get(f"{name.upper()}_EXE")
    if env and Path(env).is_file():
        return env

    # 2. Known Windows paths
    if sys.platform == "win32":
        for path in windows_paths:
            path = os.path.expandvars(path)
            if Path(path).is_file():
                return path

    # 3. Search PATH
    import shutil
    found = shutil.which(name)
    if found:
        return found

    # Return bare name and let the subprocess fail with a clear message
    return name


POTRACE_EXE = _find_executable(
    "potrace",
    windows_paths=[
        r"C:\Users\test\Downloads\potrace-1.16.win64\potrace-1.16.win64\potrace.exe",
        r"C:\Program Files\potrace\potrace.exe",
    ],
)

FFPYTHON_EXE = _find_executable(
    "ffpython",
    windows_paths=[
        r"C:\Program Files\FontForgeBuilds\bin\ffpython.exe",
        r"C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe",
    ],
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

# Ensure directories exist (needed for production WSGI servers)
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)
EXTRACTED_FOLDER.mkdir(exist_ok=True)


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _run_pipeline(image_path: Path, job_id: str, mode: str = "alphabet") -> dict:
    """
    Run the full extraction + font-build pipeline for a single upload.
    Returns a dict with success flag, ttf_path, message, and any errors.
    """
    result = {
        "success": False,
        "job_id": job_id,
        "ttf_path": None,
        "message": "",
        "errors": [],
        "extracted_count": 0,
        "mode": mode,
    }

    job_extracted = EXTRACTED_FOLDER / job_id
    job_output = OUTPUT_FOLDER / f"{job_id}.ttf"

    try:
        # --- 1. Extract letters ---
        from extract_letters import extract_letters
        count = extract_letters(str(image_path), str(job_extracted), mode=mode)

        # Count extracted PNGs (U+XXXX.png pattern excludes diagnostics)
        pngs = list(job_extracted.glob("U+*.png"))
        result["extracted_count"] = len(pngs)

        # --- 2. Build font ---
        build_cmd = [
            sys.executable, "build_font.py",
            "-i", str(job_extracted),
            "-o", str(job_output),
            "--potrace", POTRACE_EXE,
            "--normalize",
            "--mode", mode,
        ]
        p2 = subprocess.run(build_cmd, capture_output=True, text=True)
        if p2.returncode != 0:
            result["errors"].append(f"Font build failed: {p2.stderr}")
            return result

        if not job_output.exists():
            result["errors"].append("TTF file was not created.")
            return result

        result["success"] = True
        result["ttf_path"] = str(job_output)
        result["message"] = f"Generated {mode} font with {result['extracted_count']} glyphs."

    except Exception as exc:
        result["errors"].append(str(exc))

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


def _handle_upload(mode: str):
    """Shared upload handler for alphabet and symbols modes."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file in request."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename."}), 400

    if not _allowed(file.filename):
        return jsonify({"success": False, "error": "Unsupported file type."}), 400

    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
    upload_path = UPLOAD_FOLDER / f"{job_id}.{ext}"
    file.save(upload_path)

    result = _run_pipeline(upload_path, job_id, mode=mode)

    if result["success"]:
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": result["message"],
            "download_url": url_for("download_font", job_id=job_id, mode=mode, _external=True),
            "preview_url": url_for("preview_font", job_id=job_id, mode=mode, _external=True),
            "verify_url": url_for("verify_font", job_id=job_id, _external=True),
            "extracted_count": result["extracted_count"],
            "mode": mode,
        })
    else:
        if upload_path.exists():
            upload_path.unlink()
        extracted_dir = EXTRACTED_FOLDER / job_id
        if extracted_dir.exists():
            shutil.rmtree(extracted_dir)
        return jsonify({
            "success": False,
            "error": "; ".join(result["errors"]) if result["errors"] else "Unknown error",
        }), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Legacy endpoint — defaults to alphabet mode."""
    return _handle_upload("alphabet")


@app.route("/api/upload/alphabet", methods=["POST"])
def api_upload_alphabet():
    return _handle_upload("alphabet")


@app.route("/api/upload/symbols", methods=["POST"])
def api_upload_symbols():
    return _handle_upload("symbols")


@app.route("/api/download/<job_id>")
def download_font(job_id):
    mode = request.args.get("mode", "alphabet")
    ttf_path = OUTPUT_FOLDER / f"{job_id}.ttf"
    if not ttf_path.exists():
        return jsonify({"error": "Font not found."}), 404
    if job_id.endswith("_combined"):
        filename = "MyHandwriting_Combined.ttf"
    elif mode == "alphabet":
        filename = "MyHandwriting.ttf"
    else:
        filename = "MyHandwriting_Symbols.ttf"
    return send_file(
        ttf_path,
        mimetype="font/ttf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/preview/<job_id>")
def preview_font(job_id):
    """Render a labeled character-grid PNG preview of the generated font."""
    from PIL import Image, ImageDraw, ImageFont

    ttf_path = OUTPUT_FOLDER / f"{job_id}.ttf"
    if not ttf_path.exists():
        return jsonify({"error": "Font not found."}), 404

    mode = request.args.get("mode", "alphabet")

    try:
        font = ImageFont.truetype(str(ttf_path), 48)
        label_font = ImageFont.truetype(str(ttf_path), 20)
    except OSError:
        font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    if mode == "symbols":
        rows = [
            ("Punctuation", ".,;:'\"!?"),
            ("Math / Logic", "+-*/=<>`~"),
            ("Brackets", "()[]{}"),
            ("Currency / Misc", "@#$%^&_|\\"),
            ("Sample", "`~!@#$%^&*()_+-=[]{}|;':\",./<>?"),
        ]
    else:
        rows = [
            ("Uppercase", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            ("Lowercase", "abcdefghijklmnopqrstuvwxyz"),
            ("Digits", "0123456789"),
            ("Sample", "The quick brown fox jumps over the lazy dog"),
        ]

    W = 1400
    pad_x = 30
    pad_y = 30
    row_gap = 24
    label_gap = 12
    label_w = 160

    draw_tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    row_heights = []
    for _, text in rows:
        bbox = draw_tmp.textbbox((0, 0), text, font=font)
        row_heights.append(bbox[3] - bbox[1])

    H = sum(row_heights) + row_gap * (len(rows) - 1) + pad_y * 2 + 20

    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Subtle header line
    draw.line([(pad_x, pad_y - 10), (W - pad_x, pad_y - 10)], fill=(200, 200, 200), width=1)

    y = pad_y
    for (label, text), rh in zip(rows, row_heights):
        # Draw label in muted gray
        draw.text((pad_x, y), label + ":", font=label_font, fill=(120, 120, 120))
        # Draw characters
        draw.text((pad_x + label_w + label_gap, y), text, font=font, fill=(0, 0, 0))
        y += rh + row_gap

    preview_path = OUTPUT_FOLDER / f"{job_id}_preview.png"
    img.save(preview_path)
    return send_file(preview_path, mimetype="image/png")


@app.route("/api/verify/<job_id>")
def verify_font(job_id):
    """Serve the extraction verification montage so the user can confirm mapping."""
    verify_path = EXTRACTED_FOLDER / job_id / "_verification.png"
    if not verify_path.exists():
        return jsonify({"error": "Verification image not found."}), 404
    return send_file(verify_path, mimetype="image/png")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/template")
def download_template():
    """Serve the blank alphabet template.png for printing."""
    tpl = Path("template.png")
    if not tpl.exists():
        subprocess.run([sys.executable, "generate_template.py", str(tpl)], check=True)
    return send_file(tpl, mimetype="image/png", as_attachment=True, download_name="handwriting_template.png")


@app.route("/api/template/symbols")
def download_symbol_template():
    """Serve the blank symbol template.png for printing."""
    tpl = Path("symbol_template.png")
    if not tpl.exists():
        subprocess.run([sys.executable, "generate_symbol_template.py", str(tpl)], check=True)
    return send_file(tpl, mimetype="image/png", as_attachment=True, download_name="handwriting_symbol_template.png")


@app.route("/api/combine", methods=["POST"])
def api_combine():
    """Merge two previously generated TTFs (alphabet + symbols) into one."""
    data = request.get_json() or {}
    alpha_job = data.get("alpha_job_id")
    sym_job = data.get("sym_job_id")

    if not alpha_job or not sym_job:
        return jsonify({"success": False, "error": "Both alpha_job_id and sym_job_id are required."}), 400

    alpha_ttf = OUTPUT_FOLDER / f"{alpha_job}.ttf"
    sym_ttf = OUTPUT_FOLDER / f"{sym_job}.ttf"

    if not alpha_ttf.exists():
        return jsonify({"success": False, "error": "Alphabet font not found."}), 404
    if not sym_ttf.exists():
        return jsonify({"success": False, "error": "Symbols font not found."}), 404

    combined_id = f"{alpha_job}_{sym_job}_combined"
    combined_ttf = OUTPUT_FOLDER / f"{combined_id}.ttf"

    # Merge via FontForge — probe for a Python that can import fontforge
    combine_script = Path(__file__).parent / "combine_fonts.py"
    python_exe = None
    for candidate in [sys.executable, FFPYTHON_EXE, shutil.which("ffpython"), shutil.which("ffpython3"), "/usr/bin/python3"]:
        if not candidate:
            continue
        probe = subprocess.run(
            [candidate, "-c", "import fontforge; print('OK')"],
            capture_output=True, text=True
        )
        if probe.returncode == 0 and "OK" in probe.stdout:
            python_exe = candidate
            break
    if not python_exe:
        return jsonify({
            "success": False,
            "error": "No Python interpreter with fontforge found. Please install FontForge / python3-fontforge.",
        }), 500

    try:
        result = subprocess.run(
            [python_exe, str(combine_script), str(alpha_ttf), str(sym_ttf), str(combined_ttf)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": f"FontForge merge failed: {result.stderr}",
            }), 500
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({
        "success": True,
        "job_id": combined_id,
        "download_url": url_for("download_font", job_id=combined_id, _external=True),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
