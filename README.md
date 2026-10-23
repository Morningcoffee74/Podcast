# Podcast – YouTube Playlist naar Overcast

Dit systeem zet automatisch video's uit een YouTube-playlist om naar een podcast die je in Overcast kunt beluisteren.

**Hoe het werkt in één zin:**
Voeg een video toe aan je YouTube-playlist op je iPhone → de Mac pikt dit automatisch op → de audio verschijnt in Overcast.

---

## Overzicht

```
iPhone: video toevoegen aan YouTube-playlist
           ↓  (elke 4 uur automatisch)
Mac: podcast_sync.py draait op de achtergrond via launchd
           ↓
yt-dlp downloadt de audio (M4A) met jouw Firefox-cookies
           ↓
generate_rss.py maakt/updatet feed.xml
           ↓
Git pusht audio + feed naar GitHub
           ↓
Overcast leest de feed en toont de nieuwe aflevering
```

- Afleveringen worden automatisch verwijderd na **30 dagen**
- Per aflevering: eigen YouTube-thumbnail + volledige beschrijving
- De feed is publiek toegankelijk via de directe GitHub-URL (niet vindbaar, maar niet beveiligd)

---

## Vereisten

- Mac met macOS (draait op de achtergrond via launchd)
- Firefox, ingelogd bij YouTube
- Homebrew + yt-dlp: `brew install yt-dlp`
- Git met PAT ingebakken in de remote URL (zodat push werkt zonder wachtwoord)
- Python 3 (standaard aanwezig op macOS)

---

## Eerste keer instellen (stap voor stap)

### Stap 1 – yt-dlp installeren

```bash
brew install yt-dlp
```

### Stap 2 – YouTube-playlist aanmaken

1. Open YouTube op je iPhone
2. Maak een nieuwe playlist aan (bijv. "Podcast")
3. Stel zichtbaarheid in op **Niet-vermeld** (unlisted) — niet Privé, niet Openbaar
4. Kopieer de playlist-URL: `https://www.youtube.com/playlist?list=JOUW_PLAYLIST_ID`

> **Waarom niet Privé?** yt-dlp kan privé-playlists niet lezen, zelfs niet met cookies.
> Niet-vermeld betekent: niet vindbaar via zoeken, wel toegankelijk via directe link.

### Stap 3 – Plist configureren

Open het bestand `~/Library/LaunchAgents/com.morningcoffee.podcast.plist` en vul jouw playlist-URL in bij `PLAYLIST_URL`. De rest is al ingevuld.

> **De map Library is verborgen in Finder.** Open hem via:
> Finder → menu Ga → houd Option ingedrukt → Library

### Stap 4 – GitHub-repo publiek maken

De feed-URL werkt alleen als de GitHub-repo **publiek** is:
GitHub → Settings → General → Danger Zone → Change visibility → Public

> De feed is via de directe URL te lezen, maar niet vindbaar via zoeken op GitHub.

### Stap 5 – Handmatig testen

Voer dit uit in de terminal (elke regel apart, daarna Enter):

```bash
export PLAYLIST_URL="https://www.youtube.com/playlist?list=JOUW_PLAYLIST_ID"
export FEED_BASE_URL="https://raw.githubusercontent.com/Morningcoffee74/Podcast/main"
export FEED_TOKEN="519119c7eca349020fbab31a5c068d1ad7f746884415f36216ee6bd09759ce88"
export REPO_PATH="/Users/wb-antal/Development/podcast"
python3 /Users/wb-antal/Development/podcast/podcast_sync.py
```

Je ziet dan output in de terminal: het script haalt de playlist op, downloadt audio, en pusht naar GitHub.

> `FEED_TOKEN` is aanwezig maar wordt niet meer gebruikt in de feed-URL. Het staat er nog als configuratievariabele voor het geval dit later weer nodig is.

