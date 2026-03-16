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
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_PATH     = Path(os.environ.get("REPO_PATH", Path(__file__).parent))
PLAYLIST_URL  = os.environ["PLAYLIST_URL"]
FEED_BASE_URL = os.environ["FEED_BASE_URL"]
FEED_TOKEN    = os.environ["FEED_TOKEN"]
YTDLP         = "/opt/homebrew/bin/yt-dlp"
PYTHON        = sys.executable
RETENTION_DAYS = 30

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
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MANUAL_RUN = os.environ.get("PODCAST_MANUAL_RUN") == "1"


def notify(title: str, message: str) -> None:
    """Send a macOS notification (only during manual runs)."""
    if not MANUAL_RUN:
        return
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script])


def indent_xml(elem, level=0):
    pad = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = pad
        last = None
        for child in elem:
            indent_xml(child, level + 1)
            last = child
        if last is not None and (not last.tail or not last.tail.strip()):
            last.tail = pad
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = pad


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
        [YTDLP, "--flat-playlist", "--dump-json", PLAYLIST_URL],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("yt-dlp stderr: %s", result.stderr)
        raise subprocess.CalledProcessError(result.returncode, result.args)

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


def download_video(video_id: str, title: str) -> tuple[str, int, int, str, str, str]:
    """Download audio and return (filename, duration_secs, file_size_bytes, channel_name, description, thumbnail)."""
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

    # Get duration, channel, description and thumbnail from metadata
    meta = get_video_metadata(video_id)
    duration = int(meta.get("duration") or 0)
    channel_name = meta.get("channel") or meta.get("uploader") or "Podcast"
    description = meta.get("description") or ""
    # Best available thumbnail
    thumbnails = meta.get("thumbnails") or []
    thumbnail = ""
    if thumbnails:
        # Prefer maxresdefault or the highest resolution available
        for t in reversed(thumbnails):
            url_t = t.get("url", "")
            if url_t.startswith("http"):
                thumbnail = url_t
                break

    return filename, duration, file_size, channel_name, description, thumbnail


def update_rss(filename: str, title: str, channel_name: str, duration: int, file_size: int,
               description: str = "", thumbnail: str = "") -> None:
    env = {
        **os.environ,
        "FEED_BASE_URL": FEED_BASE_URL,
        "FEED_TOKEN":    FEED_TOKEN,
        "AUDIO_FILE":    filename,
        "TITLE":         title,
        "CHANNEL_NAME":  channel_name,
        "DURATION":      str(duration),
        "FILE_SIZE":     str(file_size),
        "DESCRIPTION":   description,
        "THUMBNAIL":     thumbnail,
    }
    subprocess.run(
        [PYTHON, str(REPO_PATH / "generate_rss.py")],
        check=True,
        cwd=REPO_PATH,
        env=env,
    )
    log.info("RSS updated for: %s", title)


def remove_episode_from_feed(filename: str) -> None:
    """Remove an item from feed.xml by matching its audio filename."""
    feed_path = REPO_PATH / "feed.xml"
    if not feed_path.exists():
        return
    tree = ET.parse(feed_path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        return
    for item in channel.findall("item"):
        guid = item.findtext("guid") or ""
        if filename in guid:
            channel.remove(item)
            log.info("Removed from feed.xml: %s", filename)
            break
    indent_xml(root)
    tree.write(str(feed_path), encoding="utf-8", xml_declaration=True, short_empty_elements=False)


def cleanup_old_episodes(state: dict) -> tuple[dict, list[str]]:
    """Delete episodes older than RETENTION_DAYS. Returns updated state and list of removed audio paths."""
    now = datetime.now(timezone.utc)
    to_remove = []
    for video_id, info in list(state.items()):
        downloaded_at = datetime.fromisoformat(info["downloaded_at"])
        age_days = (now - downloaded_at).days
        if age_days >= RETENTION_DAYS:
            to_remove.append((video_id, info))

    if not to_remove:
        return state, []

    removed_files = []
    for video_id, info in to_remove:
        filename = info["filename"]
        audio_path = AUDIO_DIR / filename
        if audio_path.exists():
            audio_path.unlink()
            log.info("Deleted audio: %s (%d days old)", filename, (now - datetime.fromisoformat(info["downloaded_at"])).days)
        remove_episode_from_feed(filename)
        del state[video_id]
        removed_files.append(f"audio/{filename}")

    return state, removed_files


def git_commit_and_push(new_files: list[str], titles: list[str], removed: bool = False) -> None:
    if removed:
        commit_msg = f"Remove episodes older than {RETENTION_DAYS} days"
    elif len(titles) == 1:
        commit_msg = "Add episode: " + titles[0]
    else:
        commit_msg = "Add episodes: " + ", ".join(titles)

    files_to_stage = ["feed.xml", "downloaded.json"] + new_files
    # Use git rm for deleted audio files so git tracks the removal
    for f in new_files:
        audio_path = REPO_PATH / f
        if not audio_path.exists():
            subprocess.run(["git", "rm", "--ignore-unmatch", f], check=True, cwd=REPO_PATH)
    subprocess.run(["git", "add"] + [f for f in files_to_stage if (REPO_PATH / f).exists()], check=True, cwd=REPO_PATH)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=REPO_PATH)
    subprocess.run(["git", "push"], check=True, cwd=REPO_PATH)
    log.info("Pushed to GitHub: %s", commit_msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== podcast_sync start ===")

    state = load_state()

    # Cleanup episodes older than RETENTION_DAYS
    state, removed_files = cleanup_old_episodes(state)
    if removed_files:
        save_state(state)

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
            filename, duration, file_size, channel_name, description, thumbnail = download_video(video_id, title)
            update_rss(filename, title, channel_name, duration, file_size, description, thumbnail)

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
            notify("Podcast Sync ❌", f"Download mislukt: {title[:60]}")
            continue

    if new_files or removed_files:
        commit_files = new_files + removed_files
        commit_titles = new_titles or ["cleanup"]
        try:
            git_commit_and_push(commit_files, commit_titles, removed=bool(removed_files and not new_files))
            if new_titles:
                summary = new_titles[0] if len(new_titles) == 1 else f"{len(new_titles)} nieuwe afleveringen"
                notify("Podcast Sync ✅", f"Gepubliceerd: {summary[:80]}")
            if removed_files and not new_files:
                notify("Podcast Sync 🧹", f"{len(removed_files)} oude afleveringen verwijderd")
        except subprocess.CalledProcessError as exc:
            log.error("Git push failed: %s", exc)
            notify("Podcast Sync ❌", f"Git push mislukt: {exc}")
    else:
        log.info("No new episodes.")
        notify("Podcast Sync ℹ️", "Geen nieuwe afleveringen gevonden")

    log.info("=== podcast_sync done ===")


if __name__ == "__main__":
    main()
