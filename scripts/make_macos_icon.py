"""Build a simple focus reticle app icon without external image assets."""

from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


out = Path("build_assets")
iconset = out / "FocusViewer.iconset"
iconset.mkdir(parents=True, exist_ok=True)

def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    pad = int(size * 0.06)
    radius = int(size * 0.22)
    d.rounded_rectangle((pad, pad, size-pad, size-pad), radius=radius,
                        fill="#17202b")
    mid = size / 2
    r = size * 0.27
    stroke = max(2, int(size * 0.052))
    c = "#ff4d5b"
    length = size * 0.13
    inset = size * 0.025
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = mid + sx*r, mid + sy*r
            d.line((x, y, x - sx*length, y), fill=c, width=stroke)
            d.line((x, y, x, y - sy*length), fill=c, width=stroke)
    dot = size * 0.055
    d.ellipse((mid-dot, mid-dot, mid+dot, mid+dot), fill="#f3f6fa")
    return image

for logical in (16, 32, 128, 256, 512):
    draw_icon(logical).save(iconset / f"icon_{logical}x{logical}.png")
    draw_icon(logical * 2).save(iconset / f"icon_{logical}x{logical}@2x.png")
subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out / "FocusViewer.icns")], check=True)
