import cv2
import numpy as np
import os
import argparse
from typing import List, Tuple


def detect_line_positions(proj: np.ndarray, min_gap: int = 40) -> List[int]:
    """Detect line centers from a 1D projection array, merging lines that are too close."""
    threshold = np.max(proj) * 0.15
    positions = []
    in_line = False
    start = 0

    for i, val in enumerate(proj):
        if val > threshold and not in_line:
            in_line = True
            start = i
        elif val <= threshold and in_line:
            in_line = False
            center = (start + i) // 2
            if positions and center - positions[-1] < min_gap:
                # Merge with previous line (take average center)
                positions[-1] = (positions[-1] + center) // 2
            else:
                positions.append(center)

    if in_line:
        center = (start + len(proj) - 1) // 2
        if positions and center - positions[-1] < min_gap:
            positions[-1] = (positions[-1] + center) // 2
        else:
            positions.append(center)

    return positions


def detect_grid(image: np.ndarray) -> Tuple[List[int], List[int]]:
    """
    Detect horizontal and vertical grid line positions using morphological operations.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    h, w = gray.shape

    # Invert binary so dark lines become white for detection
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Adaptive kernel sizes based on image dimensions
    h_kernel_w = max(w // 20, 20)
    v_kernel_h = max(h // 20, 20)

    # Detect horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_w, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
    h_proj = np.sum(h_lines, axis=1)
    h_positions = detect_line_positions(h_proj)

    # Detect vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_h))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
    v_proj = np.sum(v_lines, axis=0)
    v_positions = detect_line_positions(v_proj)

    return h_positions, v_positions


def extract_cells(image: np.ndarray, h_positions: List[int], v_positions: List[int]) -> List[np.ndarray]:
    """
    Extract cell images from the regions between detected grid lines.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    h_positions = sorted(set(h_positions))
    v_positions = sorted(set(v_positions))

    cells = []
    margin = 3  # Margin to avoid including grid lines

    for i in range(len(h_positions) - 1):
        for j in range(len(v_positions) - 1):
            y1 = h_positions[i] + margin
            y2 = h_positions[i + 1] - margin
            x1 = v_positions[j] + margin
            x2 = v_positions[j + 1] - margin

            if y2 > y1 and x2 > x1:
                cell = gray[y1:y2, x1:x2].copy()
                cells.append(cell)

    return cells


def process_and_save(cell: np.ndarray, output_path: str) -> None:
    """
    Apply binary threshold to make handwriting black and background white, then save.
    """
    if cell.size == 0:
        cell = np.ones((50, 50), dtype=np.uint8) * 255

    # Slight blur to reduce scanner noise before thresholding
    blurred = cv2.GaussianBlur(cell, (3, 3), 0)

    # Otsu threshold: black text (0) on white background (255)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    cv2.imwrite(output_path, binary)


