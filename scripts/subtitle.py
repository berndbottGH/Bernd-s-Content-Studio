#!/usr/bin/env python3
"""Untertitel einbrennen + 9:16-Export via FFmpeg.

Stil kommt aus config/subtitle-style.json. Schreibt nach /work:
  <name>_subtitled.mp4       – Original-Format mit eingebrannten Untertiteln
  <name>_subtitled_9x16.mp4  – 9:16-Variante (falls in der Config aktiviert)

Aufruf:
  python scripts/subtitle.py inbox/video.mp4 work/video.srt
  python scripts/subtitle.py inbox/video.mp4 work/video.srt --no-vertical
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = PROJECT_ROOT / "work"
STYLE_PATH = PROJECT_ROOT / "config" / "subtitle-style.json"


def build_force_style(style: dict) -> str:
    parts = [
        f"FontName={style.get('font_name', 'Arial')}",
        f"FontSize={style.get('font_size', 14)}",
        f"PrimaryColour={style.get('primary_colour', '&H00FFFFFF')}",
        f"OutlineColour={style.get('outline_colour', '&H00000000')}",
        f"BackColour={style.get('back_colour', '&H80000000')}",
        f"Bold={1 if style.get('bold', True) else 0}",
        f"Outline={style.get('outline', 1.5)}",
        f"Shadow={style.get('shadow', 0)}",
        f"BorderStyle={style.get('border_style', 1)}",
        f"Alignment={style.get('alignment', 2)}",
        f"MarginV={style.get('margin_v', 60)}",
        f"MarginL={style.get('margin_l', 30)}",
        f"MarginR={style.get('margin_r', 30)}",
    ]
    return ",".join(parts)


def escape_filter_path(path: Path) -> str:
    # FFmpeg-Filterargumente: ':' und '\' müssen escaped werden
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def run_ffmpeg(cmd: list[str]) -> None:
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Untertitel einbrennen + 9:16-Export")
    parser.add_argument("video", help="Eingangsvideo (z. B. inbox/video.mp4)")
    parser.add_argument("srt", help="SRT-Datei (z. B. work/video.srt)")
    parser.add_argument("--no-vertical", action="store_true",
                        help="9:16-Export überspringen")
    args = parser.parse_args()

    video = Path(args.video)
    srt = Path(args.srt)
    for f in (video, srt):
        if not f.exists():
            print(f"FEHLER: Datei nicht gefunden: {f}", file=sys.stderr)
            return 1
    if not shutil.which("ffmpeg"):
        print("FEHLER: ffmpeg nicht gefunden. Installieren mit: brew install ffmpeg",
              file=sys.stderr)
        return 1

    style = json.loads(STYLE_PATH.read_text(encoding="utf-8"))
    force_style = build_force_style(style)
    srt_escaped = escape_filter_path(srt)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    out_main = WORK_DIR / f"{video.stem}_subtitled.mp4"
    print(f"Brenne Untertitel ein → {out_main.name}")
    run_ffmpeg([
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"subtitles='{srt_escaped}':force_style='{force_style}'",
        "-c:a", "copy",
        str(out_main),
    ])

    vertical = style.get("vertical_export", {})
    if vertical.get("enabled", True) and not args.no_vertical:
        w = vertical.get("width", 1080)
        h = vertical.get("height", 1920)
        mode = vertical.get("mode", "crop_center")
        out_vert = WORK_DIR / f"{video.stem}_subtitled_9x16.mp4"

        if mode == "crop_center":
            # Auf 9:16 hochskalieren und mittig beschneiden
            vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},"
                  f"subtitles='{srt_escaped}':force_style='{force_style}'")
        else:  # pad: Video komplett zeigen, Rest mit unscharfem Hintergrund füllen
            vf = (f"split[bg][fg];"
                  f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},boxblur=20[bgb];"
                  f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fgs];"
                  f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,"
                  f"subtitles='{srt_escaped}':force_style='{force_style}'")

        print(f"Erzeuge 9:16-Variante → {out_vert.name}")
        run_ffmpeg([
            "ffmpeg", "-y", "-i", str(video),
            "-vf", vf,
            "-c:a", "copy",
            str(out_vert),
        ])

    print("\nFertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
