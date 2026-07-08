#!/usr/bin/env python3
"""Zitat-Grafiken rendern (F7) – Pillow, Template + config/design/design.json.

Erzeugt pro Aufruf automatisch BEIDE Formate (1:1 und 9:16) als PNG in /work.

Aufruf:
  python scripts/render_image.py --template zitat --text "Die zweite Hälfte wird die beste meines Lebens."
  python scripts/render_image.py --template wort --text "Freiheit"
  python scripts/render_image.py --template hook --text "Was würdest du mit 50 nochmal neu anfangen?" --name mein-post
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = PROJECT_ROOT / "work"
DESIGN_PATH = PROJECT_ROOT / "config" / "design" / "design.json"

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("FEHLER: Pillow ist nicht installiert. Installieren mit: pip install Pillow",
          file=sys.stderr)
    sys.exit(1)


def hex_to_rgb(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def load_font(candidates: list, size: int) -> ImageFont.FreeTypeFont:
    """Erste existierende Schriftdatei laden; sonst PIL-Default."""
    for cand in candidates:
        if not cand:
            continue
        p = Path(cand)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def make_background(design: dict, width: int, height: int) -> Image.Image:
    bg = design["background"]
    if bg.get("image"):
        p = PROJECT_ROOT / bg["image"]
        if p.exists():
            img = Image.open(p).convert("RGB")
            # Auf Zielformat skalieren und mittig beschneiden
            ratio = max(width / img.width, height / img.height)
            img = img.resize((round(img.width * ratio), round(img.height * ratio)))
            left = (img.width - width) // 2
            top = (img.height - height) // 2
            return img.crop((left, top, left + width, top + height))
    if bg.get("type") == "gradient":
        top_rgb = hex_to_rgb(bg.get("color_top", "#1c2733"))
        bottom_rgb = hex_to_rgb(bg.get("color_bottom", "#0e141b"))
        img = Image.new("RGB", (width, height))
        px = img.load()
        for y in range(height):
            t = y / max(height - 1, 1)
            row = tuple(round(a + (b - a) * t) for a, b in zip(top_rgb, bottom_rgb))
            for x in range(width):
                px[x, y] = row
        return img
    return Image.new("RGB", (width, height), hex_to_rgb(bg.get("color_top", "#1c2733")))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_font(draw, text, candidates, start_size, max_width, max_height):
    """Schrift verkleinern, bis der (umbrochene) Text in die Box passt."""
    size = start_size
    while size > 18:
        font = load_font(candidates, size)
        lines = wrap_text(draw, text, font, max_width)
        line_height = round(size * 1.28)
        if len(lines) * line_height <= max_height and \
           all(draw.textlength(l, font=font) <= max_width for l in lines):
            return font, lines, line_height
        size = round(size * 0.94)
    font = load_font(candidates, size)
    lines = wrap_text(draw, text, font, max_width)
    return font, lines, round(size * 1.28)


def render(design: dict, template_name: str, text: str, width: int, height: int) -> Image.Image:
    template = design["templates"][template_name]
    text_cfg = design["text"]
    branding = design["branding"]

    display_text = text.strip()
    if template.get("uppercase"):
        display_text = display_text.upper()
    if template.get("quote_marks", text_cfg.get("quote_marks", False)):
        display_text = f"„{display_text}“"

    img = make_background(design, width, height)
    draw = ImageDraw.Draw(img)

    # Haupttext
    max_text_width = round(width * text_cfg.get("max_width_ratio", 0.78))
    start_size = round(width * template.get("font_size_ratio", 0.062))
    font_candidates = [text_cfg.get("font")] + text_cfg.get("font_fallbacks", [])
    font, lines, line_height = fit_font(
        draw, display_text, font_candidates, start_size,
        max_text_width, round(height * 0.6),
    )
    block_height = len(lines) * line_height
    y = (height - block_height) // 2
    for line in lines:
        line_width = draw.textlength(line, font=font)
        draw.text(((width - line_width) / 2, y), line,
                  font=font, fill=hex_to_rgb(text_cfg.get("color", "#f5f0e8")))
        y += line_height

    # Branding / Copyright-Vermerk
    brand_text = branding.get("text", "© Bernd Bott")
    brand_size = max(round(width * 0.026), 20)
    brand_font = load_font(branding.get("font_fallbacks", []), brand_size)
    margin = round(height * branding.get("margin_ratio", 0.055))
    brand_width = draw.textlength(brand_text, font=brand_font)
    draw.text(((width - brand_width) / 2, height - margin - brand_size), brand_text,
              font=brand_font, fill=hex_to_rgb(branding.get("color", "#c9a35f")))

    # Optionales Logo oberhalb des Branding-Texts
    if branding.get("logo"):
        logo_path = PROJECT_ROOT / branding["logo"]
        if logo_path.exists():
            logo = Image.open(logo_path).convert("RGBA")
            target_h = round(height * branding.get("logo_height_ratio", 0.06))
            ratio = target_h / logo.height
            logo = logo.resize((round(logo.width * ratio), target_h))
            lx = (width - logo.width) // 2
            ly = height - margin - brand_size - target_h - round(height * 0.015)
            img.paste(logo, (lx, ly), logo)

    return img


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9äöüß]+", "-", text.lower()).strip("-")
    return slug[:40] or "grafik"


def main() -> int:
    parser = argparse.ArgumentParser(description="Zitat-Grafik rendern (1:1 + 9:16)")
    parser.add_argument("--template", default="zitat",
                        help="Template: zitat / wort / hook (Default: zitat)")
    parser.add_argument("--text", required=True, help="Der Satz / das Wort für die Grafik")
    parser.add_argument("--name", default=None,
                        help="Basisname der Ausgabedateien (Default: aus dem Text)")
    args = parser.parse_args()

    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    if args.template not in design["templates"]:
        print(f"FEHLER: Unbekanntes Template '{args.template}'. "
              f"Verfügbar: {', '.join(design['templates'])}", file=sys.stderr)
        return 1

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    base = args.name or slugify(args.text)

    outputs = []
    for fmt_name, fmt in design["formats"].items():
        img = render(design, args.template, args.text, fmt["width"], fmt["height"])
        out = WORK_DIR / f"{base}_{args.template}_{fmt_name}.png"
        img.save(out)
        outputs.append(out)

    print("Fertig:")
    for out in outputs:
        print(f"  {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
