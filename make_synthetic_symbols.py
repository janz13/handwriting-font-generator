"""Create a synthetic 'scanned' symbol grid for testing."""
from PIL import Image, ImageDraw, ImageFont
import random

random.seed(42)

# Load the blank symbol template
img = Image.open("symbol_template.png").convert("RGB")
draw = ImageDraw.Draw(img)

MARGIN = 200
ROWS = 4
COLS = 8
WIDTH, HEIGHT = img.size
grid_w = WIDTH - 2 * MARGIN
grid_h = HEIGHT - 2 * MARGIN
cell_w = grid_w // COLS
cell_h = grid_h // ROWS

CHARACTERS = [
    '`', '~', '!', '@', '#', '$', '%', '^',
    '&', '*', '(', ')', '-', '_', '+', '=',
    '[', ']', '{', '}', '|', '\\', ';', ':',
    "'", '"', ',', '.', '<', '>', '/', '?',
]

# Try to load a font
try:
    font = ImageFont.truetype("calibri.ttf", cell_h // 3)
except OSError:
    font = ImageFont.load_default()

for idx, char in enumerate(CHARACTERS):
    r = idx // COLS
    c = idx % COLS
    x1 = MARGIN + c * cell_w + 40
    y1 = MARGIN + r * cell_h + 40
    x2 = MARGIN + (c + 1) * cell_w - 40
    y2 = MARGIN + (r + 1) * cell_h - 40

    # Slight random offset
    ox = random.randint(-15, 15)
    oy = random.randint(-15, 15)
    draw.text((x1 + ox, y1 + oy), char, fill=(0, 0, 0), font=font)

    # Add a few random scribble lines
    for _ in range(random.randint(2, 5)):
        sx = random.randint(x1, x2)
        sy = random.randint(y1, y2)
        ex = random.randint(x1, x2)
        ey = random.randint(y1, y2)
        draw.line([(sx, sy), (ex, ey)], fill=(0, 0, 0), width=3)

# Save
img.save("synthetic_symbols.png")
print("Saved synthetic_symbols.png")
