# ascii-art

Convert images to ASCII art in the terminal, with optional colour and background removal.

```
         ====
     =-::::::::-=
    -::::::::::::-
   -:...::::::...:-
  ===++++=--=++++===
 --*##%%%#++##%%%#*--
 --=*####*--*####*=--
  --=--:..::..:--=--
 =+===  . .. .  ===+=
  ====:-.    .-:====
    --=+=-..-=+=--
       ==+==+==
```

<sub>`uv run main.py image.jpg -r -w 50` on an AI-generated image with a checkerboard background.</sub>

## Requirements

- [uv](https://docs.astral.sh/uv/) — it installs the right Python (3.12) and Pillow in a project-local `.venv`, isolated from the rest of the system.

```bash
uv sync   # optional: uv run does it automatically on first use
```

## Usage

```bash
uv run main.py IMAGE [options]
```

| Option | Description |
|---|---|
| `-w, --width N` | Output width in characters (default: 100). |
| `-d, --detailed` | Use a 70-character palette for finer shading. |
| `-c, --charset CHARS` | Custom palette, from densest to sparsest (e.g. `"█▓▒░ "`). |
| `-i, --invert` | Invert shading. Use it on dark terminal backgrounds. |
| `-r, --remove-bg [TOLERANCE]` | Remove a plain or checkerboard background (default tolerance: 30, summed over RGB). Must come **after** the image path. |
| `-C, --color` | Colour each character with its pixel colour (24-bit ANSI). |
| `-b, --blocks` | Draw solid `█` blocks instead of characters (implies `--color`). |
| `-o, --output FILE` | Save to `FILE` instead of printing. A bare file name is saved in `output/`; a path with a directory is used as is. |

### Output

Every result is saved, overwriting any previous file with the same name:

| Command | Prints | Saves to |
|---|---|---|
| `main.py photo.jpg` | yes | `output/photo.txt` |
| `main.py photo.jpg -o arte.txt` | no | `output/arte.txt` |
| `main.py photo.jpg -o ~/Desktop/arte.txt` | no | `~/Desktop/arte.txt` |

`output/` lives next to `main.py` (whatever the current directory) and is git-ignored.

### Examples

```bash
uv run main.py photo.jpg                      # plain ASCII (reads right on light backgrounds)
uv run main.py photo.jpg -i                   # dark terminal
uv run main.py photo.jpg -r -C -i             # coloured, background removed
uv run main.py photo.jpg -r 170               # background removal with higher tolerance
uv run main.py photo.jpg -r -b                # colour blocks, almost photo-like
uv run main.py photo.jpg -r -C -i -o arte.txt && cat output/arte.txt   # save under a custom name, then show
```

## How it works

1. **Orientation** — applies the EXIF rotation, so phone photos come out upright.
2. **Background removal** (`-r`) — detects the dominant border colour, or the two colours of a fake-transparency checkerboard, and flood-fills from the four corners. Only background connected to the edges is cleared, so areas inside the subject with the same colour are kept. Cleared pixels are drawn as spaces.
3. **Downscaling** — resizes to the requested width; height is halved because terminal cells are about twice as tall as they are wide.
4. **Mapping** — each pixel's brightness picks a character from the palette; with `-C`/`-b` each character also gets the pixel's RGB colour.

## Limitations

- Background removal works on plain or checkerboard backgrounds only, not on busy photos (landscapes, rooms).
- If the subject covers more than 25% of the image border, its colour may be mistaken for a second background colour.
- Files saved with `-C`/`-b` contain ANSI colour codes: `cat` shows the colours, a text editor shows `^[[38;2;...m`.
- Colour output needs a terminal with 24-bit colour support (iTerm2, macOS Terminal, VS Code).
