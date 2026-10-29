# ascii-art

Image → ASCII art CLI. Single script: `main.py` (Python 3.12 + Pillow, managed with uv).

## Commands

```bash
uv run main.py IMAGE                       # plain ASCII, 100 columns (reads right on light backgrounds)
uv run main.py IMAGE -i                    # invert shading, for dark terminals
uv run main.py IMAGE -w 150 -d             # wider, 70-character palette for finer shading
uv run main.py IMAGE -c "█▓▒░ "            # custom palette, densest to sparsest

uv run main.py IMAGE -r                    # remove plain or checkerboard background (tolerance 30)
uv run main.py IMAGE -r 170                # remove background with a higher tolerance

uv run main.py IMAGE -r -C -i              # coloured characters, no background, dark terminal
uv run main.py IMAGE -r -b                 # solid colour blocks (█), no background

uv run main.py IMAGE -r -C -i -o out.txt && cat output/out.txt   # save under a custom name, then show
uv run main.py IMAGE -o ~/Desktop/out.txt                         # save outside output/
```

## Output

- Every run saves its result, overwriting files with the same name. No `-o`: prints and saves to `output/<image name>.txt`.
- `-o name.txt` (bare name) saves to `output/name.txt`; `-o dir/name.txt` saves exactly there. With `-o` nothing is printed.
- `output/` sits next to `main.py` regardless of the current directory, and is git-ignored.
- The `saved to ...` line goes to stderr, so `| tee` or `> file` capture only the art.

## Gotchas

- `-r` takes an optional number, so it must come **after** the image path (`main.py IMAGE -r`, not `main.py -r IMAGE`).
- `-t` no longer exists; the tolerance goes right after `-r` (`-r 170`).
- Output with `-C`/`-b` contains ANSI colour codes: `cat` shows colours, a text editor shows `^[[38;2;...m`. Drop `-C` for a clean text file.
- `> file` redirects stdout to a file; `> cat` creates a file named `cat`. Use `&& cat file` to show a saved result.
- Background removal only clears regions connected to the image corners; it does not work on busy photo backgrounds.
