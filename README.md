# Podcast

Privé podcast pipeline: YouTube-playlist → M4A audio → RSS feed → Overcast.

Werkt volledig lokaal op de Mac. Geen GitHub Actions nodig.

## Hoe het werkt

1. Voeg een video toe aan je YouTube-playlist op de iPhone (2 tikken)
2. De Mac draait elk half uur `podcast_sync.py` via launchd
3. Nieuwe videos worden gedownload (met Firefox-cookies), RSS wordt bijgewerkt, en alles wordt gepusht naar GitHub
4. Overcast pikt de nieuwe aflevering automatisch op

---

## Eerste keer instellen

### 1. Vereisten

```bash
brew install yt-dlp
```

Zorg dat je ingelogd bent bij YouTube in **Firefox**.

### 2. YouTube-playlist aanmaken

Maak een playlist aan op je telefoon (mag Niet-vermeld zijn). Kopieer de playlist-URL.

### 3. Plist configureren

Vul de `PLAYLIST_URL` in in de plist:

```
~/Library/LaunchAgents/com.morningcoffee.podcast.plist
```

### 4. Handmatig testen (doe dit eerst)

```bash
export PLAYLIST_URL="https://www.youtube.com/playlist?list=..."
export FEED_BASE_URL="https://raw.githubusercontent.com/Morningcoffee74/Podcast/main"
export FEED_TOKEN="519119c7eca349020fbab31a5c068d1ad7f746884415f36216ee6bd09759ce88"
export REPO_PATH="/Users/wb-antal/Development/podcast"

cd /Users/wb-antal/Development/podcast
python3 podcast_sync.py
```

### 5. Launchd activeren

```bash
launchctl load ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
```

Handmatig triggeren (zonder 30 minuten te wachten):

```bash
launchctl start com.morningcoffee.podcast
tail -f ~/Library/Logs/podcast_sync.log
```

---

## Privé feed URL

```
https://raw.githubusercontent.com/Morningcoffee74/Podcast/main/feed.xml?token=519119c7eca349020fbab31a5c068d1ad7f746884415f36216ee6bd09759ce88
```

Voeg deze URL toe in Overcast via **Add URL**.

---

## Problemen oplossen

**TCC-fout (macOS blokkeert toegang tot Firefox-profiel):**
Systeeminstellingen → Privacy & Beveiliging → Volledige schijftoegang → voeg `/usr/bin/python3` toe.

**Logs bekijken:**
```bash
tail -f ~/Library/Logs/podcast_sync.log
```

**Launchd uitschakelen:**
```bash
launchctl unload ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
```
