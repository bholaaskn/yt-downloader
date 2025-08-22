import os, re, tempfile, threading
from datetime import datetime
from flask import Flask, request, render_template_string, send_file, abort
from yt_dlp import YoutubeDL

# Try to supply ffmpeg on free hosts (Render) via imageio-ffmpeg binary
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None  # yt-dlp will try PATH

app = Flask(__name__)

SAFE_NAME = re.compile(r"[^A-Za-z0-9_\-\.]+")

def sanitize_filename(name: str) -> str:
    name = SAFE_NAME.sub("_", name).strip("._")
    return name or f"video_{int(datetime.utcnow().timestamp())}"

@app.route("/", methods=["GET"])
def index():
    # Read index.html from repo
    with open("index.html", "r", encoding="utf-8") as f:
        return render_template_string(f.read())

def format_selector(quality: str) -> str:
    if quality == "mp3":
        return "bestaudio/best"
    if quality == "best":
        return "bestvideo+bestaudio/best"
    try:
        h = int(quality)
    except Exception:
        h = 2160
    return f"bestvideo[height>={h}]+bestaudio/best"

@app.route("/download", methods=["POST"])
def download():
    url = (request.form.get("url") or "").strip()
    quality = (request.form.get("quality") or "2160").strip()
    ext = (request.form.get("ext") or "mp4").strip().lower()
    if not url:
        abort(400, "Missing URL")

    tmpdir = tempfile.mkdtemp(prefix="yt4k_")
    outtmpl = os.path.join(tmpdir, "%(title).200B.%(id)s.%(ext)s")

    # 👇 Here we added cookies.txt support
    ydl_opts = {
        "outtmpl": outtmpl,
        "merge_output_format": ext if quality != "mp3" else None,
        "format": format_selector(quality),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cookies": "cookies.txt",   # 👈 use cookies file
        "ffmpeg_location": FFMPEG_PATH,
    }

    # Add mp3 postprocessor when needed
    if quality == "mp3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        abort(400, f"Failed to download: {e}")

    # Find largest resulting file in tmpdir
    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
    if not files:
        abort(500, "No output file found.")
    filepath = max(files, key=lambda p: os.path.getsize(p))
    filename = os.path.basename(filepath)

    # Background cleanup
    def cleanup(path):
        import time, shutil
        time.sleep(30)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
    threading.Thread(target=cleanup, args=(tmpdir,), daemon=True).start()

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream",
        conditional=True
    )

@app.route("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    # Render provides PORT env var
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
