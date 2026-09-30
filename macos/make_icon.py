"""Draws the app icon (1024 px) and builds AppIcon.icns with iconutil."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

S = 1024
HERE = os.path.dirname(os.path.abspath(__file__))


def gradient(size, stops):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
                if t0 <= t <= t1:
                    k = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
                    break
    return img


def icon():
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    margin, radius = 100, 185  # macOS icon grid: 824 px body
    body = gradient(S - 2 * margin, [(0, (91, 71, 201)), (.55, (140, 69, 184)), (1, (194, 79, 143))])
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *body.size), radius, fill=255)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((margin, margin + 18, S - margin, S - margin + 18), radius, fill=(40, 20, 80, 110))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)))
    canvas.paste(body, (margin, margin), mask)

    d = ImageDraw.Draw(canvas)
    white, w = (255, 255, 255, 255), 34
    cx = S // 2
    top, mid, bottom = 330, 520, 700
    xs = [cx - 190, cx, cx + 190]
    d.line([(cx, top + 62), (cx, mid)], fill=white, width=w)
    d.line([(xs[0], mid), (xs[2], mid)], fill=white, width=w)
    for x in xs:
        d.line([(x, mid), (x, bottom - 52)], fill=white, width=w)
    d.ellipse((cx - 70, top - 70, cx + 70, top + 70), fill=white)
    for x in xs:
        d.ellipse((x - 56, bottom - 56, x + 56, bottom + 56), fill=white)
    for x, y in [(xs[0], mid), (xs[2], mid)]:
        d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=white)
    return canvas


def main():
    out = os.path.join(HERE, "build", "AppIcon.iconset")
    os.makedirs(out, exist_ok=True)
    base = icon()
    base.save(os.path.join(HERE, "Resources", "icon-1024.png"))
    for size in (16, 32, 128, 256, 512):
        base.resize((size, size), Image.LANCZOS).save(os.path.join(out, f"icon_{size}x{size}.png"))
        base.resize((size * 2, size * 2), Image.LANCZOS).save(os.path.join(out, f"icon_{size}x{size}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", out, "-o", os.path.join(HERE, "Resources", "AppIcon.icns")], check=True)
    print("AppIcon.icns ready")


if __name__ == "__main__":
    sys.exit(main())
