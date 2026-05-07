#!/usr/bin/env python3

import subprocess
import tempfile
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE_SVG = ROOT / "logo-icon-social.svg"
FONT_FILE = ROOT.parent / "app" / "node_modules" / "@fontsource" / "inter" / "files" / "inter-latin-600-normal.woff"
EXPORTS = {
    "logo-icon-social-512.png": 512,
    "logo-icon-social-1024.png": 1024,
    "logo-icon-social-1200.png": 1200,
}
WHITE = "#FFFFFF"
BASE_SIZE = 1024
TEXT_BASELINE_Y = 864
TEXT_FONT_SIZE = 86
TEXT_LETTER_SPACING = -1.9
WORDMARK = "Ledgora"


def scale_value(size: int, value: float) -> float:
    return value * size / BASE_SIZE


def render_icon_background(size: int) -> Image.Image:
    svg_text = SOURCE_SVG.read_text(encoding="utf-8")
    svg_without_text = re.sub(r"\s*<text[\s\S]*?</text>\s*", "\n", svg_text, count=1)
    sized_svg = svg_without_text.replace('width="1024" height="1024"', f'width="{size}" height="{size}"', 1)
    sized_svg = sized_svg.replace(
        "../app/node_modules/@fontsource/inter/files/inter-latin-600-normal.woff",
        FONT_FILE.resolve().as_uri(),
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_svg = Path(temp_dir) / "icon-only.svg"
        temp_png = Path(temp_dir) / "icon-only.png"
        temp_svg.write_text(sized_svg, encoding="utf-8")
        subprocess.run(
            ["sips", "-s", "format", "png", str(temp_svg), "--out", str(temp_png)],
            check=True,
            capture_output=True,
            text=True,
        )
        return Image.open(temp_png).convert("RGBA")


def measure_wordmark(font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, letter_spacing: float) -> float:
    total_width = 0.0
    for index, character in enumerate(WORDMARK):
        total_width += draw.textlength(character, font=font)
        if index < len(WORDMARK) - 1:
            total_width += letter_spacing
    return total_width


def draw_wordmark(
    image: Image.Image,
    size: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    draw = ImageDraw.Draw(image)
    letter_spacing = scale_value(size, TEXT_LETTER_SPACING)
    total_width = measure_wordmark(font, draw, letter_spacing)
    ascent, _ = font.getmetrics()
    baseline_y = scale_value(size, TEXT_BASELINE_Y)
    x_cursor = (size - total_width) / 2
    top_y = baseline_y - ascent

    for index, character in enumerate(WORDMARK):
        draw.text((x_cursor, top_y), character, font=font, fill=WHITE)
        x_cursor += draw.textlength(character, font=font)
        if index < len(WORDMARK) - 1:
            x_cursor += letter_spacing


def render_png(size: int, output_path: Path) -> None:
    image = render_icon_background(size)
    font = ImageFont.truetype(str(FONT_FILE), round(scale_value(size, TEXT_FONT_SIZE)))
    draw_wordmark(image, size, font)
    image.save(output_path, format="PNG")


def main() -> None:
    for filename, size in EXPORTS.items():
        output_path = ROOT / filename
        render_png(size, output_path)
        print(f"wrote {filename} ({size}x{size}) from {SOURCE_SVG.name}")


if __name__ == "__main__":
    main()