def save_verification_montage(
    cells: List[np.ndarray],
    characters: List[str],
    output_path: str,
    cols: int = 9,
) -> None:
    """
    Build a diagnostic image showing every extracted cell with its assigned
    character label, arranged in the same grid layout as the template.
    """
    if not cells:
        return

    # Determine a consistent thumbnail size
    thumb_h = max(c.shape[0] for c in cells)
    thumb_w = max(c.shape[1] for c in cells)
    pad = 8
    label_h = 30

    rows_needed = (len(cells) + cols - 1) // cols
    W = cols * (thumb_w + pad) + pad
    H = rows_needed * (thumb_h + label_h + pad) + pad

    montage = np.ones((H, W, 3), dtype=np.uint8) * 240  # light gray background

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2

    for idx, cell in enumerate(cells):
        if idx >= len(characters):
            break
        r = idx // cols
        c = idx % cols
        x = pad + c * (thumb_w + pad)
        y = pad + r * (thumb_h + label_h + pad)

        # Resize cell to thumbnail size (pad with white)
        thumb = np.ones((thumb_h, thumb_w), dtype=np.uint8) * 255
        ch, cw = cell.shape[:2]
        off_y = (thumb_h - ch) // 2
        off_x = (thumb_w - cw) // 2
        thumb[off_y:off_y + ch, off_x:off_x + cw] = cell

        # Place cell
        montage[y + label_h:y + label_h + thumb_h, x:x + thumb_w, :] = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)

        # Draw label (character name + index)
        label = f"{characters[idx]} ({idx})"
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        tx = x + (thumb_w - tw) // 2
        ty = y + label_h - 6
        cv2.putText(montage, label, (tx, ty), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

    cv2.imwrite(output_path, montage)
    print(f"Saved verification montage to {output_path}")


# Mode-specific character sets with Unicode hex filenames
_ALPHABET_CHARS = (
    [chr(c) for c in range(ord('A'), ord('Z') + 1)] +
    [chr(c) for c in range(ord('a'), ord('z') + 1)] +
    [chr(c) for c in range(ord('0'), ord('9') + 1)]
)

_SYMBOL_CHARS = [
    '`', '~', '!', '@', '#', '$', '%', '^',
    '&', '*', '(', ')', '-', '_', '+', '=',
    '[', ']', '{', '}', '|', '\\', ';', ':',
    "'", '"', ',', '.', '<', '>', '/', '?',
]

_MODE_CONFIG = {
    "alphabet": {"chars": _ALPHABET_CHARS, "cols": 9, "expected": 62},
    "symbols": {"chars": _SYMBOL_CHARS, "cols": 8, "expected": 32},
}


def _char_to_filename(char: str) -> str:
    """Convert a character to a unique filename, e.g. 'A' → 'U+0041.png'."""
    return f"U+{ord(char):04X}.png"


def _filename_to_char(filename: str) -> str:
    """Parse a Unicode filename back to a character, e.g. 'U+0041.png' → 'A'."""
    stem = os.path.splitext(filename)[0]  # remove .png
    if stem.startswith("U+"):
        return chr(int(stem[2:], 16))
    raise ValueError(f"Unexpected filename format: {filename}")


def extract_letters(image_path: str, output_dir: str, mode: str = "alphabet") -> int:
    """
    Extract handwritten characters from a scanned grid template.

    Args:
        image_path: Path to the scanned grid image.
        output_dir: Directory to save extracted PNGs and diagnostics.
        mode: 'alphabet' (A-Z, a-z, 0-9) or 'symbols' (32 keyboard symbols).

    Returns:
        Number of cells successfully extracted.
    """
    if mode not in _MODE_CONFIG:
        raise ValueError(f"Unknown mode: {mode}. Use 'alphabet' or 'symbols'.")

    cfg = _MODE_CONFIG[mode]
    char_list = cfg["chars"]
    expected = cfg["expected"]
    cols = cfg["cols"]

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    print(f"Loaded image: {image.shape[1]}x{image.shape[0]} (mode={mode})")

    h_pos, v_pos = detect_grid(image)
    print(f"Detected {len(h_pos)} horizontal lines and {len(v_pos)} vertical lines")

    if len(h_pos) < 2 or len(v_pos) < 2:
        raise RuntimeError(
            "Could not detect sufficient grid lines. "
            "Ensure the scanned image has clear horizontal and vertical grid lines."
        )

    # Always save grid-line debug overlay
    debug_img = image.copy()
    for y in h_pos:
        cv2.line(debug_img, (0, y), (debug_img.shape[1], y), (0, 0, 255), 2)
    for x in v_pos:
        cv2.line(debug_img, (x, 0), (x, debug_img.shape[0]), (0, 255, 0), 2)
    debug_path = os.path.join(output_dir, '_debug.png')
    os.makedirs(output_dir, exist_ok=True)
    cv2.imwrite(debug_path, debug_img)
    print(f"Saved grid debug image to {debug_path}")

    cells = extract_cells(image, h_pos, v_pos)
    print(f"Extracted {len(cells)} cells")

    if len(cells) != expected:
        print(f"Warning: Expected {expected} cells, but found {len(cells)}")

    os.makedirs(output_dir, exist_ok=True)

    count = 0
    for idx, cell in enumerate(cells):
        if idx >= len(char_list):
            break
        char = char_list[idx]
        filename = _char_to_filename(char)
        out_path = os.path.join(output_dir, filename)
        process_and_save(cell, out_path)
        count += 1
        print(f"  -> {filename}")

    # Save verification montage so user can confirm mapping
    montage_path = os.path.join(output_dir, '_verification.png')
    save_verification_montage(cells, char_list, montage_path, cols=cols)

    print(f"\nDone. Saved {count} images to '{output_dir}/'")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Extract handwritten characters from a scanned grid template. '
                    'Supports alphabet (A-Z, a-z, 0-9) or symbols mode.'
    )
    parser.add_argument('image_path', help='Path to the scanned grid image')
    parser.add_argument(
        '-o', '--output', default='extracted_letters',
        help='Output directory for extracted images'
    )
    parser.add_argument(
        '--mode', choices=['alphabet', 'symbols'], default='alphabet',
        help='Template mode: alphabet (default) or symbols'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Save a debug visualization of detected grid lines (always on)'
    )
    args = parser.parse_args()

    extract_letters(args.image_path, args.output, mode=args.mode)


if __name__ == '__main__':
    main()
