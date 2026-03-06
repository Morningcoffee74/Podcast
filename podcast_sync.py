#!/usr/bin/env python3
"""
podcast_sync.py
Reads a YouTube playlist, downloads new audio, updates RSS, and pushes to GitHub.

Required env vars:
  PLAYLIST_URL  - YouTube playlist URL
  FEED_BASE_URL - e.g. https://raw.githubusercontent.com/Morningcoffee74/Podcast/main
  FEED_TOKEN    - secret token for private feed URL

Optional env vars:
  REPO_PATH     - path to repo (default: directory containing this script)
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_PATH     = Path(os.environ.get("REPO_PATH", Path(__file__).parent))
PLAYLIST_URL  = os.environ["PLAYLIST_URL"]
FEED_BASE_URL = os.environ["FEED_BASE_URL"]
FEED_TOKEN    = os.environ["FEED_TOKEN"]
YTDLP         = "/opt/homebrew/bin/yt-dlp"
PYTHON        = sys.executable

STATE_FILE    = REPO_PATH / "downloaded.json"
AUDIO_DIR     = REPO_PATH / "audio"
LOG_PATH      = Path.home() / "Library" / "Logs" / "podcast_sync.log"

# ---------------------------------------------------------------------------
# Logging: file + stdout
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_title(title: str) -> str:
    safe = re.sub(r"[^\w\-.]", "_", title)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    log.info("State saved (%d entries)", len(state))


def get_playlist_entries() -> list[dict]:
    log.info("Fetching playlist: %s", PLAYLIST_URL)
    result = subprocess.run(
        [YTDLP, "--flat-playlist", "--dump-json", "--no-warnings", PLAYLIST_URL],
        capture_output=True,
        text=True,
        check=True,
    )
    entries = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    log.info("Found %d playlist entries", len(entries))
    return entries


def get_video_metadata(video_id: str) -> dict:
    url = f"https://www.youtube.com/watch?v={video_id}"
    result = subprocess.run(
        [YTDLP, "--dump-json", "--no-warnings", "--no-playlist", url],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def download_video(video_id: str, title: str) -> tuple[str, int, int, str]:
    """Download audio and return (filename, duration_secs, file_size_bytes, channel_name)."""
    filename = sanitize_title(title)[:80] + "_" + video_id + ".m4a"
    output_path = AUDIO_DIR / filename
    url = f"https://www.youtube.com/watch?v={video_id}"

    log.info("Downloading: %s → %s", title, filename)
    subprocess.run(
        [
            YTDLP,
            "--cookies-from-browser", "firefox",
            "-x",
            "--audio-format", "m4a",
            "--audio-quality", "0",
            "--no-playlist",
            "-o", str(output_path),
            url,
        ],
        check=True,
        cwd=REPO_PATH,
    )

    file_size = output_path.stat().st_size
    log.info("Downloaded %s (%.1f MB)", filename, file_size / 1_048_576)

    # Get duration and channel from metadata
    meta = get_video_metadata(video_id)
    duration = int(meta.get("duration") or 0)
    channel_name = meta.get("channel") or meta.get("uploader") or "Podcast"

    return filename, duration, file_size, channel_name


def update_rss(filename: str, title: str, channel_name: str, duration: int, file_size: int) -> None:
    env = {
        **os.environ,
        "FEED_BASE_URL": FEED_BASE_URL,
        "FEED_TOKEN":    FEED_TOKEN,
        "AUDIO_FILE":    filename,
        "TITLE":         title,
        "CHANNEL_NAME":  channel_name,
        "DURATION":      str(duration),
        "FILE_SIZE":     str(file_size),
    }
    subprocess.run(
        [PYTHON, str(REPO_PATH / "generate_rss.py")],
        check=True,
        cwd=REPO_PATH,
        env=env,
    )
    log.info("RSS updated for: %s", title)


def git_commit_and_push(new_files: list[str], titles: list[str]) -> None:
    commit_msg = "Add episode: " + titles[0] if len(titles) == 1 else "Add episodes: " + ", ".join(titles)

    files_to_stage = ["feed.xml", "downloaded.json"] + new_files
    subprocess.run(["git", "add"] + files_to_stage, check=True, cwd=REPO_PATH)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=REPO_PATH)
    subprocess.run(["git", "push"], check=True, cwd=REPO_PATH)
    log.info("Pushed to GitHub: %s", commit_msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== podcast_sync start ===")

    state = load_state()
    entries = get_playlist_entries()

    new_files: list[str] = []
    new_titles: list[str] = []

    for entry in entries:
        video_id = entry.get("id")
        title    = entry.get("title") or video_id

        if not video_id:
            log.warning("Entry without id, skipping: %s", entry)
            continue

        if video_id in state:
            log.debug("Already downloaded: %s", video_id)
            continue

        try:
            filename, duration, file_size, channel_name = download_video(video_id, title)
            update_rss(filename, title, channel_name, duration, file_size)

            state[video_id] = {
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "title":         title,
                "filename":      filename,
            }
            save_state(state)

            new_files.append(f"audio/{filename}")
            new_titles.append(title)

        except subprocess.CalledProcessError as exc:
            log.error("Failed to process %s (%s): %s", title, video_id, exc)
            continue

    if new_files:
        try:
            git_commit_and_push(new_files, new_titles)
        except subprocess.CalledProcessError as exc:
            log.error("Git push failed: %s", exc)
    else:
        log.info("No new episodes.")

    log.info("=== podcast_sync done ===")


if __name__ == "__main__":
    main()
