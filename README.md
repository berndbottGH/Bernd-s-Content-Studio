# Content-Studio „Bernd Bott"

Ein Content-System, das komplett in der Claude-Code-App läuft. Die App IST die
Oberfläche: Video (oder Sprachnotiz oder Stichworte) rein, Claude verarbeitet,
zeigt alle Textvorschläge pro Plattform im Chat, Bernd gibt per Zuruf frei –
dann wird über Ayrshare gepostet.

**Eisernes Prinzip: Kein Post ohne explizite Freigabe.**

## Schnellstart

1. `.env.example` nach `.env` kopieren und den Ayrshare-API-Key eintragen
2. Abhängigkeiten: `brew install ffmpeg` und `pip install openai-whisper Pillow requests`
3. 2–3 eigene Beispiel-Posts in `config/brand-voice.md` eintragen (Ton-Referenz)
4. Claude-Code-App im Projektordner öffnen, Video in `/inbox` legen und sagen:
   „Neues Video, verarbeite es."

## Struktur

| Pfad | Zweck |
|---|---|
| `CLAUDE.md` | Arbeitsanweisung für jede Session (Workflow, Prinzipien) |
| `config/` | Brand Voice, Stil-Wächter, Sprach-DNA, Routing-Regeln, Plattform-Profile, Design |
| `scripts/` | transcribe.py (Whisper) · subtitle.py (FFmpeg) · render_image.py (Zitat-Grafiken) · publish.py (Ayrshare) |
| `inbox/` | Hier landen neue Videos/Audios |
| `work/` | Zwischenstände (Transkripte, untertitelte Videos, Grafiken) |
| `archive/posts.jsonl` | Log aller veröffentlichten Posts (Doppel-Posting-Schutz) |

## Checkliste vor dem ersten Lauf

1. [ ] Instagram auf Creator-Konto umgestellt
2. [ ] Meta Accounts Center: Auto-Share IG → Facebook + Threads aktiviert (falls gewünscht)
3. [ ] Ayrshare-Account + Profile verbunden (inkl. TikTok), API-Key in `.env`
4. [ ] ffmpeg + Whisper installiert
5. [ ] 2–3 Beispiel-Posts in `config/brand-voice.md`
6. [ ] Design-Assets für Zitat-Grafiken in `config/design/assets/` (sonst startet
       das cleane Platzhalter-Design)
