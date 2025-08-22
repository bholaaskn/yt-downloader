import os
from flask import Flask, render_template, request, send_file
import yt_dlp

app = Flask(__name__)

# Path to ffmpeg (Render usually installs it globally)
FFMPEG_PATH = "/usr/bin/ffmpeg"


def format_selector(quality):
    """
    Returns the format string for yt-dlp based on quality.
    """
    if quality == "mp3":
        return "bestaudio/best"
    elif quality == "720p":
        return "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif quality == "1080p":
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    elif quality == "4k":
        return "bestvideo[height<=2160]+bestaudio/best[height<=2160]"
    else:
        return "best"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download_video():
    url = request.form["url"]
    quality = request.form["quality"]
    ext = request.form.get("ext", "mp4")

    # Save files inside downloads/ folder
    outtmpl = f"downloads/%(title)s.%(ext)s"

    # yt-dlp options
    ydl_opts = {
        "outtmpl": outtmpl,
        "merge_output_format": ext if quality != "mp3" else None,
        "format": format_selector(quality),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cookies": "cookies.txt",   # 👈 must match filename in repo
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }] if quality == "mp3" else [],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if quality == "mp3":
                filename = filename.rsplit(".", 1)[0] + ".mp3"

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return f"❌ Error: {str(e)}"


if __name__ == "__main__":
    # Ensure downloads folder exists
    os.makedirs("downloads", exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
