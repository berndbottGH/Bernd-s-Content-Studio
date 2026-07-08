#!/usr/bin/env python3
"""Whisper-Transkription (Deutsch) für das Content-Studio.

Nimmt eine Video- oder Audiodatei (z. B. aus /inbox) und schreibt nach /work:
  <name>.txt  – reines Transkript (für die Texterstellung)
  <name>.srt  – Untertitel mit Timestamps (für subtitle.py, nur sinnvoll bei Video)

Aufruf:
  python scripts/transcribe.py inbox/mein-video.mp4
  python scripts/transcribe.py inbox/notiz.m4a --model small
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = PROJECT_ROOT / "work"

SUPPORTED = {".mp4", ".mov", ".m4a", ".mp3", ".wav", ".aac", ".webm", ".mkv"}


def format_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{format_srt_time(seg['start'])} --> {format_srt_time(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Whisper-Transkription (Deutsch)")
    parser.add_argument("input", help="Video-/Audiodatei (z. B. inbox/video.mp4)")
    parser.add_argument("--model", default="medium",
                        help="Whisper-Modell: tiny/base/small/medium/large (Default: medium)")
    parser.add_argument("--language", default="de", help="Sprache (Default: de)")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"FEHLER: Datei nicht gefunden: {src}", file=sys.stderr)
        return 1
    if src.suffix.lower() not in SUPPORTED:
        print(f"FEHLER: Nicht unterstütztes Format: {src.suffix}", file=sys.stderr)
        return 1

    try:
        import whisper
    except ImportError:
        print("FEHLER: openai-whisper ist nicht installiert.\n"
              "Installieren mit: pip install openai-whisper", file=sys.stderr)
        return 1

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Lade Whisper-Modell '{args.model}' …")
    model = whisper.load_model(args.model)

    print(f"Transkribiere {src.name} …")
    result = model.transcribe(str(src), language=args.language)

    txt_path = WORK_DIR / f"{src.stem}.txt"
    srt_path = WORK_DIR / f"{src.stem}.srt"

    txt_path.write_text(result["text"].strip() + "\n", encoding="utf-8")
    write_srt(result["segments"], srt_path)

    print(f"\nFertig:")
    print(f"  Transkript: {txt_path}")
    print(f"  Untertitel: {srt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
