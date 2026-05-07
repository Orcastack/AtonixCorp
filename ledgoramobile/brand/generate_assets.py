#!/usr/bin/env python3
"""
Ledgora Brand Asset Generator
Renders brand SVGs to PNG at every required mobile density.

Usage:
    python3 brand/generate_assets.py

Outputs:
    iOS     → ios/ledgoramobile/Images.xcassets/AppIcon.appiconset/
              ios/ledgoramobile/Images.xcassets/SplashIcon.imageset/
    Android → android/app/src/main/res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/
"""

import os
import cairosvg

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(BASE, '..')
ANDROID = os.path.join(PROJECT, 'android/app/src/main/res')
IOS_XCA = os.path.join(PROJECT, 'ios/ledgoramobile/Images.xcassets')

# ── SVG source paths ──────────────────────────────────────────────────────────
ICON_APP_SVG   = os.path.join(BASE, 'icon-app.svg')    # opaque, for raster icons
ICON_MARK_SVG  = os.path.join(BASE, 'icon-mark.svg')   # transparent bg, for splash


def render(svg_path: str, output_path: str, size: int) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cairosvg.svg2png(
        url=svg_path,
        write_to=output_path,
        output_width=size,
        output_height=size,
    )
    rel = os.path.relpath(output_path, PROJECT)
    print(f"  ✓  {size:>4}×{size:<4}  {rel}")


def render_padded_foreground(svg_path: str, output_path: str, canvas: int) -> None:
    """
    Render the shield mark inside an Android adaptive-icon canvas.
    The safe zone occupies the central 72/108 = 66.7% of the canvas.
    We scale the 64×64 icon into the safe zone with 18dp padding on each side.
    """
    scale  = (72 / 108) * canvas / 64   # safe-zone scale
    offset = (canvas - 64 * scale) / 2  # padding to centre icon
    with open(svg_path, 'r') as f:
        inner = f.read()
    wrapped = (
        f'<svg width="{canvas}" height="{canvas}" '
        f'viewBox="0 0 {canvas} {canvas}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="translate({offset:.3f},{offset:.3f}) scale({scale:.4f})">'
        f'{inner}'
        f'</g></svg>'
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cairosvg.svg2png(
        bytestring=wrapped.encode('utf-8'),
        write_to=output_path,
        output_width=canvas,
        output_height=canvas,
    )
    rel = os.path.relpath(output_path, PROJECT)
    print(f"  ✓  {canvas:>4}×{canvas:<4}  {rel}")


def main() -> None:
    # ── iOS App Icons ─────────────────────────────────────────────────────────
    print('\n── iOS App Icons ─────────────────────────────────────────────')
    ios_icon_dir = os.path.join(IOS_XCA, 'AppIcon.appiconset')
    for size in [40, 58, 60, 80, 87, 120, 180, 1024]:
        render(ICON_APP_SVG, os.path.join(ios_icon_dir, f'icon-{size}.png'), size)

    # ── iOS Splash Icon (shield mark on transparent bg) ───────────────────────
    print('\n── iOS Splash Icon ───────────────────────────────────────────')
    ios_splash_dir = os.path.join(IOS_XCA, 'SplashIcon.imageset')
    for size, scale in [(96, '1x'), (192, '2x'), (288, '3x')]:
        render(ICON_MARK_SVG,
               os.path.join(ios_splash_dir, f'splash-icon@{scale}.png'), size)

    # ── Android Legacy PNG Icons ───────────────────────────────────────────────
    print('\n── Android Legacy PNG Icons ──────────────────────────────────')
    android_densities = {
        'mipmap-mdpi':    48,
        'mipmap-hdpi':    72,
        'mipmap-xhdpi':   96,
        'mipmap-xxhdpi':  144,
        'mipmap-xxxhdpi': 192,
    }
    for density, size in android_densities.items():
        d = os.path.join(ANDROID, density)
        render(ICON_APP_SVG, os.path.join(d, 'ic_launcher.png'),       size)
        render(ICON_APP_SVG, os.path.join(d, 'ic_launcher_round.png'), size)

    # ── Android Adaptive Icon Foreground (108dp canvas, icon in 72dp safe zone)
    print('\n── Android Adaptive Foreground PNGs ──────────────────────────')
    adaptive_canvas = {
        'mipmap-mdpi':    108,
        'mipmap-hdpi':    162,
        'mipmap-xhdpi':   216,
        'mipmap-xxhdpi':  324,
        'mipmap-xxxhdpi': 432,
    }
    for density, canvas in adaptive_canvas.items():
        d = os.path.join(ANDROID, density)
        render_padded_foreground(
            ICON_MARK_SVG,
            os.path.join(d, 'ic_launcher_foreground.png'),
            canvas,
        )

    print('\n── Complete ──────────────────────────────────────────────────\n')


if __name__ == '__main__':
    main()
