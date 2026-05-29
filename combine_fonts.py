"""
Font merge script — run with FontForge's bundled Python (ffpython).

  ffpython.exe combine_fonts.py <font1.ttf> <font2.ttf> <output.ttf>

Merges font2 into font1 (no overlapping glyphs expected between alphabet & symbols).
"""
import sys
import fontforge


def merge_fonts(path1: str, path2: str, output_path: str) -> None:
    font1 = fontforge.open(path1)
    font2 = fontforge.open(path2)

    # Merge all glyphs from font2 into font1
    font1.mergeFonts(font2)

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
