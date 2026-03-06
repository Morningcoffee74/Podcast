#!/usr/bin/env python3
"""
generate_rss.py
Creates or updates feed.xml with a new podcast episode.

Environment variables (set by GitHub Actions workflow):
  FEED_BASE_URL  - e.g. "https://raw.githubusercontent.com/Morningcoffee74/Podcast/main"
  FEED_TOKEN     - secret token appended as ?token=<FEED_TOKEN> to the feed URL
  AUDIO_FILE     - sanitized filename, e.g. "My_Episode_dQw4w9WgXcQ.m4a"
  TITLE          - episode title from YouTube
  CHANNEL_NAME   - YouTube channel name (used as podcast title on first run)
  DURATION       - integer seconds
  FILE_SIZE      - integer bytes
"""

import os
from datetime import timezone
from email.utils import formatdate
from xml.etree import ElementTree as ET

BASE_URL     = os.environ["FEED_BASE_URL"].rstrip("/")
TOKEN        = os.environ["FEED_TOKEN"]
AUDIO_FILE   = os.environ["AUDIO_FILE"]
TITLE        = os.environ["TITLE"]
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "Podcast")
DURATION     = int(os.environ["DURATION"])
FILE_SIZE    = int(os.environ["FILE_SIZE"])

FEED_PATH  = "feed.xml"
ITUNES_NS  = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS    = "http://www.w3.org/2005/Atom"

ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("atom",   ATOM_NS)


def audio_url(filename):
    return f"{BASE_URL}/audio/{filename}"


def feed_url():
    return f"{BASE_URL}/feed.xml"


def rfc2822_now():
    return formatdate(usegmt=True)


def duration_str(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_item(title, audio_filename, pub_date, duration_secs, file_size):
    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "guid", isPermaLink="false").text = audio_url(audio_filename)
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "enclosure",
                  url=audio_url(audio_filename),
                  length=str(file_size),
                  type="audio/mp4")
    ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = duration_str(duration_secs)
    ET.SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "no"
    return item


def create_feed(first_item, channel_name):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text       = channel_name
    ET.SubElement(channel, "description").text = f"Private podcast feed - {channel_name}"
    ET.SubElement(channel, "language").text    = "en-us"
    ET.SubElement(channel, "link").text        = feed_url()
    ET.SubElement(channel, "lastBuildDate").text = rfc2822_now()

    ET.SubElement(channel, f"{{{ATOM_NS}}}link",
                  href=feed_url(),
                  rel="self",
                  type="application/rss+xml")

    ET.SubElement(channel, f"{{{ITUNES_NS}}}author").text   = channel_name
    ET.SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "no"
    ET.SubElement(channel, f"{{{ITUNES_NS}}}type").text     = "episodic"

    channel.append(first_item)
    return ET.ElementTree(rss)


def update_feed(existing_path, new_item):
    tree = ET.parse(existing_path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Malformed feed.xml: no <channel> element")

    lbd = channel.find("lastBuildDate")
    if lbd is not None:
        lbd.text = rfc2822_now()

    items = channel.findall("item")
    if items:
        channel.insert(list(channel).index(items[0]), new_item)
    else:
        channel.append(new_item)

    return tree


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


def main():
    pub_date = rfc2822_now()
    new_item = build_item(
        title=TITLE,
        audio_filename=AUDIO_FILE,
        pub_date=pub_date,
        duration_secs=DURATION,
        file_size=FILE_SIZE,
    )

    if os.path.exists(FEED_PATH):
        print(f"Updating existing {FEED_PATH}")
        tree = update_feed(FEED_PATH, new_item)
    else:
        print(f"Creating new {FEED_PATH}")
        tree = create_feed(new_item, CHANNEL_NAME)

    indent_xml(tree.getroot())
    tree.write(FEED_PATH,
               encoding="utf-8",
               xml_declaration=True,
               short_empty_elements=False)

    print(f"Done. Feed URL (private): {feed_url()}")
    print(f"      Audio URL:          {audio_url(AUDIO_FILE)}")


if __name__ == "__main__":
    main()
