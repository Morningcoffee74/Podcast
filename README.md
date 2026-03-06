# Podcast

Private podcast pipeline: YouTube URL → M4A audio → RSS feed → Overcast (of een andere podcast-app).

## Hoe het werkt

1. Trigger de GitHub Actions workflow met een YouTube URL (via de GitHub UI of een iOS Shortcut)
2. De workflow downloadt het geluid als M4A, maakt/updatet `feed.xml`, en commit alles terug naar de repo
3. Voeg de privé feed URL toe aan je podcast-app

---

## Vereiste GitHub Secrets

Ga naar **Settings → Secrets and variables → Actions** en voeg toe:

| Secret | Waarde |
|--------|--------|
| `FEED_BASE_URL` | `https://raw.githubusercontent.com/Morningcoffee74/Podcast/main` |
| `FEED_TOKEN` | Een lang willekeurig geheim (zie hieronder) |

Genereer een token:
```bash
openssl rand -hex 32
```

---

## Privé feed URL

```
https://raw.githubusercontent.com/Morningcoffee74/Podcast/main/feed.xml?token=JOUW_FEED_TOKEN
```

Voeg deze URL toe in Overcast via **Add URL** (of vergelijkbare optie in je podcast-app).

---

## iOS Shortcut instellen

### Benodigde GitHub PAT

Maak een fine-grained Personal Access Token aan:
- GitHub → Settings → Developer Settings → Personal access tokens → Fine-grained tokens
- Repository access: alleen `Morningcoffee74/Podcast`
- Permissions: **Actions** → Read and Write

### "Get Contents of URL" configuratie

| Veld | Waarde |
|------|--------|
| URL | `https://api.github.com/repos/Morningcoffee74/Podcast/actions/workflows/download.yml/dispatches` |
| Method | POST |
| Header: `Accept` | `application/vnd.github+json` |
| Header: `Authorization` | `Bearer JOUW_GITHUB_PAT` |
| Header: `X-GitHub-Api-Version` | `2022-11-28` |
| Header: `Content-Type` | `application/json` |
| Request body type | JSON |
| Body: `ref` | `main` |
| Body: `inputs.url` | _(YouTube URL uit Shortcut-invoer)_ |

### Equivalent curl-commando

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer JOUW_GITHUB_PAT" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  https://api.github.com/repos/Morningcoffee74/Podcast/actions/workflows/download.yml/dispatches \
  -d '{"ref":"main","inputs":{"url":"YOUTUBE_URL"}}'
```

Een succesvolle aanroep geeft HTTP **204** terug (geen body).

---

## Handmatig testen

Actions → **Download YouTube Audio** → **Run workflow** → plak een YouTube URL → **Run workflow**

Na afloop:
- Controleer of `audio/*.m4a` en `feed.xml` zijn gecommit
- Valideer de feed via [Podba.se Validator](https://podba.se/validate/)
