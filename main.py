"""Convert an image to ASCII art."""

import argparse
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

# Ordered from densest to sparsest: dark pixels become dense characters, which reads
# correctly as dark text on a light background. Use --invert for dark terminals.
DEFAULT_CHARSET = "@%#*+=-:. "
DETAILED_CHARSET = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
BLOCK = "█"

# Terminal cells are roughly twice as tall as they are wide; compensate so the
# output keeps the image's proportions.
CHAR_ASPECT = 0.5

DEFAULT_BG_TOLERANCE = 30
# A second border colour counts as background (e.g. the two greys of a fake
# "transparency" checkerboard) only if it covers this share of the border;
# otherwise it is just the subject touching the edge.
SECOND_BG_COLOUR_SHARE = 0.25

RGB = tuple[int, int, int]

# Every result is saved here unless -o names a path with its own directory.
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def colour_distance(a: RGB, b: RGB) -> float:
    return sum(abs(x - y) for x, y in zip(a, b))


def dominant_colour(pixels: list[RGB]) -> RGB:
    """Average of the most frequent colour bucket, so JPEG noise is smoothed out."""
    buckets = Counter(tuple(c // 16 for c in p) for p in pixels)
    top = buckets.most_common(1)[0][0]
    members = [p for p in pixels if tuple(c // 16 for c in p) == top]
    return tuple(round(sum(ch) / len(members)) for ch in zip(*members))


def background_colours(image: Image.Image, tolerance: int) -> tuple[RGB, RGB | None]:
    """Detect one background colour, or two when the border is a checkerboard."""
    w, h = image.size
    px = image.load()
    border = [px[x, y] for x in range(w) for y in (0, h - 1)]
    border += [px[x, y] for y in range(h) for x in (0, w - 1)]

    first = dominant_colour(border)
    rest = [p for p in border if colour_distance(p, first) > tolerance]
    if len(rest) < SECOND_BG_COLOUR_SHARE * len(border):
        return first, None
    return first, dominant_colour(rest)


def distance_to_segment(p: RGB, a: RGB, b: RGB | None) -> float:
    """Colour distance from p to the nearest blend of a and b (or to a alone).

    Measuring against the segment, not just its ends, also matches the blended
    pixels along checkerboard square edges, which would otherwise wall off the fill.
    """
    if b is None:
        return colour_distance(p, a)
    d = [y - x for x, y in zip(a, b)]
    t = sum((pc - ac) * dc for pc, ac, dc in zip(p, a, d)) / sum(dc * dc for dc in d)
    t = min(1.0, max(0.0, t))
    return colour_distance(p, tuple(ac + t * dc for ac, dc in zip(a, d)))


def remove_background(image: Image.Image, width: int, tolerance: int) -> Image.Image:
    """Make the background transparent by flood-filling from the four corners.

    Only regions connected to the border are cleared, so areas inside the subject
    that share the background colour are kept. Works for plain or checkerboard
    backgrounds, not for busy photos.
    """
    image = image.convert("RGBA")
    # Per-pixel work is pure Python; shrink first. The ASCII output is far
    # smaller anyway, so 4x its width loses no visible detail.
    image.thumbnail((width * 4, image.height))
    rgb = image.convert("RGB")

    bg_a, bg_b = background_colours(rgb, tolerance)
    mask = Image.new("L", rgb.size)
    mask.putdata([255 if distance_to_segment(p, bg_a, bg_b) <= tolerance else 0 for p in rgb.get_flattened_data()])

    # Mark background-like pixels reachable from a corner as 128; isolated
    # background-like areas inside the subject stay 255 and are kept.
    last_x, last_y = mask.width - 1, mask.height - 1
    for corner in ((0, 0), (last_x, 0), (0, last_y), (last_x, last_y)):
        if mask.getpixel(corner) == 255:
            ImageDraw.floodfill(mask, corner, 128)

    keep = mask.point(lambda v: 0 if v == 128 else 255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), keep))
    return image


def image_to_ascii(
    image: Image.Image,
    width: int,
    charset: str,
    invert: bool,
    transparent: bool = False,
    colour: bool = False,
    blocks: bool = False,
) -> str:
    if invert:
        charset = charset[::-1]

    height = max(1, round(image.height / image.width * width * CHAR_ASPECT))
    size = (width, height)
    gray = image.convert("L").resize(size).tobytes()
    # Transparent pixels (alpha below half) are rendered as blank space.
    alpha = image.convert("RGBA").getchannel("A").resize(size).tobytes() if transparent else None
    rgb = image.convert("RGB").resize(size).tobytes() if colour else None

    scale = (len(charset) - 1) / 255

    def cell(i: int) -> str:
        if alpha is not None and alpha[i] < 128:
            return " "
        ch = BLOCK if blocks else charset[round(gray[i] * scale)]
        if rgb is None:
            return ch
        r, g, b = rgb[3 * i : 3 * i + 3]
        return f"\033[38;2;{r};{g};{b}m{ch}"  # 24-bit ANSI foreground colour

    reset = "\033[0m" if colour else ""
    return "\n".join(
        "".join(cell(i) for i in range(y * width, (y + 1) * width)) + reset
        for y in range(height)
    )


def tolerance_arg(value: str) -> int:
    # -r takes an optional number, so "-r photo.jpg" makes argparse read the path
    # as the tolerance; say how to fix it instead of "invalid int value".
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a number, got {value!r}; put -r after the image path"
        ) from None


def output_path(output: Path | None, image: Path) -> Path:
    """Default to output/<image name>.txt; a bare -o file name also lands in output/."""
    if output is None:
        return OUTPUT_DIR / f"{image.stem}.txt"
    if output.parent == Path("."):
        return OUTPUT_DIR / output
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert an image to ASCII art.")
    parser.add_argument("image", type=Path, help="path to the input image")
    parser.add_argument("-w", "--width", type=int, default=100, help="output width in characters (default: 100)")
    parser.add_argument("-d", "--detailed", action="store_true", help="use a 70-character palette for finer shading")
    parser.add_argument("-c", "--charset", help="custom palette, from densest to sparsest")
    parser.add_argument("-i", "--invert", action="store_true", help="invert shading (for dark terminal backgrounds)")
    parser.add_argument(
        "-r", "--remove-bg", type=tolerance_arg, nargs="?", const=DEFAULT_BG_TOLERANCE, metavar="TOLERANCE",
        help="remove a plain or checkerboard background; optional colour tolerance, "
        f"summed over RGB (default: {DEFAULT_BG_TOLERANCE}). Put it after the image path",
    )
    parser.add_argument("-C", "--color", action="store_true", help="colour each character with its pixel colour (24-bit ANSI)")
    parser.add_argument("-b", "--blocks", action="store_true", help=f"draw solid '{BLOCK}' blocks instead of characters (implies --color)")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="save to this file instead of printing; a bare file name is saved in output/ "
        "(default: print and save to output/<image name>.txt)",
    )
    args = parser.parse_args()

    if args.width < 1:
        parser.error("--width must be positive")
    if args.remove_bg is not None and args.remove_bg < 0:
        parser.error("--remove-bg tolerance must be >= 0")

    charset = args.charset or (DETAILED_CHARSET if args.detailed else DEFAULT_CHARSET)
    if len(charset) < 2:
        parser.error("--charset needs at least 2 characters")

    try:
        with Image.open(args.image) as image:
            image = ImageOps.exif_transpose(image)
    except (FileNotFoundError, OSError) as exc:
        sys.exit(f"error: cannot read image {args.image}: {exc}")

    remove_bg = args.remove_bg is not None
    if remove_bg:
        image = remove_background(image, args.width, args.remove_bg)
    art = image_to_ascii(
        image, args.width, charset, args.invert,
        transparent=remove_bg, colour=args.color or args.blocks, blocks=args.blocks,
    )

    output = output_path(args.output, args.image)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(art + "\n", encoding="utf-8")
    if args.output is None:
        print(art)
    # stderr, so "| tee" or "> file" capture only the art.
    print(f"saved to {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
