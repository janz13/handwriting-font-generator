"""
Font merge script — run with FontForge's bundled Python (ffpython).

  ffpython.exe combine_fonts.py <font1.ttf> <font2.ttf> <output.ttf>

Copies glyphs from font2 into font1 (no overlapping glyphs expected).
"""
import sys
import fontforge


def merge_fonts(path1: str, path2: str, output_path: str) -> None:
    font1 = fontforge.open(path1)
    font2 = fontforge.open(path2)

    # Copy each glyph from font2 into font1 individually.
    # mergeFonts() is missing in some older FontForge builds, so we do it manually.
    for glyph in font2.glyphs():
        if glyph.unicode == -1:
            continue  # skip .notdef and other unencoded glyphs
        # Overwrite or create the glyph at the same codepoint in font1
        target = font1.createChar(glyph.unicode)
        target.clear()
        # Duplicate the foreground layer (layer index 1)
        target.layers[1] = glyph.layers[1].dup()
        target.width = glyph.width
        target.left_side_bearing = glyph.left_side_bearing
        target.right_side_bearing = glyph.right_side_bearing

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

    merge_fonts(sys.argv[1], sys.argv[2], sys.argv[3])
