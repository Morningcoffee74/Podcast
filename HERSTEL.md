# HERSTEL – Podcast-sync weer aanzetten

*Status sinds 24 oktober 2026: **uitgeschakeld en leeggemaakt.***
*Dit bestand is bedoeld voor Antal én voor Claude. Zeg tegen Claude: "lees HERSTEL.md in ~/Development/podcast en zet de podcast-sync weer aan".*

---

> ## ⚠️ EERST DOEN, VÓÓR JE DE APP WEER AANZET
>
> Doe je deze twee dingen niet, dan loopt de app op precies dezelfde manier vast als in 2026:
>
> - [ ] **1. yt-dlp bijwerken.** Voer `brew upgrade yt-dlp` uit. Met een oude versie weigert YouTube downloads (`HTTP Error 403: Forbidden`).
> - [ ] **2. Bestanden groter dan 100 MB voorkomen.** Pas `podcast_sync.py` aan zoals beschreven in stap 2 hieronder. GitHub weigert bestanden boven 100 MB, en dan komt er **niets** meer aan in Overcast, ook geen kleine afleveringen.
>
> Claude: controleer deze twee punten altijd voordat je de achtergrondtaak weer activeert.

---

## Wat is er gedaan (24-10-2026)

| Actie | Details |
|---|---|
| Achtergrondtaak gestopt | `launchctl bootout gui/$(id -u)/com.morningcoffee.podcast` |
| Startbestand weggehaald uit LaunchAgents | Verplaatst naar deze map als `com.morningcoffee.podcast.plist.uitgeschakeld` (staat **niet** in git, zie `.gitignore`) |
| Lokale audio verwijderd | Map `audio/` geleegd (was ±1 GB, 32 afleveringen) |
| Git-geschiedenis gewist | Nieuwe, schone geschiedenis met alleen scripts + documentatie, met `--force` naar GitHub gepusht. Lokale `.git` ging van 3,3 GB naar enkele KB's |
| State gereset | `downloaded.json` = `{}`, `feed.xml` = lege feed zonder afleveringen |
| Logbestand verwijderd | `~/Library/Logs/podcast_sync.log` (21 MB) |

De GitHub-repo `Morningcoffee74/Podcast` bestaat nog (publiek), maar bevat geen audio meer.

---

## Waarom Overcast geen nieuwe afleveringen meer kreeg

Er waren twee problemen, en die moet je oplossen voordat je de app weer aanzet:

1. **Bestand te groot voor GitHub (hoofdoorzaak).**
   Op 7 maart 2026 werd *"Why the Pentagon Wants to Destroy Anthropic – The Ezra Klein Show"* gedownload (139 MB). GitHub weigert bestanden boven **100 MB**. Sindsdien werd elke `git push` geweigerd: 136 commits bleven lokaal hangen. De laatste geslaagde push was op 5 april 2026. De Mac bleef wel downloaden, maar er kwam niets meer bij Overcast aan.
2. **yt-dlp verouderd.** Versie 2026.03.17 gaf regelmatig `HTTP Error 403: Forbidden` bij het downloaden. YouTube verandert vaak iets, en yt-dlp moet daarom regelmatig bijgewerkt worden.

---

## Stappen om het weer te laten werken

### 1. yt-dlp bijwerken (verplicht)
```bash
brew upgrade yt-dlp
```

### 2. Grote bestanden voorkomen (verplicht, anders gaat het opnieuw mis)
Zoek in `podcast_sync.py`, functie `download_video`, het blok met de yt-dlp-argumenten. Vervang `"--audio-quality", "0",` door:
```python
"--audio-quality", "5",          # lagere bitrate, ruim voldoende voor gesproken woord
"--max-filesize", "95M",         # sla alles boven 95 MB over (GitHub-limiet is 100 MB)
```
Let op: als yt-dlp een bestand overslaat vanwege `--max-filesize`, bestaat het outputbestand niet. Het script crasht dan op `output_path.stat()` en logt een fout. Dat is acceptabel: de aflevering wordt overgeslagen en de rest gaat gewoon door. Wil je dit netter, vraag Claude dan om een check `if not output_path.exists()` toe te voegen.

### 3. GitHub-repo controleren
- Bestaat `https://github.com/Morningcoffee74/Podcast` nog en staat hij op **Public**? Ga dan door naar stap 4.
- **Repo verwijderd?** Opnieuw aanmaken kost ongeveer 2 minuten:
  1. github.com → **New repository** → naam exact `Podcast` → **Public** → *geen* README toevoegen → Create.
  2. In de terminal:
     ```bash
     cd ~/Development/podcast
     git push -u origin main
     ```
  3. Omdat de naam hetzelfde is, blijft de feed-URL ongewijzigd en hoef je in Overcast niets aan te passen.
- **Push vraagt om wachtwoord of geeft "authentication failed"?** Het toegangstoken (PAT) in de remote-URL is verlopen of ingetrokken. Maak een nieuw token aan: GitHub → Settings → Developer settings → Personal access tokens → *Fine-grained*, met alleen toegang tot de repo `Podcast` en *Contents: Read and write*. Stel het daarna in:
  ```bash
  git remote set-url origin https://<NIEUW_TOKEN>@github.com/Morningcoffee74/Podcast.git
  ```

### 4. Firefox-cookies
Het script gebruikt de YouTube-login uit **Firefox**. Zorg dat je daar nog ingelogd bent bij YouTube. Gebruik je een andere browser, verander dan `"--cookies-from-browser", "firefox"` in `chrome` of `safari`.

### 5. Eerst handmatig testen
```bash
cd ~/Development/podcast
export PLAYLIST_URL="https://www.youtube.com/playlist?list=PLFnus5-VCd3ougLcTCBtfAxbkEnmykWxC"
export FEED_BASE_URL="https://raw.githubusercontent.com/Morningcoffee74/Podcast/main"
export FEED_TOKEN="ongebruikt"
export REPO_PATH="$HOME/Development/podcast"
python3 podcast_sync.py
tail -30 ~/Library/Logs/podcast_sync.log
git status -sb        # moet "## main...origin/main" tonen, ZONDER "[ahead N]"
```
Staat er `[ahead N]`? Dan is de push mislukt. Kijk in het log naar de regel met `remote: error`.

> Let op: de afspeellijst bevat nog zo'n 32 video's. Bij de eerste run worden die **allemaal** opnieuw gedownload. Haal eerst op YouTube de video's uit de afspeellijst die je niet meer wilt.

### 6. Automatisch laten draaien
```bash
cd ~/Development/podcast
mv com.morningcoffee.podcast.plist.uitgeschakeld ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.morningcoffee.podcast.plist
launchctl list | grep morningcoffee    # moet de taak tonen
```
De taak draait elke 30 minuten (`StartInterval` = 1800) en direct na het inloggen (`RunAtLoad` = true). Let op: de README noemt nog "elke 4 uur", maar dat klopt niet meer.

### 7. Overcast
De feed-URL is `https://raw.githubusercontent.com/Morningcoffee74/Podcast/main/feed.xml`. Heb je het abonnement in Overcast verwijderd? Voeg het dan opnieuw toe via **+** → **Add URL**.

---

## Weer uitschakelen
```bash
launchctl bootout gui/$(id -u)/com.morningcoffee.podcast
mv ~/Library/LaunchAgents/com.morningcoffee.podcast.plist ~/Development/podcast/com.morningcoffee.podcast.plist.uitgeschakeld
```
