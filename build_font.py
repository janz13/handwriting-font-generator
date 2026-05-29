import os
import sys
import argparse
import tempfile
import shutil
import subprocess
from typing import Dict, List, Tuple

import cv2
import numpy as np

try:
    import fontforge
    HAS_FONTFORGE = True
except ImportError:
    fontforge = None  # type: ignore
    HAS_FONTFORGE = False


# Mode-specific character sets
_ALPHABET_CHARS: List[str] = (
    [chr(c) for c in range(ord('A'), ord('Z') + 1)] +
    [chr(c) for c in range(ord('a'), ord('z') + 1)] +
    [chr(c) for c in range(ord('0'), ord('9') + 1)]
)

_SYMBOL_CHARS: List[str] = [
    '`', '~', '!', '@', '#', '$', '%', '^',
    '&', '*', '(', ')', '-', '_', '+', '=',
    '[', ']', '{', '}', '|', '\\', ';', ':',
    "'", '"', ',', '.', '<', '>', '/', '?',
]


def _char_to_filename(char: str) -> str:
    """Convert a character to a unique filename, e.g. 'A' → 'U+0041.png'."""
    return f"U+{ord(char):04X}.png"


def _get_mode_chars(mode: str) -> List[str]:
    """Return the character list for the given mode."""
    if mode == "alphabet":
        return _ALPHABET_CHARS
    if mode == "symbols":
        return _SYMBOL_CHARS
    raise ValueError(f"Unknown mode: {mode}")


_DEFAULT_POTRACE = shutil.which("potrace") or r"C:\Users\test\Downloads\potrace-1.16.win64\potrace-1.16.win64\potrace.exe"


def _find_potrace(potrace_path: str) -> str:
    """Return the resolved potrace executable path or raise FileNotFoundError."""
    path = os.path.expanduser(potrace_path)
    if os.path.isfile(path):
        return path
    # Fallback: search PATH
    found = shutil.which("potrace")
    if found:
        return found
    raise FileNotFoundError(
        f"potrace executable not found: {path}\n"
        f"Please install potrace or pass the correct path with --potrace."
    )


def _normalize_strokes(binary_img: np.ndarray) -> np.ndarray:
    """
    Normalize stroke width using morphological opening.

    This thins slightly-thick strokes and removes small noise specks,
    producing more uniform line weight across all glyphs.
    """
    # A 2x2 kernel is aggressive enough to thin most over-thick strokes
    # without destroying thin ones entirely.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    opened = cv2.morphologyEx(binary_img, cv2.MORPH_OPEN, kernel)
    return opened


