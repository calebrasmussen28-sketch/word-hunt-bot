# word-hunt-bot

A Python Word Hunt bot for a Mac desktop workflow where an iPhone is mirrored in
QuickTime Player and mouse gestures are forwarded to the phone through Apple's
Switch Control network link.

The script solves a 4x4 Word Hunt board, calibrates the on-screen board location
inside the QuickTime window, then uses `pyautogui` to drag the Mac cursor across
the mirrored tiles.

## Requirements

- macOS with Python 3 installed
- An iPhone connected by USB and displayed in QuickTime Player via
  **File > New Movie Recording**
- Switch Control configured so Mac mouse actions are sent to the iPhone
- A local newline-delimited English dictionary file
- Python package:

```bash
python3 -m pip install pyautogui
```

## Dictionary setup

The solver needs a plain text dictionary with one word per line.

You can provide it in any of these ways:

1. Pass a path explicitly:

   ```bash
   python3 main.py --dictionary /path/to/words.txt
   ```

2. Set an environment variable:

   ```bash
   export WORD_HUNT_DICTIONARY=/path/to/words.txt
   python3 main.py
   ```

3. Put a file named `dictionary.txt` or `words.txt` in this repository.

If no dictionary is provided, the script also checks `/usr/share/dict/words`.

## Running the bot

1. Connect the iPhone to the Mac with USB.
2. Open QuickTime Player.
3. Choose **File > New Movie Recording**.
4. Select the iPhone as the camera source so the phone screen appears on the Mac.
5. Open Word Hunt on the iPhone and make sure the full 4x4 board is visible.
6. Start the script:

   ```bash
   python3 main.py --dictionary /path/to/words.txt
   ```

7. Follow the calibration prompts:
   - Hover over the center of the top-left tile.
   - Wait for the 3-second capture.
   - Hover over the center of the bottom-right tile.
   - Wait for the second capture.
8. Enter the 16 board letters row-by-row when prompted.

Example board input:

```text
abcdefghijklmnop
```

That represents this board:

```text
a b c d
e f g h
i j k l
m n o p
```

The solver will find valid paths, sort them from longest word to shortest word,
map them to calibrated screen pixels, and play them automatically.

## Dry run mode

Use `--dry-run` to test solving and pixel mapping without moving the mouse:

```bash
python3 main.py --dictionary /path/to/words.txt --dry-run
```

This is useful after calibration because it prints the solved words and mapped
pixel paths without executing any drags.

## Useful options

```bash
python3 main.py \
  --dictionary /path/to/words.txt \
  --max-words 50 \
  --drag-duration 0.025 \
  --word-delay 0.05 \
  --start-delay 1.0
```

- `--max-words`: limit how many longest-first words are played.
- `--drag-duration`: seconds spent moving between adjacent tile centers.
- `--word-delay`: pause between completed words for Switch Control lag.
- `--start-delay`: pause after solving before automated playback begins.
- `--min-length`: minimum word length to submit; defaults to `3`.

## Safety notes

- Keep the QuickTime window in the same position after calibration.
- Do not resize the QuickTime window after calibration.
- Move the cursor to the top-left screen corner to trigger pyautogui's fail-safe
  if playback needs to stop.
- Run `--dry-run` first if you are adjusting dictionary, calibration, or timing
  settings.
