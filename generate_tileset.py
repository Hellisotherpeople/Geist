#!/usr/bin/env python3
"""Generate a font-only CP437 tileset PNG for Geist.

This produces a clean text tilesheet for UI rendering.
Pixel-art game sprites are registered separately at runtime via tiles.py.

Run with:  uv run --with pillow python generate_tileset.py [tile_size]
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CP437 = [
    0x0000, 0x263A, 0x263B, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25D8, 0x25CB, 0x25D9, 0x2642, 0x2640, 0x266A, 0x266B, 0x263C,
    0x25BA, 0x25C4, 0x2195, 0x203C, 0x00B6, 0x00A7, 0x25AC, 0x21A8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221F, 0x2194, 0x25B2, 0x25BC,
    *range(0x20, 0x7F), 0x2302,
    0x00C7, 0x00FC, 0x00E9, 0x00E2, 0x00E4, 0x00E0, 0x00E5, 0x00E7,
    0x00EA, 0x00EB, 0x00E8, 0x00EF, 0x00EE, 0x00EC, 0x00C4, 0x00C5,
    0x00C9, 0x00E6, 0x00C6, 0x00F4, 0x00F6, 0x00F2, 0x00FB, 0x00F9,
    0x00FF, 0x00D6, 0x00DC, 0x00A2, 0x00A3, 0x00A5, 0x20A7, 0x0192,
    0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1, 0x00D1, 0x00AA, 0x00BA,
    0x00BF, 0x2310, 0x00AC, 0x00BD, 0x00BC, 0x00A1, 0x00AB, 0x00BB,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255D, 0x255C, 0x255B, 0x2510,
    0x2514, 0x2534, 0x252C, 0x251C, 0x2500, 0x253C, 0x255E, 0x255F,
    0x255A, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256C, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256B,
    0x256A, 0x2518, 0x250C, 0x2588, 0x2584, 0x258C, 0x2590, 0x2580,
    0x03B1, 0x00DF, 0x0393, 0x03C0, 0x03A3, 0x03C3, 0x00B5, 0x03C4,
    0x03A6, 0x0398, 0x03A9, 0x03B4, 0x221E, 0x03C6, 0x03B5, 0x2229,
    0x2261, 0x00B1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00F7, 0x2248,
    0x00B0, 0x2219, 0x00B7, 0x221A, 0x207F, 0x00B2, 0x25A0, 0x00A0,
]

FONT_PATHS = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "C:\\Windows\\Fonts\\consola.ttf",
    "C:\\Windows\\Fonts\\cour.ttf",
]


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_tileset(tile_size: int = 16, output: str = "assets/tileset.png") -> None:
    cols, rows = 16, 16
    width = cols * tile_size
    height = rows * tile_size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    font = _find_font(int(tile_size * 0.85))

    for idx in range(256):
        col = idx % cols
        row = idx // cols
        x0 = col * tile_size
        y0 = row * tile_size
        codepoint = CP437[idx]
        char = chr(codepoint) if codepoint != 0 else " "
        bbox = draw.textbbox((0, 0), char, font=font)
        cw = bbox[2] - bbox[0]
        ch = bbox[3] - bbox[1]
        cx = x0 + (tile_size - cw) // 2 - bbox[0]
        cy = y0 + (tile_size - ch) // 2 - bbox[1]
        draw.text((cx, cy), char, fill=(255, 255, 255, 255), font=font)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    img.save(output)
    print(f"Generated {output} ({width}x{height}, {tile_size}x{tile_size} tiles)")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    generate_tileset(tile_size=size)
