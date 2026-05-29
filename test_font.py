"""Render a pangram using the generated handwriting font for visual verification."""
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "MyHandwriting.ttf"
SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog 12345"

# Canvas size
W, H = 1200, 400
BG = (255, 255, 255)
FG = (0, 0, 0)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# Try the custom font at a readable size
try:
    font = ImageFont.truetype(FONT_PATH, 60)
    font_ok = True
except OSError:
    font = ImageFont.load_default()
    font_ok = False

# Center text
bbox = draw.textbbox((0, 0), SAMPLE_TEXT, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (W - text_w) // 2
y = (H - text_h) // 2

draw.text((x, y), SAMPLE_TEXT, font=font, fill=FG)

# Status label
status = f"Font loaded OK: {font_ok}"
if not font_ok:
    status += " (fallback bitmap font used)"
draw.text((20, H - 40), status, fill=(180, 0, 0) if not font_ok else (0, 128, 0))

out = "font_preview.png"
img.save(out)
print(f"Preview saved: {out}")
print(f"  Font path : {FONT_PATH}")
print(f"  Text      : {SAMPLE_TEXT}")
print(f"  Font OK   : {font_ok}")
