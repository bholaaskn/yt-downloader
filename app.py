import os
from flask import Flask, render_template, request, send_file, abort
import yt_dlp

app = Flask(__name__)

# Path to ffmpeg (set to None to use PATH; set to "/usr/bin/ffmpeg" if you know it exists)
FFMPEG_PATH = os.environ.get("FFMPEG_PATH")  # fallback to PATH if not set

def format_selector(quality: str) -> str:
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
    # Ensure your index.html is in templates/index.html
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download_video():
    url = request.form.get("url")
    quality = request.form.get("quality")
    ext = request.form.get("ext", "mp4")

    if not url or not quality:
        abort(400, description="Missing url or quality")

    # Ensure downloads folder exists and use absolute paths
    download_dir = os.path.abspath("downloads")
    os.makedirs(download_dir, exist_ok=True)
    outtmpl = os.path.join(download_dir, "%(title)s.%(ext)s")

    # Build yt-dlp options safely
    ydl_opts = {
        "outtmpl": outtmpl,
        "merge_output_format": None if quality == "mp3" else ext,
        "format": format_selector(quality),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Only pass cookies if the file exists
        **({"cookies": "cookies.txt"} if os.path.exists("cookies.txt") else {}),
        # Only set ffmpeg_location if provided
        **({"ffmpeg_location": FFMPEG_PATH} if FFMPEG_PATH else {}),
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

        # Adjust filename for mp3 extraction
        if quality == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        # Ensure file exists before sending
        if not os.path.exists(filename):
            abort(500, description="Downloaded file not found")

        # Optional: set a safe download name
        safe_title = info.get("title", "video")
        download_name = f"{safe_title}.mp3" if quality == "mp3" else f"{safe_title}.{ext}"

        return send_file(filename, as_attachment=True, download_name=download_name, max_age=0)

    except yt_dlp.utils.DownloadError as e:
        # Errors from yt-dlp (e.g., invalid URL, private video, bad cookies)
        return (f"Error during download: {str(e)}", 400)
    except FileNotFoundError as e:
        # Missing cookies.txt or ffmpeg not found when required
        return (f"File not found: {str(e)}", 500)
    except Exception as e:
        # Generic fallback
        return (f"Error: {str(e)}", 500)

if __name__ == "__main__":
    # For local dev; in production use gunicorn
    app.run(host="0.0.0.0", port=5000)
