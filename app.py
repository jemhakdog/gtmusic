"""Local dev server for Cernodile's Growtopia Music Simulator.

Serves GTMusicSim/ as the web root so its relative paths (./Player.js,
./assets/*.png, ./notes/*.wav) resolve. Missing assets 404 - the page draws
placeholders for those.
"""

from pathlib import Path

from flask import Flask, send_from_directory

WEB_ROOT = Path(__file__).parent / "GTMusicSim"

app = Flask(__name__)


@app.get("/")
def index():
    return send_from_directory(WEB_ROOT, "index.html")


@app.get("/<path:filename>")
def files(filename):
    return send_from_directory(WEB_ROOT, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
