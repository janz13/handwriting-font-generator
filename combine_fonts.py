"""
Font merge script — run with FontForge's bundled Python (ffpython).

  ffpython.exe combine_fonts.py <font1.ttf> <font2.ttf> <output.ttf>

Copies glyphs from font2 into font1 (no overlapping glyphs expected).
"""
import sys
import traceback
import fontforge


def merge_fonts(path1: str, path2: str, output_path: str) -> None:
    font1 = fontforge.open(path1)
    font2 = fontforge.open(path2)

    # Copy each glyph from font2 into font1 individually.
    # mergeFonts() is missing in some older FontForge builds, so we do it manually.
    for glyph in font2.glyphs():
        if glyph.unicode == -1:
            continue  # skip .notdef and other unencoded glyphs
        try:
            source = font2[glyph.unicode]
            target = font1.createChar(glyph.unicode)
            target.clear()
            # Use the foreground property (widely supported across versions)
            target.foreground = source.foreground
            target.width = source.width
        except Exception as exc:
            print(f"  [warn] Could not copy glyph U+{glyph.unicode:04X}: {exc}")
            continue

    # Ensure space character exists
    if 0x0020 not in [g.unicode for g in font1.glyphs()]:
        space = font1.createChar(0x0020)
        space.width = int(font1.em * 0.25)

    font1.generate(output_path, flags=("opentype",))
    print(f"Combined font saved to {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: ffpython.exe combine_fonts.py <font1.ttf> <font2.ttf> <output.ttf>")
        sys.exit(1)

    try:
        merge_fonts(sys.argv[1], sys.argv[2], sys.argv[3])
    except Exception:
        traceback.print_exc()
        sys.exit(1)
