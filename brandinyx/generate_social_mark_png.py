#!/usr/bin/env python3
"""Render canonical AtonixCorp social SVGs as square PNGs."""

from pathlib import Path

import cairosvg


ROOT = Path(__file__).resolve().parent
EXPORTS = {
    "atonixcorp-social-mark.svg": {
        "atonixcorp-social-mark-512.png": 512,
        "atonixcorp-social-mark-1024.png": 1024,
    },
    "atonixcorp-social-lockup.svg": {
        "atonixcorp-social-lockup-512.png": 512,
        "atonixcorp-social-lockup-1024.png": 1024,
    },
}
def main():
    for source_name, output_sizes in EXPORTS.items():
        source = ROOT / source_name
        for filename, size in output_sizes.items():
            output = ROOT / filename
            cairosvg.svg2png(
                url=str(source),
                write_to=str(output),
                output_width=size,
                output_height=size,
            )
            print(f"wrote {output.name} ({size}x{size})")


if __name__ == "__main__":
    main()