def png_to_svg(
    png_path: str,
    svg_path: str,
    potrace_path: str = _DEFAULT_POTRACE,
    normalize: bool = False,
) -> None:
    """
    Convert a binary PNG image to an SVG outline using potrace.

    potrace works most reliably with BMP on Windows, so the PNG is first
    converted to a temporary BMP before tracing.
    """
    exe = _find_potrace(potrace_path)

    img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {png_path}")

    # Ensure pure black-and-white (handwriting = black, background = white)
    _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    if normalize:
        binary = _normalize_strokes(binary)

    fd, bmp_path = tempfile.mkstemp(suffix='.bmp')
    os.close(fd)
    try:
        cv2.imwrite(bmp_path, binary)
        result = subprocess.run(
            [exe, '-s', '-o', svg_path, bmp_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"potrace failed for {png_path}: {result.stderr.strip()}"
            )
    finally:
        try:
            os.remove(bmp_path)
        except OSError:
            pass


def _scale_and_position_glyph(glyph, reference_height=None) -> None:
    """
    Uniformly scale the glyph so its height fits comfortably inside the em square,
    then shift it to sit on a reasonable baseline.

    If *reference_height* is provided, tiny glyphs are prevented from being
    blown up by capping the denominator at *reference_height*.
    """
    bbox = glyph.boundingBox()
    height = bbox[3] - bbox[1]
    if height <= 0:
        return

    # Scale so glyph height occupies ~70 % of the em square
    target_height = glyph.font.em * 0.7
    if reference_height and reference_height > 0:
        scale = target_height / max(height, reference_height)
    else:
        scale = target_height / height
    glyph.transform((scale, 0, 0, scale, 0, 0))

    # Recompute bbox after scaling
    bbox = glyph.boundingBox()
    # Shift so the bottom sits slightly above the baseline (em * 0.15)
    x_shift = 50
    y_shift = (glyph.font.em * 0.15) - bbox[1]
    glyph.transform((1, 0, 0, 1, x_shift, y_shift))


def _set_glyph_spacing(glyph, left: int = 30, right: int = 30) -> None:
    """Set side bearings based on the glyph's actual outline width."""
    bbox = glyph.boundingBox()
    outline_width = bbox[2] - bbox[0]
    glyph.width = int(outline_width + left + right)
    glyph.left_side_bearing = left
    glyph.right_side_bearing = right


def _find_ffpython() -> str:
    """Locate FontForge's bundled Python (ffpython / ffpython3)."""
    # Windows-specific paths
    candidates = [
        r"C:\Program Files\FontForgeBuilds\bin\ffpython.exe",
        r"C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    # Cross-platform: search PATH for ffpython or ffpython3
    for name in ("ffpython", "ffpython3"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError(
        "ffpython not found. Please install FontForge or add it to PATH."
    )


def _delegate_to_ffpython(svg_dir: str, output_path: str, mode: str = "alphabet") -> None:
    """Invoke FontForge's Python to run fontforge_assemble.py."""
    try:
        ffpython = _find_ffpython()
    except FileNotFoundError:
        # Fallback: try the current Python interpreter directly
        # (works in Docker where python3-fontforge is installed but
        # no separate ffpython binary exists)
        ffpython = sys.executable
    assemble_script = os.path.join(os.path.dirname(__file__), "fontforge_assemble.py")
    if not os.path.isfile(assemble_script):
        raise FileNotFoundError(
            f"Helper script not found: {assemble_script}\n"
            "Ensure fontforge_assemble.py is in the same directory as build_font.py."
        )
    print(f"\nDelegating font assembly to FontForge's Python:\n  {ffpython}\n")
    result = subprocess.run(
        [ffpython, assemble_script, svg_dir, os.path.abspath(output_path), mode],
        capture_output=True, text=True
    )
    # Stream subprocess output back to user
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"Font assembly failed (exit {result.returncode}).\n"
            "See error output above for details."
        )


def build_ttf(
    input_dir: str,
    output_path: str,
    potrace_path: str = _DEFAULT_POTRACE,
    normalize: bool = False,
    mode: str = "alphabet",
) -> Tuple[int, List[str]]:
    """
    Iterate over the expected PNGs, trace them to SVG, import into a new
    FontForge font, and generate a TrueType file.

    Args:
        input_dir: Directory with the PNG letter images.
        output_path: Path for the generated .ttf file.
        potrace_path: Path to the potrace executable (default uses _DEFAULT_POTRACE).
        mode: 'alphabet' or 'symbols'.

    Returns:
        (success_count, missing_chars)
    """
    characters = _get_mode_chars(mode)
    char_map = {c: ord(c) for c in characters}
    missing: List[str] = []
    processed = 0

    # Temporary workspace for intermediate SVGs
    svg_dir = tempfile.mkdtemp(prefix='font_svgs_')
    try:
        # ---- Trace all PNGs -> SVGs ----
        print(f"Tracing PNG images to SVG outlines (mode={mode}) …\n")
        for char in characters:
            png_name = _char_to_filename(char)
            png_path = os.path.join(input_dir, png_name)
            if not os.path.exists(png_path):
                missing.append(char)
                print(f"  [skip] {png_name} not found")
                continue

            svg_name = png_name.replace('.png', '.svg')
            svg_path = os.path.join(svg_dir, svg_name)
            try:
                png_to_svg(png_path, svg_path, potrace_path=potrace_path, normalize=normalize)
                processed += 1
                print(f"  [ok]   {png_name} -> {svg_name}")
            except Exception as exc:
                print(f"  [err]  {char}: {exc}")
                missing.append(char)

        if processed == 0:
            raise RuntimeError("No PNGs were successfully traced; aborting.")

        # ---- Font assembly ----
        if HAS_FONTFORGE:
            # Inline assembly when fontforge is importable
            print("\nAssembling font …\n")
            font = fontforge.font()
            font.fontname = "MyHandwriting"
            font.fullname = "My Handwriting"
            font.familyname = "MyHandwriting"
            font.version = "001.000"
            font.copyright = "Generated by handwriting-font pipeline"
            font.encoding = "UnicodeFull"
            font.em = 1000

            # ---- First pass: import all glyphs and collect heights ----
            glyph_map = {}
            heights = []
            for char in characters:
                svg_name = _char_to_filename(char).replace('.png', '.svg')
                svg_path = os.path.join(svg_dir, svg_name)
                if not os.path.exists(svg_path):
                    continue
                try:
                    codepoint = char_map[char]
                    glyph = font.createChar(codepoint)
                    glyph.importOutlines(svg_path)
                    glyph.removeOverlap()
                    glyph_map[char] = glyph
                    bbox = glyph.boundingBox()
                    h = bbox[3] - bbox[1]
                    if h > 0:
                        heights.append(h)
                    print(f"  [ok]   {char}  ->  U+{codepoint:04X}")
                except Exception as exc:
                    print(f"  [err]  {char}: {exc}")

            # Compute reference height from 75th percentile so tiny glyphs
            # (period, comma, quotes) aren't blown up to full cap-height.
            if heights:
                heights_sorted = sorted(heights)
                reference_height = heights_sorted[int(len(heights_sorted) * 0.75)]
            else:
                reference_height = None

            # ---- Second pass: scale and set spacing consistently ----
            for char, glyph in glyph_map.items():
                _scale_and_position_glyph(glyph, reference_height=reference_height)
                _set_glyph_spacing(glyph, left=30, right=30)

            # Add space character so words don't show missing-glyph boxes
            space = font.createChar(0x0020)
            space.width = int(font.em * 0.25)

            font.generate(output_path, flags=("opentype",))
            print(f"\nSuccess: generated '{output_path}' with {processed} glyphs.")
            if missing:
                print(f"Missing characters ({len(missing)}): {', '.join(missing)}")
        else:
            # Delegate to FontForge's bundled Python
            _delegate_to_ffpython(svg_dir, output_path, mode=mode)

    finally:
        shutil.rmtree(svg_dir, ignore_errors=True)

    return processed, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile extracted PNG letter images into a TrueType font."
    )
    parser.add_argument(
        '-i', '--input', default='extracted_letters',
        help="Directory containing A.png … Z.png, a.png … z.png, 0.png … 9.png"
    )
    parser.add_argument(
        '-o', '--output', default='MyHandwriting.ttf',
        help="Output TrueType font filename"
    )
    parser.add_argument(
        '--potrace', default=_DEFAULT_POTRACE,
        help='Path to the potrace executable (default: %(default)s)'
    )
    parser.add_argument(
        '--normalize', action='store_true',
        help='Normalize stroke width before tracing (thins thick strokes)'
    )
    parser.add_argument(
        '--mode', choices=['alphabet', 'symbols'], default='alphabet',
        help='Font mode: alphabet (default) or symbols'
    )
    args = parser.parse_args()

    build_ttf(args.input, args.output, potrace_path=args.potrace, normalize=args.normalize, mode=args.mode)


if __name__ == '__main__':
    main()
