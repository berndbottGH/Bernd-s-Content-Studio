#!/usr/bin/env python3
"""Ayrshare-Publishing: posten oder planen, Live-Links zurückgeben, Archiv loggen.

WICHTIG: Dieses Script wird NUR nach Bernds explizitem "Go" aufgerufen.

Aufruf (pro Plattform-Kombination ein Aufruf):
  python scripts/publish.py --platforms linkedin,twitter --text "…"
  python scripts/publish.py --platforms instagram --text "…" --media work/video_9x16.mp4
  python scripts/publish.py --platforms linkedin --text "…" --schedule 2026-07-09T06:00:00Z
  python scripts/publish.py --platforms twitter --text "…" --test   (Dry-Run ohne API-Call)

Plattform-Namen (Ayrshare): instagram, facebook, threads, twitter, linkedin, tiktok
"""

import argparse
import json
import mimetypes
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = PROJECT_ROOT / "archive" / "posts.jsonl"
ENV_PATH = PROJECT_ROOT / ".env"

VALID_PLATFORMS = {"instagram", "facebook", "threads", "twitter", "linkedin", "tiktok"}
API_URL = "https://api.ayrshare.com/api/post"
MEDIA_UPLOAD_URL = "https://api.ayrshare.com/api/media/upload"


def load_api_key() -> str | None:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AYRSHARE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def upload_media(api_key: str, media_path: Path) -> str:
    """Lokale Datei zu Ayrshare hochladen, gibt die Media-URL zurück."""
    import requests

    content_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
    resp = requests.get(
        MEDIA_UPLOAD_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        params={"fileName": media_path.name, "contentType": content_type},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    upload_url = data["uploadUrl"]
    access_url = data["accessUrl"]

    with media_path.open("rb") as fh:
        put = requests.put(upload_url, data=fh,
                           headers={"Content-Type": content_type}, timeout=600)
    put.raise_for_status()
    return access_url


def log_post(entry: dict) -> None:
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Über Ayrshare posten/planen")
    parser.add_argument("--platforms", required=True,
                        help="Kommagetrennt: instagram,facebook,threads,twitter,linkedin,tiktok")
    parser.add_argument("--text", required=True, help="Der Post-Text")
    parser.add_argument("--media", default=None,
                        help="Optionale Mediendatei (Video/Bild) oder bereits öffentliche URL")
    parser.add_argument("--schedule", default=None,
                        help="Geplante Zeit als UTC-ISO-Timestamp, z. B. 2026-07-09T06:00:00Z")
    parser.add_argument("--source", default=None,
                        help="Quelldatei für das Archiv-Log (z. B. inbox/video.mp4)")
    parser.add_argument("--format", dest="fmt", default="text",
                        help="Format fürs Archiv-Log: video / text / text+bild")
    parser.add_argument("--test", action="store_true",
                        help="Dry-Run: zeigt den Payload, ruft die API nicht auf")
    args = parser.parse_args()

    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    invalid = set(platforms) - VALID_PLATFORMS
    if invalid:
        print(f"FEHLER: Unbekannte Plattform(en): {', '.join(sorted(invalid))}\n"
              f"Gültig: {', '.join(sorted(VALID_PLATFORMS))}", file=sys.stderr)
        return 1

    payload: dict = {"post": args.text, "platforms": platforms}
    if args.schedule:
        payload["scheduleDate"] = args.schedule

    api_key = load_api_key()

    media_url = None
    if args.media:
        if args.media.startswith(("http://", "https://")):
            media_url = args.media
        else:
            media_path = Path(args.media)
            if not media_path.exists():
                print(f"FEHLER: Mediendatei nicht gefunden: {media_path}", file=sys.stderr)
                return 1
            if args.test:
                media_url = f"(Upload von {media_path} – im Test-Modus übersprungen)"
            else:
                if not api_key:
                    print("FEHLER: AYRSHARE_API_KEY fehlt in .env", file=sys.stderr)
                    return 1
                print(f"Lade {media_path.name} zu Ayrshare hoch …")
                media_url = upload_media(api_key, media_path)
        payload["mediaUrls"] = [media_url]
        if "tiktok" in platforms or (isinstance(media_url, str) and
                                     media_url.lower().endswith((".mp4", ".mov"))):
            payload["isVideo"] = True

    if args.test:
        print("TEST-MODUS – es wird NICHT gepostet. Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not api_key:
        print("FEHLER: AYRSHARE_API_KEY fehlt in .env", file=sys.stderr)
        return 1

    import requests

    print(f"Poste auf: {', '.join(platforms)}"
          + (f" (geplant für {args.schedule})" if args.schedule else " (sofort)"))
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    data = resp.json()

    if resp.status_code != 200 or data.get("status") == "error":
        print("FEHLER von Ayrshare:", file=sys.stderr)
        print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    # Live-Links einsammeln (pro Plattform)
    links: dict = {}
    for item in data.get("postIds", []):
        platform = item.get("platform", "?")
        links[platform] = item.get("postUrl") or item.get("id", "")

    print("\nErfolgreich:" if not args.schedule else "\nGeplant:")
    for platform in platforms:
        link = links.get(platform, "(kein Link zurückgegeben)")
        print(f"  {platform}: {link}")

    # Archiv-Log (F6)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for platform in platforms:
        log_post({
            "date": now,
            "scheduled_for": args.schedule,
            "platform": platform,
            "format": args.fmt,
            "text": args.text,
            "source": args.source,
            "live_link": links.get(platform),
            "ayrshare_id": data.get("id"),
        })
    print(f"\nIns Archiv geloggt: {ARCHIVE_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