### Stap 6 – Automatisch activeren (eenmalig)

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
```

Vanaf nu draait het script **elke 4 uur automatisch** op de achtergrond, ook zonder open terminal. Je hoeft dit maar één keer te doen — ook na een herstart van de Mac blijft het actief.

### Stap 7 – Feed toevoegen in Overcast

1. Open Overcast op je iPhone
2. Tik op **+** (rechtsonder)
3. Kies **Add URL**
4. Plak:
   ```
   https://raw.githubusercontent.com/Morningcoffee74/Podcast/main/feed.xml
   ```
5. Tik **Add**

---

## Dagelijks gebruik

**Video toevoegen aan je podcast:**
1. Open YouTube op je iPhone
2. Zoek de video die je wilt beluisteren
3. Tik op **Opslaan** → selecteer je playlist "Podcast"

Klaar. Binnen 4 uur verschijnt de aflevering automatisch in Overcast.

**Handmatig triggeren (zonder 4 uur te wachten):**
```bash
launchctl start com.morningcoffee.podcast
```

**Logs bekijken:**
```bash
tail -f ~/Library/Logs/podcast_sync.log
```

---

## Configuratie-overzicht

### Plist (`~/Library/LaunchAgents/com.morningcoffee.podcast.plist`)

Dit bestand staat **niet** in de repo — het is puur lokaal op de Mac. Het vertelt macOS wanneer en hoe het script gestart moet worden.

| Instelling | Waarde | Uitleg |
|-----------|--------|--------|
| `StartInterval` | `14400` (= 4 uur) | Hoe vaak het script draait, in seconden |
| `RunAtLoad` | `false` | Niet direct starten bij inloggen, pas na 4 uur |
| `PLAYLIST_URL` | jouw playlist-URL | De YouTube-playlist om te volgen |
| `FEED_BASE_URL` | `https://raw.githubusercontent.com/Morningcoffee74/Podcast/main` | Basis-URL voor de feed en audio-bestanden |
| `REPO_PATH` | `/Users/wb-antal/Development/podcast` | Pad naar de lokale git-repo op de Mac |
| `PATH` | `/opt/homebrew/bin:...` | Zoekpad voor programma's (nodig omdat launchd geen Homebrew kent) |

### Script (`podcast_sync.py`)

| Instelling | Waarde | Uitleg |
|-----------|--------|--------|
| `RETENTION_DAYS` | `30` | Afleveringen ouder dan 30 dagen worden automatisch verwijderd |
| `YTDLP` | `/opt/homebrew/bin/yt-dlp` | Absoluut pad naar yt-dlp |
| `--cookies-from-browser` | `firefox` | Pas aan naar `chrome` of `safari` als je YouTube daar gebruikt |

---

## Bestanden in deze repo

| Bestand | Uitleg |
|---------|--------|
| `podcast_sync.py` | Hoofdscript: playlist lezen, audio downloaden, RSS updaten, pushen naar GitHub |
| `generate_rss.py` | Genereert `feed.xml` in RSS 2.0-formaat met iTunes-extensies |
| `downloaded.json` | Bijhoudt welke video-ID's al verwerkt zijn (voorkomt dubbele downloads) |
| `feed.xml` | De RSS-feed die Overcast leest (automatisch gegenereerd, niet handmatig aanpassen) |
| `audio/` | Gedownloade M4A-audiobestanden |

---

## Problemen oplossen

**yt-dlp niet gevonden:**
```bash
brew install yt-dlp
```

**"The playlist does not exist":**
Controleer of de playlist op **Niet-vermeld** staat (niet Privé).

**Feed geeft 404:**
Controleer of de GitHub-repo op **Publiek** staat:
GitHub → Settings → General → Change visibility → Public

**macOS blokkeert toegang tot Firefox-cookies:**
Systeeminstellingen → Privacy & Beveiliging → Volledige schijftoegang → voeg `/usr/bin/python3` toe

**Automatisch script uitschakelen:**
```bash
launchctl bootout gui/$(id -u)/com.morningcoffee.podcast
```

**Opnieuw activeren na aanpassing aan de plist:**
```bash
launchctl bootout gui/$(id -u)/com.morningcoffee.podcast
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
```

**Controleren of het script actief is:**
```bash
launchctl list | grep morningcoffee
```
Je ziet drie kolommen: PID (leeg = draait nu niet), exitcode (0 = geen fout), naam.

---

## Podcast-details

| | |
|-|-|
| **Feed-URL** | `https://raw.githubusercontent.com/Morningcoffee74/Podcast/main/feed.xml` |
| **Naam** | YouTube Playlist |
| **Logo** | YouTube-logo (voor de hele podcast) |
| **Per aflevering** | Eigen YouTube-thumbnail + volledige beschrijving |
| **Formaat** | M4A (audio/mp4) |
| **Automatische opruiming** | Na 30 dagen verdwijnt een aflevering uit de feed en van GitHub |
