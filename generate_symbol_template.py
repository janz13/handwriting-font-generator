from PIL import Image, ImageDraw, ImageFont
import os
import sys

# A4 / US Letter at 300 DPI for crisp print quality
DPI = 300
WIDTH = int(8.5 * DPI)
HEIGHT = int(11 * DPI)

# Margins (in pixels) – slightly larger for fewer cells
MARGIN = 200

# Grid dimensions: 4 rows x 8 columns = 32 cells
ROWS = 4
COLS = 8

# All standard keyboard symbols (non-alphanumeric)
CHARACTERS = [
    '`', '~', '!', '@', '#', '$', '%', '^',
    '&', '*', '(', ')', '-', '_', '+', '=',
    '[', ']', '{', '}', '|', '\\', ';', ':',
    "'", '"', ',', '.', '<', '>', '/', '?',
]

# Very light gray labels: faintly visible on paper but well above Otsu threshold
LABEL_COLOR = (235, 235, 235)
GRID_COLOR = (0, 0, 0)
BG_COLOR = (255, 255, 255)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try common system fonts; fall back to Pillow's default bitmap font."""
    candidates = [
        ("arial.ttf", size),
        ("calibri.ttf", size),
        ("segoeui.ttf", size),
        ("DejaVuSans.ttf", size),
    ]
    for name, sz in candidates:
        try:
            return ImageFont.truetype(name, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_symbol_template(output_path: str = "symbol_template.png") -> None:
    """Draw a printable handwriting template with a 4x8 grid for symbols."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Calculate drawable grid area
    grid_w = WIDTH - 2 * MARGIN
    grid_h = HEIGHT - 2 * MARGIN
    cell_w = grid_w // COLS
    cell_h = grid_h // ROWS

    # Draw horizontal grid lines
    for r in range(ROWS + 1):
        y = MARGIN + r * cell_h
        draw.line([(MARGIN, y), (MARGIN + grid_w, y)], fill=GRID_COLOR, width=3)

    # Draw vertical grid lines
    for c in range(COLS + 1):
        x = MARGIN + c * cell_w
        draw.line([(x, MARGIN), (x, MARGIN + grid_h)], fill=GRID_COLOR, width=3)

    # Draw handwriting guide lines inside each cell (baseline + x-height)
    # These are light gray so they vanish during Otsu extraction
    guide_color = LABEL_COLOR  # same faint gray as labels
    guide_width = 1
    dash_len = 6
    gap_len = 4

    for r in range(ROWS):
        for c in range(COLS):
            x1 = MARGIN + c * cell_w
            x2 = MARGIN + (c + 1) * cell_w
            y_top = MARGIN + r * cell_h
            y_bot = MARGIN + (r + 1) * cell_h

            # Baseline: solid line near bottom of cell
            y_base = int(y_bot - cell_h * 0.15)
            draw.line([(x1, y_base), (x2, y_base)], fill=guide_color, width=guide_width)

            # X-height / midline: dotted line halfway up from baseline
            y_mid = int(y_bot - cell_h * 0.55)
            x = x1
            while x < x2:
                seg_end = min(x + dash_len, x2)
                draw.line([(x, y_mid), (seg_end, y_mid)], fill=guide_color, width=guide_width)
                x += dash_len + gap_len

    # Place reference labels
    label_font = _load_font(120)
    label_padding_x = 50
    label_padding_y = 40

    idx = 0
    for r in range(ROWS):
        for c in range(COLS):
            if idx >= len(CHARACTERS):
                break
            x = MARGIN + c * cell_w + label_padding_x
            y = MARGIN + r * cell_h + label_padding_y
            draw.text((x, y), CHARACTERS[idx], fill=LABEL_COLOR, font=label_font)
            idx += 1

    img.save(output_path)
    print(f"Symbol template saved to: {os.path.abspath(output_path)}  ({WIDTH}x{HEIGHT} px)")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "symbol_template.png"
    generate_symbol_template(output)
