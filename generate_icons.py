"""
Generate CarTruth PWA icons (192x192 and 512x512) from logo.png.
Requires: pip install Pillow
"""
from PIL import Image
import os


def make_icon(logo_path: str, size: int, out_path: str) -> None:
    bg_color = (13, 13, 20)  # #0d0d14

    # Create square canvas
    canvas = Image.new("RGBA", (size, size), bg_color + (255,))

    # Open logo and convert to RGBA
    logo = Image.open(logo_path).convert("RGBA")

    # Fit logo inside canvas with 15% padding on each side
    pad = int(size * 0.15)
    inner = size - 2 * pad

    # Scale logo to fit within inner square, preserving aspect ratio
    lw, lh = logo.size
    scale = min(inner / lw, inner / lh)
    new_w = int(lw * scale)
    new_h = int(lh * scale)
    logo = logo.resize((new_w, new_h), Image.LANCZOS)

    # Center on canvas
    x = (size - new_w) // 2
    y = (size - new_h) // 2
    canvas.paste(logo, (x, y), logo)

    # Convert to RGB for PNG output
    final = Image.new("RGB", (size, size), bg_color)
    final.paste(canvas, mask=canvas.split()[3])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    final.save(out_path, "PNG")
    print(f"  Saved {out_path}  ({size}x{size})")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(base, "static", "icons")
    logo_path = os.path.join(icons_dir, "logo.png")

    if not os.path.exists(logo_path):
        print(f"ERROR: logo not found at {logo_path}")
        raise SystemExit(1)

    print("Generating CarTruth PWA icons from logo.png…")
    make_icon(logo_path, 512, os.path.join(icons_dir, "icon-512.png"))
    make_icon(logo_path, 192, os.path.join(icons_dir, "icon-192.png"))
    print("Done.")
