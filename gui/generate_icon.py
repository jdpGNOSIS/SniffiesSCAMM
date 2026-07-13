"""Generate a Sniffies-themed app icon (.ico and .png)."""

from PIL import Image, ImageDraw
import os, math

COLORS = {
    "bg": (15, 5, 30),
    "purple": (120, 50, 255),
    "blue": (50, 100, 255),
    "cyan": (0, 200, 255),
    "green": (0, 255, 180),
    "accent": (255, 50, 120),
}


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = size // 2
    r = size // 2 - 2

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COLORS["bg"])

    for i, color in enumerate([COLORS["purple"], COLORS["blue"], COLORS["cyan"], COLORS["green"]]):
        draw.pieslice(
            [cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2],
            i * 90, (i + 1) * 90, fill=color,
        )

    ir = r // 2
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=COLORS["bg"])

    cr = max(2, size // 12)
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=COLORS["accent"])

    if size >= 32:
        dr = r // 3
        for angle in [0, 60, 120, 180, 240, 300]:
            dx = int(dr * math.cos(math.radians(angle)))
            dy = int(dr * math.sin(math.radians(angle)))
            dotr = max(1, size // 24)
            col = COLORS["purple"] if angle % 120 == 0 else COLORS["blue"]
            draw.ellipse(
                [cx + dx - dotr, cy + dy - dotr, cx + dx + dotr, cy + dy + dotr],
                fill=col,
            )

    return img


def create_ico(out_path: str):
    sizes = [16, 32, 48, 64, 128, 256]
    imgs = [make_icon(s) for s in sizes]
    imgs[0].save(out_path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print(f"ICO: {out_path}")

    # also save a png version
    png_path = out_path.replace(".ico", ".png")
    make_icon(256).save(png_path)
    print(f"PNG: {png_path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "assets", "sniffies.ico")
    create_ico(out)
